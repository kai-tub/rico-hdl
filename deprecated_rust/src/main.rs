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
use std::any::Any;
use std::borrow::Cow;
use std::cmp::Ordering;
use std::collections::{HashMap, HashSet};
use std::{fs, path::Path, path::PathBuf};
use walkdir::WalkDir;

// <A, D> are place-holders for types
// (...) is a tuple struct with a single field
// struct Wrapper<A, D>(Array<A, D>);

// enum SupportedWrapper<D> {
//     U16(Wrapper<u16, D>),
//     F32(Wrapper<f32, D>),
// }

// struct DataKeyPair<'a> {
// path: &'a Path

// FUTURE: Fix this anti-pattern
// it should be structure of arrays not
// array of structs
const N_HYSPECNET_BANDS: isize = 224;
const N_UCMERCED_BANDS: isize = 3;

#[derive(Debug)]
enum SrcDataset {
    BigEarthNetS1,
    BigEarthNetS2,
    HySpecNet,
    UCMerced,
}

/// Encoder that converts TIFF files into `safetensors` values and embeds them in an LMDB database.
#[derive(Parser)]
#[command(
    author,
    version,
    about,
    long_about = "
Encoder that converts TIFF files into `safetensors` values and embeds them in an LMDB database.

The CLI will have one required argument, which is the path to the target LMDB file (in reality it is a directory)
Then it will take name arguments that indicate which dataset is being converted:
BigEarthNet-S1, BigEarthNet-S2,etc.

These will take the path to the root directory and find the TIFF files based on custom dataset-specific search functions.

Each dataset will have their own mapping function to:
- filter out wrong tiff files (files not matching a specific regular expression)
- generate a unique key for each safetensors 'value'
   - Important: The key is ONLY guaranteed to be unique for each individual dataset!
- Generate the safetensors value from the files, which will usually include each band as an individual key

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

    /// Path to the HySpecNet root directory.
    #[arg(long, value_name = "ROOT_DIR")]
    hyspecnet_root: Option<PathBuf>,
}

fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    let mut v = Vec::new();
    // if let Some(bigearthnet_s1_root) = cli.bigearthnet_s1_root {
    //     println!("Starting to process BigEarthNet-S1");
    //     v.push(generate_grouped_files(
    //         bigearthnet_s1_root.to_str().unwrap(),
    //         SrcDataset::BigEarthNetS1,
    //     ));
    // }
    if let Some(bigearthnet_s2_root) = cli.bigearthnet_s2_root {
        println!("Starting to process BigEarthNet-S2");
        let paths = recursively_find_tiffs(bigearthnet_s2_root.to_str().unwrap());
        let processed_paths = process_paths_bigearthnet_s2(paths);

        // HERE: extract keys for LMDB! Need to be materialized to ensure checking
        // let lmdb_keys = processed_paths
        //     .iter()
        //     .map(|p| p.file_stem()?.to_str()?.rsplit('_').next())
        //     .collect::<Vec<String>>();

        // pattern
        // X_B01
        // X_B02
        // X_B03
        // ...
        // group by X
        // X: [B01, B02, B03] -> This can be materialized
        let mut grouped_data: HashMap<String, Vec<PathBuf>> = HashMap::new();
        for p in processed_paths {
            let lmdb_key = p
                .file_stem()
                .unwrap()
                .to_str()
                .unwrap()
                .rsplit('_')
                .next()
                .unwrap();
            grouped_data
                .entry(lmdb_key.to_string())
                .or_default()
                .push(p)
        }
        // X, func([B01, B02, B03]), such that
        // serialize(func([B01, B02, B03])) works
        // -> Keep it as it currently is by passing in the source data

        lmdb_writer(&cli.target, grouped_data, SrcDataset::BigEarthNetS2);
        // could zip both to type and ensure that correct order is given, simply continue
        // by providing both lists for now!

        // v.push(generate_grouped_files(
        //     bigearthnet_s2_root.to_str().unwrap(),
        //     SrcDataset::BigEarthNetS2,
        // ));
    }

    // if let Some(hyspecnet_root) = cli.hyspecnet_root {
    //     println!("Starting to process HySpecNet-11k");
    //     v.push(generate_grouped_files(
    //         hyspecnet_root.to_str().unwrap(),
    //         SrcDataset::HySpecNet,
    //     ));
    // }

    // if v.len() == 0 {
    //     println!("No dataset selected! Nothing will be generated!");
    //     return Ok(());
    // }

    // let v_keys: Vec<&String> = v.iter().flat_map(|e| e.keys()).collect();

    // let v_keys_set = v_keys.iter().fold(HashSet::new(), |mut acc, &k| {
    //     acc.insert(k.clone());
    //     acc
    // });

    // if v_keys.len() != v_keys_set.len() {
    //     panic!("Multiple keys present across datasets!");
    // }

    // for grouped_files in v.iter().progress() {
    //     lmdb_writer(&cli.target, grouped_files);
    // }

    Ok(())
}

// /// Check that the HashMap that contains the `group`-String and the `DataKeyPair` data
// /// does not contain any duplicate data and that for each `group` we have the same matching files
// fn check_grouped_files(grouped_files: &HashMap<String, Vec<TypedData>>) {
//     // create a set of safetensors_key values for each vector, while ensuring that these
//     // length of the set is equal to the length of the vector -> Ensuring that there aren't any duplicated keys
//     let safetensors_keys_sets = grouped_files
//         .values()
//         .map(|vec| {
//             let safetensors_keys_set = vec.iter().fold(HashSet::new(), |mut acc, d| {
//                 acc.insert(d.get_safetensors_key().clone());
//                 acc
//             });
//             if safetensors_keys_set.len() != vec.len() {
//                 panic!(
//                     "Safetensor keys are duplicated! This should never happen! Report as bug: {:?}",
//                     vec
//                 );
//             }
//             safetensors_keys_set
//         })
//         .collect::<Vec<_>>();
//     // check that all have the same number of values per match!
//     let safetensors_keys = safetensors_keys_sets.into_iter().reduce(|mut acc, h| {
//         let next_set_len = h.len();
//         acc.extend(h);
//         if acc.len() != next_set_len {
//             panic!("There are differing keys across the safetensors within the same dataset! There must be an issue with the selected dataset!");
//         }
//         acc
//     }).expect("Should be non-empty iterable");

//     let mut pretty_keys = safetensors_keys
//         .iter()
//         .map(|x| x.clone())
//         .collect::<Vec<String>>();
//     pretty_keys.sort_by(|a, b| natural_cmp(a, b));

//     println!(
//         "The following keys will be used in the safetensor:\n{:?}\n",
//         pretty_keys
//     );
// }

fn recursively_find_tiffs(path: &str) -> Vec<PathBuf> {
    info!(
        "About to recursively iterate through directory {}",
        path.to_string()
    );
    let paths = WalkDir::new(path)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| {
            let extension = e
                .path()
                .extension()
                .unwrap_or_default()
                .to_str()
                .unwrap()
                .to_lowercase();
            extension == "tiff" || extension == "tif"
        })
        .map(|e| e.path().to_path_buf())
        .collect::<Vec<PathBuf>>();
    info!("Finished recursing");
    paths
}

static BIGEARTHNET_S1_ORDERING: &[&str] = &["VH", "VV"];

/// Fix S1 band ordering
fn bigearthnet_s1_ordering(a: &str, b: &str) -> Ordering {
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

/// Fix S2 band ordering
/// prefer spatial-ordering for better cache-alignment
/// as usually the channels with the same spatial resolution are stacked together
/// and potentially interpolated
fn bigearthnet_s2_ordering(a: &str, b: &str) -> Ordering {
    match (
        BIGEARTHNET_S2_ORDERING.iter().position(|&x| x == a),
        BIGEARTHNET_S2_ORDERING.iter().position(|&x| x == b),
    ) {
        (Some(index_a), Some(index_b)) => index_a.cmp(&index_b),
        _ => panic!("Unsupported BigEarthNet-S2 key found! {} or {}", a, b),
    }
}

// HERE: Consider rewriting the code and removing safetensorKey
// the main motivation is that I do not actually use that to derive the
// value of the safetensor key! I actually use the underlying data for
// multi-channel data to derive part of the name (channel index for example).
// It started because BigEarthNet was a special case and the safetensorKey
// could be immediately derived from the path + it helped with checking if
// all files were present
// Instead, I could only store the path and wrap a type around it
// -> This function would simply filter out all paths that are
// not part of the match function and potentially error out if unexpected tiffs
// are encountered.
// It could still return a vector of a new type to combine the different types
// In generate_grouped_files the safetensor keys need to be ordered
// -> Only affects BigEarthNet as we are deriving the data from it
// In the check function it only checks if in all "groups" the same "keys" are stored
// and that the keys themselves are unique
// So if I have a single vector of paths for files
// I could... What?
// I could group by the common prefix and count how many matches I have
// 12 for S2 and 2 for S1, while ensuring that the suffix isn't repeated
// Ordering could still be done on a path level? Maybe?
// would just have to be smart in creating a new sort function.
fn process_paths_bigearthnet_s2(paths: Vec<PathBuf>) -> Vec<PathBuf> {
    let pattern_str = r".*_B[0-9A]+$";
    let pattern = Regex::new(&pattern_str).unwrap();
    let mut filtered_paths = paths
        .into_iter()
        .filter(|p| {
            pattern
                .captures(p.file_stem().unwrap().to_str().unwrap())
                .is_some()
        })
        .collect::<Vec<PathBuf>>();
    // .map(|p| TypedData::BigEarthNetS2(p))
    // .collect::<Vec<TypedData>>();
    filtered_paths.sort_unstable_by(
        |a, b| {
            let (a_pre, a_suf) = a
                .file_stem()
                .unwrap()
                .to_str()
                .unwrap()
                .rsplit_once('_')
                .unwrap();
            let (b_pre, b_suf) = b
                .file_stem()
                .unwrap()
                .to_str()
                .unwrap()
                .rsplit_once('_')
                .unwrap();
            match natural_cmp(a_pre, b_pre) {
                Ordering::Equal => bigearthnet_s2_ordering(a_suf, b_suf),
                ordering => ordering,
            }
        }, // split into a_parts, b_parts
    );

    filtered_paths

    // here would come the dataset specific path checking
    // by grouping pased on prefix/suffix and counting +
    // all suffixes are identical
}

// fn process_paths(paths: Vec<PathBuf>, dataset: SrcDataset) -> Vec<TypedData> {
//     // should be a simple switch and process logic
//     let pattern_str = match dataset {
//         SrcDataset::BigEarthNetS2 => "",
//         SrcDataset::BigEarthNetS1 => r".*_V[VH]$",
//         // ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X03110438-SPECTRAL_IMAGE.TIF
//         SrcDataset::HySpecNet => r".*-SPECTRAL_IMAGE$",
//         SrcDataset::UCMerced => r".*\d\d$",
//     };
// }

/// Given a list of file `paths` loop over each file, extract the file stems and
/// generate a grouped_files.
/// The function applies a pre-defined regular expression (selected via `satellite` enum)
/// where a `group` will be extracted as the key of the returning hashmap
/// and the associated value will be pushed to a vector, where each value is a `DataKeyPair`
/// with the `path` set to the considered `path` and the `safetensors_key` to the matched
/// `saftensorsKey` from the regular expression.
// fn generate_grouped_files_from_paths(
//     paths: Vec<PathBuf>,
//     dataset: SrcDataset,
// ) -> HashMap<String, Vec<TypedData>> {
//     let mut grouped_files: HashMap<String, Vec<TypedData>> = HashMap::new();
//     // when parallelizing the regex matching, check:
//     // https://docs.rs/regex/latest/regex/#sharing-a-regex-across-threads-can-result-in-contention
//     let pattern_str = match dataset {
//         SrcDataset::BigEarthNetS2 => r"(?<group>.*)_(?<safetensorsKey>B[0-9A]+)$",
//         SrcDataset::BigEarthNetS1 => r"(?<group>.*)_(?<safetensorsKey>V[VH])$",
//         // ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X03110438-SPECTRAL_IMAGE.TIF
//         SrcDataset::HySpecNet => r"(?<group>.*)-(?<safetensorsKey>SPECTRAL_IMAGE)$",
//         SrcDataset::UCMerced => r"(?<group>.*\d\d)$",
//     };
//     let pattern = Regex::new(&pattern_str).unwrap();
//     // FUTURE: potentially think about parallel access as NFS storage could benefit from it
//     for p in paths {
//         // fix last unwrap
//         let cap_res = pattern.captures(p.file_stem().unwrap().to_str().unwrap());
//         match cap_res {
//             Some(cap) => {
//                 let datakeypair = DataPath {
//                     path: p.clone(),
//                     // could default to an empty string here
//                     safetensors_key: cap["safetensorsKey"].to_string(),
//                 };
//                 grouped_files
//                     .entry(cap["group"].to_string())
//                     .or_default()
//                     .push(match dataset {
//                         SrcDataset::BigEarthNetS1 => TypedData::BigEarthNetS1(datakeypair),
//                         SrcDataset::BigEarthNetS2 => TypedData::BigEarthNetS2(datakeypair),
//                         SrcDataset::HySpecNet => TypedData::HySpecNet(datakeypair),
//                         SrcDataset::UCMerced => TypedData::UCMerced(datakeypair),
//                     })
//             }
//             None => {
//                 match dataset {
//                     SrcDataset::HySpecNet => {},
//                     _ => warn!("Found a tiff file that doesn't match the expected regular expression: \n{}\nThis might indicate issues with the dataset directory!", p.to_str().unwrap_or("<INVALID_UNICODE_PATH>")),
//                 }
//             }
//         }
//     }
//     info!("Finished grouping data!");
//     grouped_files
// }

// fn generate_grouped_files(root_dir: &str, dataset: SrcDataset) -> HashMap<String, Vec<TypedData>> {
//     let paths = recursively_find_tiffs(root_dir);
//     let mut grouped_files = generate_grouped_files_from_paths(paths, dataset);
//     for vals in grouped_files.values_mut() {
//         vals.sort_by(|a, b| match (a, b) {
//             // Only support sorting on S2 only keys here
//             (TypedData::BigEarthNetS2(a), TypedData::BigEarthNetS2(b)) => {
//                 bigearthnet_s2_ordering(&a.safetensors_key, &b.safetensors_key)
//             }
//             (TypedData::BigEarthNetS1(a), TypedData::BigEarthNetS1(b)) => {
//                 bigearthnet_s1_ordering(&a.safetensors_key, &b.safetensors_key)
//             }
//             (TypedData::HySpecNet(a), TypedData::HySpecNet(b)) => {
//                 // hyspecnet_ordering(&a.safetensors_key, &b.safetensors_key)
//                 a.safetensors_key.cmp(&b.safetensors_key)
//             }
//             (TypedData::UCMerced(a), TypedData::UCMerced(b)) => {
//                 a.safetensors_key.cmp(&b.safetensors_key)
//             }
//             _ => panic!("Unsupported ordering operation!"),
//         })
//     }
//     if grouped_files.len() == 0 {
//         panic!("No matching tiff files found!");
//     } else {
//         // needs to be checked before the grouped_files are merged together!
//         check_grouped_files(&grouped_files);
//     }
//     grouped_files
// }

fn lmdb_writer(db_path: &Path, grouped_files: HashMap<String, Vec<PathBuf>>, dataset: SrcDataset) {
    fs::create_dir_all(db_path)
        .expect("should be able to create target directory. Maybe check permissions?");
    let env = EnvOpenOptions::new()
        .map_size(1 * 1024 * 1024 * 1024 * 1024) // 1TB for max map_size
        .open(db_path)
        .expect("Issue creating envoptions. Report as bug!");
    let db: Database<types::Str, types::CowSlice<u8>> = env
        .create_database(None)
        .expect("Should have write access to create database");

    let mut keys: Vec<String> = grouped_files.keys().map(|e| e.clone()).collect();
    keys.sort();

    // Chunk size was chosen more or less randomly. The main idea is to
    // not close & open a write transaction for every item and I also use
    // it to open the files
    for chunk in keys.chunks(512).progress().into_iter() {
        // wtxn cannot be shared across threads!
        // I assume, I would have to parallelize over chunks
        let mut wtxn = env.write_txn().expect("write transaction");
        // maybe the chunk could be split into different threads and the tensors can be shared
        let keyed_tensors: Vec<(&String, Vec<u8>)> = chunk
            .into_par_iter()
            .map(|key| {
                (
                    key,
                    mk_safetensors(grouped_files.get(key).unwrap(), dataset).unwrap(),
                )
            })
            .collect();
        for (key, tns) in keyed_tensors {
            db.put(&mut wtxn, key, &tns).expect("should write");
        }
        wtxn.commit().expect("should commit");
    }
}

enum SupportedWrapper<D> {
    U16(Array<u16, D>),
    I16(Array<i16, D>),
    F32(Array<f32, D>),
}

fn mk_bigearthnet_safetensor(
    path: &PathBuf,
) -> (String, SupportedWrapper<ndarray::prelude::Dim<[usize; 2]>>) {
    let dataset = Dataset::open(path).expect("Current file should have read access!");
    let band1 = dataset
        .rasterband(1)
        .expect("Tiff files should contain at least one band!");
    // tuples (x, y) are in (cols, rows) order
    // `window` is the (x, y) coordinate of the upper left corner of the region to read
    let window = (0, 0);
    // `window_size` is the amount to read -> We will always read everything!
    let window_size = band1.size();
    // assert_eq!(band1.band_type(), GdalDataType::UInt16);
    let arr = match band1.band_type() {
        GdalDataType::UInt16 => SupportedWrapper::U16(
            band1
                .read_as_array::<u16>(window, window_size, window_size, None)
                .expect("File should open correctly. Report bug!"),
        ),
        GdalDataType::Float32 => SupportedWrapper::F32(
            band1
                .read_as_array::<f32>(window, window_size, window_size, None)
                .expect("File should open correctly. Report bug!"),
        ),
        _ => panic!("Unsupported data type detected!"),
    };
    // derive safetensor_key!
    // TODO: Understand if `arr` is copied or not!
    (datakeypair.safetensors_key.clone(), arr)
}

// Function cannot consume the datakeypair
// name mapping could also be implemented by caller
fn mk_hyspecnet_safetensor(
    datakeypair: &DataPath,
    index: isize,
) -> (String, SupportedWrapper<ndarray::prelude::Dim<[usize; 2]>>) {
    let dataset =
        Dataset::open(datakeypair.path.clone()).expect("Current file should have read access!");
    let band1 = dataset
        .rasterband(index)
        .expect("Tiff files should contain at least one band!");
    // tuples (x, y) are in (cols, rows) order
    // `window` is the (x, y) coordinate of the upper left corner of the region to read
    let window = (0, 0);
    // `window_size` is the amount to read -> We will always read everything!
    let window_size = band1.size();
    // assert_eq!(band1.band_type(), GdalDataType::UInt16);
    let arr = match band1.band_type() {
        GdalDataType::Int16 => SupportedWrapper::I16(
            band1
                .read_as_array::<i16>(window, window_size, window_size, None)
                .expect("File should open correctly. Report bug!"),
        ),
        _ => panic!("Unsupported data type detected!"),
    };
    // (datakeypair.safetensors_key.clone(), arr)
    (format!("B{}", index), arr)
}

// looking bad for RGB style datasets...
// they use a single tiff file with three channels
// per default my builder would split the bands up into individual 2d arrays.
// But one could argue that this allows me to provide the correct band metadata informtion
// i.e. describe what channel is R for example.
fn mk_ucmerced_safetensor(
    datakeypair: &DataPath,
    index: isize,
) -> (String, SupportedWrapper<ndarray::prelude::Dim<[usize; 2]>>) {
    let dataset =
        Dataset::open(datakeypair.path.clone()).expect("Current file should have read access!");
    let band1 = dataset
        .rasterband(index)
        .expect("Tiff files should contain at least one band!");

    // band1.color_interpretation().name();
    // tuples (x, y) are in (cols, rows) order
    // `window` is the (x, y) coordinate of the upper left corner of the region to read
    let window = (0, 0);
    // `window_size` is the amount to read -> We will always read everything!
    let window_size = band1.size();
    // assert_eq!(band1.band_type(), GdalDataType::UInt16);
    let arr = match band1.band_type() {
        GdalDataType::Int16 => SupportedWrapper::I16(
            band1
                .read_as_array::<i16>(window, window_size, window_size, None)
                .expect("File should open correctly. Report bug!"),
        ),
        _ => panic!("Unsupported data type detected!"),
    };
    // (datakeypair.safetensors_key.clone(), arr)
    (format!("B{}", index), arr)
}

/// Given a `DataKeyPair` `d` vector, iterate through all elements
/// and read the given raster data from `d.path` and interpret the
/// data as safetensor data.
/// Then construct the given safetensor data and return the resulting
/// data vector.
fn mk_safetensors(pairs: &Vec<PathBuf>, dataset: SrcDataset) -> anyhow::Result<Vec<u8>> {
    let it = match dataset {
        SrcDataset::BigEarthNetS2 => pairs
            .into_iter()
            .flat_map(|p| vec![mk_bigearthnet_safetensor(&p)]),
        _ => panic!("Not implemented yet!"),
    };
    // let it = pairs.into_iter().flat_map(|e| match e {
    //     TypedData::BigEarthNetS1(e) => vec![mk_bigearthnet_safetensor(&e)],
    //     TypedData::BigEarthNetS2(e) => vec![mk_bigearthnet_safetensor(&e)],
    //     // GDAL is 1-indexed!
    //     TypedData::HySpecNet(e) => (1..(N_HYSPECNET_BANDS + 1))
    //         .map(|i| mk_hyspecnet_safetensor(&e, i))
    //         .collect::<Vec<(String, SupportedWrapper<ndarray::prelude::Dim<[usize; 2]>>)>>(),
    //     TypedData::UCMerced(e) => (1..(N_UCMERCED_BANDS + 1))
    //         .map(|i| mk_ucmerced_safetensor(&e, i))
    //         .collect::<Vec<(String, SupportedWrapper<ndarray::prelude::Dim<[usize; 2]>>)>>(),
    // });
    Ok(serialize(it, &None)?)
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
            SupportedWrapper::U16(arr) => {
                let slice = arr.as_slice().expect("Non-contiguous memory for tensor!");
                let num_bytes = std::mem::size_of::<u16>();
                let new_slice: &[u8] = unsafe {
                    // len is the number of elements not the number of bytes!
                    // but as we are using u8 it is effectively the same
                    std::slice::from_raw_parts(slice.as_ptr() as *const u8, slice.len() * num_bytes)
                };
                new_slice
            }
            SupportedWrapper::I16(arr) => {
                let slice = arr.as_slice().expect("Non-contiguous memory for tensor!");
                let num_bytes = std::mem::size_of::<i16>();
                let new_slice: &[u8] = unsafe {
                    // len is the number of elements not the number of bytes!
                    // but as we are using u8 it is effectively the same
                    std::slice::from_raw_parts(slice.as_ptr() as *const u8, slice.len() * num_bytes)
                };
                new_slice
            }
            SupportedWrapper::F32(arr) => {
                let slice = arr.as_slice().expect("Non-contiguous memory for tensor!");
                let num_bytes = std::mem::size_of::<f32>();
                let new_slice: &[u8] = unsafe {
                    // len is the number of elements not the number of bytes!
                    // but as we are using u8 it is effectively the same
                    std::slice::from_raw_parts(slice.as_ptr() as *const u8, slice.len() * num_bytes)
                };
                new_slice
            }
        }
    }
}

impl<D: Dimension> View for SupportedWrapper<D> {
    fn dtype(&self) -> Dtype {
        match self {
            SupportedWrapper::U16(_) => Dtype::U16,
            SupportedWrapper::F32(_) => Dtype::F32,
            SupportedWrapper::I16(_) => Dtype::I16,
        }
    }

    fn shape(&self) -> &[usize] {
        match self {
            SupportedWrapper::U16(arr) => arr.shape(),
            SupportedWrapper::F32(arr) => arr.shape(),
            SupportedWrapper::I16(arr) => arr.shape(),
        }
    }

    fn data(&self) -> Cow<[u8]> {
        self.buffer().into()
    }

    fn data_len(&self) -> usize {
        self.buffer().len()
    }
}
