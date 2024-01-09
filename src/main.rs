use anyhow;
use gdal::{raster::GdalDataType, Dataset};
use heed::{types, Database, EnvOpenOptions};
use log::info;
use ndarray::{Array, Dimension};
use rayon::prelude::*;
use regex::Regex;
use safetensors::{serialize, Dtype, View};
use std::borrow::Cow;
use std::collections::HashMap;
use std::{fs, path::Path, path::PathBuf};
use walkdir::WalkDir;

// <A, D> are place-holders for types
// (...) is a tuple struct with a single field
struct Wrapper<A, D>(Array<A, D>);

// struct DataKeyPair<'a> {
// path: &'a Path,

#[derive(Debug)]
struct DataKeyPair {
    path: PathBuf,
    safetensor_key: String,
}

fn main() -> anyhow::Result<()> {
    // TODO: Add logic to parse data from CLI
    // where the directories the directories to process are given after each other
    let prefix_pattern = Regex::new(r"(.*)_(B[0-9A]+)|([VH]+)").unwrap();

    // loop over all input directories
    // and give option to merge them into single LMDB file
    info!("About to recursively iterate through directory");
    let paths = WalkDir::new("tiffs")
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| {
            let name = e.file_name().to_str().unwrap();
            name.ends_with(".tiff") || name.ends_with(".tif")
        })
        .map(|e| e.path().to_path_buf())
        .collect::<Vec<PathBuf>>();
    info!("Finished recursing");
    let mut grouped_files: HashMap<String, Vec<DataKeyPair>> = HashMap::new();
    // FUTURE: potentially think about parallel access
    for p in paths {
        // fix last unwrap
        let cap = prefix_pattern
            .captures(p.file_name().unwrap().to_str().unwrap())
            .unwrap();
        grouped_files
            .entry(cap.get(1).unwrap().as_str().to_string())
            .or_default()
            .push(DataKeyPair {
                path: p.clone(),
                safetensor_key: cap.get(2).unwrap().as_str().to_string(),
            })
    }
    info!("Finished grouping data!");
    println!("Grouped files: {:?}", grouped_files);
    // TODO: Write conflicts key checker
    // would have to read the data from each DataKeyPair from vec
    // and check if either the safetensor_key or path is duplicated
    // if it is, something is wrong
    // Finer checks could report how report the size of each element
    // these could be warnings if the number is weird (not 12 or 2)
    // or if the key has an unknown value. Or it could simply report all
    // keys that it found!

    // could think about working with references
    let mut keys: Vec<String> = grouped_files.keys().map(|e| e.clone()).collect();
    // could be changed in the future to sort not only by the prefix
    // Remember, this only defines how the LMDB file is written, not how the
    // safetensors are written!
    keys.sort();

    fs::create_dir_all(Path::new("target").join("b01.db"))?;
    let env = EnvOpenOptions::new()
        .map_size(1 * 1024 * 1024 * 1024 * 1024) // 1TB for max map_size
        .open(Path::new("target").join("b01.db"))
        .expect("Issue creating envoptions. Report as bug!");
    let db: Database<types::Str, types::CowSlice<u8>> = env
        .create_database(None)
        .expect("Should have write access to create database");

    for chunk in keys.chunks(1024).into_iter() {
        // wtxn cannot be shared across threads!
        // I assume, I would have to parallelize over chunks
        let mut wtxn = env.write_txn().expect("write transaction");
        for key in chunk {
            // TODO: Add sorting to vectors!
            let tns = mk_safetensor(grouped_files.get(key).unwrap()).unwrap();
            db.put(&mut wtxn, key, &tns).expect("should write");
        }
        wtxn.commit().expect("should commit");
    }

    // this should be wrapped around a chunkifying API
    // where each directory safetensor should have the shape of
    // {"B01": <data>, "B02": <data>, [...] }

    // let p = Path::new("B01.tiff");
    // let tns = mk_safetensor(vec![DataKeyPair {
    //     path: &p,
    //     safetensor_key: "B01".to_string(),
    // }])?;
    // let mut wtxn = env.write_txn().expect("write transaction");
    // db.put(&mut wtxn, "one", &tns).expect("should write");
    // wtxn.commit().expect("should commit");
    Ok(())
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
        assert_eq!(band1.band_type(), GdalDataType::UInt16);
        // tuples (x, y) are in (cols, rows) order
        // `window` is the (x, y) coordinate of the upper left corner of the region to read
        let window = (0, 0);
        // `window_size` is the amount to read -> We will always read everything!
        let window_size = band1.size();
        let arr = band1
            .read_as_array::<u16>(window, window_size, window_size, None)
            .expect("File should open correctly. Report bug!");
        (e.safetensor_key.clone(), Wrapper(arr))
    });

    Ok(serialize(it, &None)?)
}

// Returns the necessary data
// Generic type D that implements the `Dimension` trait
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
