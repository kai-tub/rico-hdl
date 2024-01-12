/// Main strategy is as follows:
/// The CLI will have one required argument, which is the path to the target LMDB "file" (in reality it is a directory)
/// Then it will take name arguments that indicate which dataset is being converted:
/// BEN-S1, BEN-S2, BEN-segmentation-maps, etc.
/// These will take the path to the root directory and resursively find all TIFF files.
/// Each dataset will have their own mapping function to:
/// - filter out wrong tiff files (files not matching a specific regular expression)
/// - generate a unique key for each safetensor "value"
///    - Important: The key is ONLY guaranteed to be unique for... Really?
/// - Generate the safetensor value from the files, which will usually include each band as an individual key
///
/// This library will NOT support custom subsetting of the datasets!
/// The main reason is that there should be almost no performance differences between the full and subsetted encoder targets.
/// The only reason would be to generate smaller files for convenience.
/// To keep the program flexible and simple, it won't provide this functionality.
/// It is up to the user to extract these subsets.
/// For BigEarthNet, one possible solution would be to simple copy (or symbolically link) only the patch directories that are of interest.
/// If there is a strong need for such subsetting functionality, we could provide another tool to do so efficiently.
use anyhow;
use clap::Parser;
use core::panic;
use gdal::{raster::GdalDataType, Dataset};
use heed::{types, Database, EnvOpenOptions};
use indicatif::ProgressIterator;
use lexical_sort::natural_cmp;
use log::{info, warn};
use ndarray::{Array, Dimension};
use rayon::prelude::*;
use regex::Regex;
use safetensors::{serialize, Dtype, View};
use std::borrow::Cow;
use std::cmp::Ordering;
use std::collections::{HashMap, HashSet};
use std::{fs, path::Path, path::PathBuf};
use walkdir::WalkDir;

// <A, D> are place-holders for types
// (...) is a tuple struct with a single field
struct Wrapper<A, D>(Array<A, D>);

enum SupportedWrapper<D> {
    U16(Wrapper<u16, D>),
    F32(Wrapper<f32, D>),
}

// enum SupportedWrapper<D> {
//     U16(Array<u16, D>),
//     F32(Array<u16, D>),
// }

// struct DataKeyPair<'a> {
// path: &'a Path,

// FUTURE: Fix this anti-pattern
// it should be structure of arrays not
// array of structs
#[derive(Debug)]
struct DataKeyPair {
    path: PathBuf,
    safetensor_key: String,
    // could add explicit indexes to read from a given band
}

/// Encoder that converts TIFF files into `safetensor` values and embeds them in an LMDB database.
#[derive(Parser)]
#[command(
    author,
    version,
    about,
    long_about = "
Encoder that converts TIFF files into `safetensor` values and embeds them in an LMDB database.

The CLI will have one required argument, which is the path to the target LMDB file (in reality it is a directory)
Then it will take name arguments that indicate which dataset is being converted:
BigEarthNet-S1, BigEarthNet-S2,etc.

These will take the path to the root directory and find the TIFF files based on custom dataset-specific search functions.

Each dataset will have their own mapping function to:
- filter out wrong tiff files (files not matching a specific regular expression)
- generate a unique key for each safetensor 'value'
   - Important: The key is ONLY guaranteed to be unique for each individual dataset!
- Generate the safetensor value from the files, which will usually include each band as an individual key

By providing multiple datset sources, all files will be written into a single LMDB file, potentially
making it easier to work with the dataset.

This library will NOT support custom subsetting of the datasets!
The main reason is that there should be almost no performance differences between the full and subsetted encoder targets.
The only reason would be to generate smaller files for convenience.
To keep the program flexible and simple, it won't provide this functionality.
It is up to the user to extract these subsets.
For BigEarthNet, one possible solution would be to simple copy (or symbolically link) only the patch directories that are of interest.
If there is a strong need for such subsetting functionality, we could provide another tool to do so efficiently.
"
)]
struct Cli {
    /// target directory where the LMDB file will be written to
    /// Paths will be created if necessary
    target: PathBuf,

    /// Path to the BigEarthNet-S1 root directory.
    #[arg(long, value_name = "ROOT_DIR")]
    bigearthnet_s1_root: Option<PathBuf>,

    /// Path to the BigEarthNet-S2 root directory.
    #[arg(long, value_name = "ROOT_DIR")]
    bigearthnet_s2_root: Option<PathBuf>,
}

// Tried to avoid GDAL and using the rust crate TIFF but this doesn't support multi-band tiffs...
// fn main() {
//     let img_file = File::open(PathBuf::from("./Highway_2.tif")).expect("cannot find image");
//     let mut decoder = Decoder::new(img_file).expect("should create decoder");
//     println!("Dimensions: {:?}", decoder.dimensions().unwrap());
//     println!("Images: {:?}", decoder.more_images());
//     let img = decoder.read_image().unwrap();
//     match img {
//         DecodingResult::U16(res) => {
//             println!("Decoded");
//         }
//         _ => panic!("wrong bit depth"),
//     };
// }

fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    let mut v = Vec::new();
    if let Some(bigearthnet_s1_root) = cli.bigearthnet_s1_root {
        println!("Starting to process BigEarthNet-S1");
        v.push(generate_grouped_files_from_bigearthnet_s1(
            bigearthnet_s1_root.to_str().unwrap(),
        ));
    }
    if let Some(bigearthnet_s2_root) = cli.bigearthnet_s2_root {
        println!("Starting to process BigEarthNet-S2");
        v.push(generate_grouped_files_from_bigearthnet_s2(
            bigearthnet_s2_root.to_str().unwrap(),
        ));
    }

    if v.len() == 0 {
        println!("No dataset selected! Nothing will be generated!");
        return Ok(());
    }

    let v_keys: Vec<&String> = v.iter().flat_map(|e| e.keys()).collect();

    let v_keys_set = v_keys.iter().fold(HashSet::new(), |mut acc, &k| {
        acc.insert(k.clone());
        acc
    });

    if v_keys.len() != v_keys_set.len() {
        panic!("Multiple keys present across datasets!");
    }

    for grouped_files in v.iter() {
        lmdb_writer(&cli.target, grouped_files);
    }

    Ok(())
}

fn check_grouped_files(grouped_files: &HashMap<String, Vec<DataKeyPair>>) {
    // create a set of safetensor_key values for each vector, while ensuring that these
    // length of the set is equal to the length of the vector -> Ensuring that there aren't any duplicated keys
    let safetensor_keys_sets = grouped_files
        .values()
        .map(|vec| {
            let safetensor_keys_set = vec.iter().fold(HashSet::new(), |mut acc, d| {
                acc.insert(d.safetensor_key.clone());
                acc
            });
            if safetensor_keys_set.len() != vec.len() {
                panic!(
                    "Safetensor keys are duplicated! This should never happen! Report as bug: {:?}",
                    vec
                );
            }
            safetensor_keys_set
        })
        .collect::<Vec<_>>();
    // check that all have the same number of values per match!
    let safetensor_keys = safetensor_keys_sets.into_iter().reduce(|mut acc, h| {
        let next_set_len = h.len();
        acc.extend(h);
        if acc.len() != next_set_len {
            panic!("There are differing keys across the safetensors within the same dataset! There must be an issue with the selected dataset!");
        }
        acc
    }).expect("Should be non-empty iterable");

    let mut pretty_keys = safetensor_keys
        .iter()
        .map(|x| x.clone())
        .collect::<Vec<String>>();
    pretty_keys.sort_by(|a, b| natural_cmp(a, b));

    println!(
        "The following keys will be used in the safetensor:\n{:?}",
        pretty_keys
    );
}

fn recursively_find_tiffs(path: &str) -> Vec<PathBuf> {
    info!(
        "About to recursively iterate through directory {}",
        path.to_string()
    );
    let paths = WalkDir::new(path)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| {
            let extension = e.path().extension().unwrap_or_default().to_str().unwrap();
            extension == "tiff" || extension == "tif"
        })
        .map(|e| e.path().to_path_buf())
        .collect::<Vec<PathBuf>>();
    info!("Finished recursing");
    paths
}

static BIGEARTHNET_S1_ORDERING: &[&str] = &["VH", "VV"];

fn bigearthnet_s1_ordering(a: &str, b: &str) -> Ordering {
    // prefer spatial-ordering for better cache-alignment
    // as usually the channels with the same spatial resolution are stacked together
    // and potentially interpolated
    // let static_order = vec!["VH", "VV"];
    match (
        BIGEARTHNET_S1_ORDERING.iter().position(|&x| x == a),
        BIGEARTHNET_S1_ORDERING.iter().position(|&x| x == b),
    ) {
        (Some(index_a), Some(index_b)) => index_a.cmp(&index_b),
        _ => panic!("Unsupported BigEarthNet-S1 key found! {} or {}", a, b),
    }
}

static BIGEARTHNET_S2_ORDERING: &[&str] = &[
    "B02", "B03", "B04", "B08", "B05", "B06", "B07", "B8A", "B10", "B11", "B12", "B01", "B09",
];

fn bigearthnet_s2_ordering(a: &str, b: &str) -> Ordering {
    // prefer spatial-ordering for better cache-alignment
    // as usually the channels with the same spatial resolution are stacked together
    // and potentially interpolated
    match (
        BIGEARTHNET_S2_ORDERING.iter().position(|&x| x == a),
        BIGEARTHNET_S2_ORDERING.iter().position(|&x| x == b),
    ) {
        (Some(index_a), Some(index_b)) => index_a.cmp(&index_b),
        _ => panic!("Unsupported BigEarthNet-S2 key found! {} or {}", a, b),
    }
}

fn generate_grouped_files_from_bigearthnet_paths(
    paths: Vec<PathBuf>,
    pattern: &Regex,
) -> HashMap<String, Vec<DataKeyPair>> {
    // loop over all input directories
    // and give option to merge them into single LMDB file
    let mut grouped_files: HashMap<String, Vec<DataKeyPair>> = HashMap::new();
    // grouped_files contains the LMDB key as key
    // and the Vec<DataKeyPair> to generate the safetensor later
    // this should be the return value for each dataset

    // FUTURE: potentially think about parallel access as NFS storage could benefit from it
    for p in paths {
        // fix last unwrap
        let cap_res = pattern.captures(p.file_stem().unwrap().to_str().unwrap());
        match cap_res {
            Some(cap) => grouped_files
                .entry(cap["prefix"].to_string())
                .or_default()
                .push(DataKeyPair {
                    path: p.clone(),
                    safetensor_key: cap["key"].to_string(),
                }),
            None => {
                warn!("Found a tiff file that doesn't match the expected regular expression: \n{}\nThis might indicate issues with the dataset directory!", p.to_str().unwrap_or("<INVALID_UNICODE_PATH>"));
            }
        }
    }
    info!("Finished grouping data!");
    grouped_files
}

fn generate_grouped_files_from_bigearthnet_s2(
    root_ben_s2_dir: &str,
) -> HashMap<String, Vec<DataKeyPair>> {
    let paths = recursively_find_tiffs(root_ben_s2_dir);
    // when parallelizing the regex matching, check:
    // https://docs.rs/regex/latest/regex/#sharing-a-regex-across-threads-can-result-in-contention
    let ben_s2_stem_pattern = Regex::new(r"(?<prefix>.*)_(?<key>B[0-9A]+)$").unwrap();
    let mut grouped_files =
        generate_grouped_files_from_bigearthnet_paths(paths, &ben_s2_stem_pattern);
    for vals in grouped_files.values_mut() {
        vals.sort_by(|a, b| bigearthnet_s2_ordering(&a.safetensor_key, &b.safetensor_key));
    }
    if grouped_files.len() == 0 {
        println!("No matching tiff files found! Skipping...");
    } else {
        // needs to be checked before the grouped_files are merged together!
        check_grouped_files(&grouped_files);
    }
    grouped_files
}

fn generate_grouped_files_from_bigearthnet_s1(
    root_ben_s1_dir: &str,
) -> HashMap<String, Vec<DataKeyPair>> {
    let paths = recursively_find_tiffs(root_ben_s1_dir);
    // when parallelizing the regex matching, check:
    // https://docs.rs/regex/latest/regex/#sharing-a-regex-across-threads-can-result-in-contention
    let ben_s1_stem_pattern = Regex::new(r"(?<prefix>.*)_(?<key>V[VH])$").unwrap();
    let mut grouped_files =
        generate_grouped_files_from_bigearthnet_paths(paths, &ben_s1_stem_pattern);
    for vals in grouped_files.values_mut() {
        vals.sort_by(|a, b| bigearthnet_s1_ordering(&a.safetensor_key, &b.safetensor_key));
    }
    // needs to be checked before the grouped_files are merged together!
    check_grouped_files(&grouped_files);
    grouped_files
}

fn lmdb_writer(db_path: &Path, grouped_files: &HashMap<String, Vec<DataKeyPair>>) {
    fs::create_dir_all(db_path)
        .expect("should be able to create target directory. Maybe check permissions?");
    let env = EnvOpenOptions::new()
        .map_size(1 * 1024 * 1024 * 1024 * 1024) // 1TB for max map_size
        .open(db_path)
        .expect("Issue creating envoptions. Report as bug!");
    let db: Database<types::Str, types::CowSlice<u8>> = env
        .create_database(None)
        .expect("Should have write access to create database");

    // FUTURE: think about working with references instead of cloning
    let mut keys: Vec<String> = grouped_files.keys().map(|e| e.clone()).collect();
    // could be changed in the future to sort not only by the prefix
    // Remember, this only defines how the LMDB file is written, not how the
    // safetensors are written!
    keys.sort();

    // TODO: Try to get it running with an older GLIBC version!
    // -> Just bite the bullet and build it as nix image and docker image
    // Chunk size was chosen more or less randomly. The main idea is to
    // not close & open a write transaction for every item.
    for chunk in keys.chunks(4096).progress().into_iter() {
        // wtxn cannot be shared across threads!
        // I assume, I would have to parallelize over chunks
        let mut wtxn = env.write_txn().expect("write transaction");
        // maybe the chunk could be split into different threads and the tensors can be shared
        let keyed_tensors: Vec<(&String, Vec<u8>)> = chunk
            .into_par_iter()
            .map(|key| (key, mk_safetensor(grouped_files.get(key).unwrap()).unwrap()))
            .collect();
        // FUTURE: Write a test that ensures that the output remains stable!
        for (key, tns) in keyed_tensors {
            db.put(&mut wtxn, key, &tns).expect("should write");
        }
        wtxn.commit().expect("should commit");
    }
}

/// Given a `DataKeyPair` `d` vector, iterate through all elements
/// and read the given raster data from `d.path` and interpret the
/// data as safetensor data.
/// Then construct the given safetensor data and return the resulting
/// data vector.
fn mk_safetensor(pairs: &Vec<DataKeyPair>) -> anyhow::Result<Vec<u8>> {
    let it = pairs.into_iter().map(|e| {
        let dataset = Dataset::open(e.path.clone()).expect("Current file should have read access!");
        let band1 = dataset
            .rasterband(1)
            .expect("Tiff files should contain at least one band!");
        // tuples (x, y) are in (cols, rows) order
        // `window` is the (x, y) coordinate of the upper left corner of the region to read
        let window = (0, 0);
        // `window_size` is the amount to read -> We will always read everything!
        let window_size = band1.size();
        // assert_eq!(band1.band_type(), GdalDataType::UInt16);
        match band1.band_type() {
            GdalDataType::UInt16 => SupportedWrapper::U16(Wrapper(
                band1
                    .read_as_array::<u16>(window, window_size, window_size, None)
                    .expect("File should open correctly. Report bug!"),
            )),
            GdalDataType::Float32 => SupportedWrapper::F32(Wrapper(
                band1
                    .read_as_array::<f32>(window, window_size, window_size, None)
                    .expect("File should open correctly. Report bug!"),
            )),
            _ => panic!("Unsupported data type detected!"),
        }
        // let arr = band1
        //     .read_as_array::<u16>(window, window_size, window_size, None)
        //     .expect("File should open correctly. Report bug!");

        // (e.safetensor_key.clone(), Wrapper(arr))
    });

    Ok(serialize(
        pairs.iter().map(|e| e.safetensor_key.clone()).zip(it),
        &None,
    )?)
}

// Code from GitHub issue:
// https://github.com/huggingface/safetensors/issues/190#issuecomment-1461515430
// Returns the necessary data
// Generic type D that implements the `Dimension` trait
// And yes, the code could definitely be simplified!
// I *really* need to redo the following code. It is impressively ugly...
impl<D: Dimension> SupportedWrapper<D> {
    fn buffer(&self) -> &[u8] {
        match self {
            SupportedWrapper::U16(arr) => arr.buffer(),
            SupportedWrapper::F32(arr) => arr.buffer(),
        }
    }
}

impl<D: Dimension> View for SupportedWrapper<D> {
    fn dtype(&self) -> Dtype {
        match self {
            SupportedWrapper::U16(_) => Dtype::U16,
            SupportedWrapper::F32(_) => Dtype::F32,
        }
        // Dtype::U16
    }

    fn shape(&self) -> &[usize] {
        match self {
            SupportedWrapper::U16(arr) => arr.0.shape(),
            SupportedWrapper::F32(arr) => arr.0.shape(),
        }
    }

    fn data(&self) -> Cow<[u8]> {
        self.buffer().into()
    }

    fn data_len(&self) -> usize {
        self.buffer().len()
    }
}

impl<D: Dimension> Wrapper<u16, D> {
    fn buffer(&self) -> &[u8] {
        let slice = self
            .0
            .as_slice()
            .expect("Non-contiguous memory for tensor!");
        let num_bytes = std::mem::size_of::<u16>();
        let new_slice: &[u8] = unsafe {
            // len is the number of elements not the number of bytes!
            // but as we are using u8 it is effectively the same
            std::slice::from_raw_parts(slice.as_ptr() as *const u8, slice.len() * num_bytes)
        };
        new_slice
    }
}

impl<D: Dimension> Wrapper<f32, D> {
    fn buffer(&self) -> &[u8] {
        let slice = self
            .0
            .as_slice()
            .expect("Non-contiguous memory for tensor!");
        let num_bytes = std::mem::size_of::<f32>();
        let new_slice: &[u8] = unsafe {
            // len is the number of elements not the number of bytes!
            // but as we are using u8 it is effectively the same
            std::slice::from_raw_parts(slice.as_ptr() as *const u8, slice.len() * num_bytes)
        };
        new_slice
    }
}

impl<D: Dimension> View for Wrapper<u16, D> {
    fn dtype(&self) -> Dtype {
        Dtype::U16
    }

    fn shape(&self) -> &[usize] {
        self.0.shape()
    }

    fn data(&self) -> Cow<[u8]> {
        self.buffer().into()
    }

    fn data_len(&self) -> usize {
        self.buffer().len()
    }
}

impl<D: Dimension> View for Wrapper<f32, D> {
    fn dtype(&self) -> Dtype {
        Dtype::F32
    }

    fn shape(&self) -> &[usize] {
        self.0.shape()
    }

    fn data(&self) -> Cow<[u8]> {
        self.buffer().into()
    }

    fn data_len(&self) -> usize {
        self.buffer().len()
    }
}
