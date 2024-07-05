import os
import typer
from typing import TypeAlias
from typing_extensions import Annotated
import lmdb
from safetensors.numpy import save
import sys
import rasterio
from pathlib import Path
import subprocess
import structlog
from more_itertools import chunked
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
import warnings
from rasterio.errors import NotGeoreferencedWarning

log = structlog.get_logger()

BIGEARTHNET_S2_ORDERING = [
    "B02",
    "B03",
    "B04",
    "B08",
    "B05",
    "B06",
    "B07",
    "B8A",
    "B11",
    "B12",
    "B01",
    "B09",
]

# Defined in the order of the bands!
# Order taken from (and only implicitely confirmed in):
# https://github.com/phelber/EuroSAT/issues/7#issuecomment-916754970
# Visualizing the individual bands supports the ordering, as one
# can see the different interpolation strengths for the 20 and 60m
# bands.
EUROSAT_MS_BANDS = [
    "B01",
    "B02",
    "B03",
    "B04",
    "B05",
    "B06",
    "B07",
    "B08",
    "B09",
    "B10",
    "B11",
    "B12",
    "B08A",
]

BIGEARTHNET_S1_ORDERING = ["VH", "VV"]

NUM_HYSPECNET_BANDS = 224
# see output of `gdalinfo`
UC_MERCED_BAND_IDX_COLOR_MAPPING = {1: "Red", 2: "Green", 3: "Blue"}

GENERAL_HELP_TEXT = """\
This CLI tool is a fast and easy-to-use *r*emote sensing *i*mage format *co*nverter
for *h*igh-throughput *d*eep-*l*earning (rico-hdl).
It iterates over the source files of a given dataset and converts the individual bands
into safetensor dictionary entries and write the result into the high-throughput
LMDB database at the given `target_dir` location.
"""

app = typer.Typer(help=GENERAL_HELP_TEXT)

# `type` is too new for pylsp
TargetDir: TypeAlias = Annotated[
    Path,
    typer.Option(
        exists=False,
        resolve_path=True,
    ),
]

DatasetDir: TypeAlias = Annotated[
    Path,
    typer.Option(
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
    ),
]


def open_lmdb(dir: str):
    # 1TB for map_size
    log.debug(f"Opening LMDB database: {dir}")
    return lmdb.open(
        str(dir),
        readonly=False,
        create=True,
        map_size=(1 * 1024 * 1024 * 1024 * 1024),
    )


def read_single_band_raster(path: Path, index: int = 1, is_georeferenced: bool = True):
    if not is_georeferenced:
        warnings.filterwarnings("ignore", category=NotGeoreferencedWarning)
    with rasterio.open(path) as r:
        return r.read(index)


def s2_read_tif(path: Path):
    # could also have the logic to try out .tiff
    if not path.exists():
        raise Exception(
            f"Could not find file: {path}\nThe S2 dataset is probably incomplete/broken!"
        )
    return read_single_band_raster(path)


def s1_read_tif(path: Path):
    if not path.exists():
        raise Exception(
            f"Could not find file: {path}\nThe S1 dataset is probably incomplete/broken!"
        )
    return read_single_band_raster(path)


def bigearthnet_s2_to_safetensor(patch_path: str) -> bytes:
    """
    Given the path to a BigEarthNet-S2 patch directory
    (NOT the individual TIFF files), read the individual
    band files in a pre-defined order and convert it
    into a serialized safetensor dictionary.
    """
    # In Python the dictionary insertion order is stable!
    # order the data here to make it clear that we are doing it
    # to order the safetensor entries!
    p = Path(patch_path)
    data = {
        band: s2_read_tif(p.joinpath(f"{p.stem}_{band}.tif"))
        for band in BIGEARTHNET_S2_ORDERING
    }
    return save(data, metadata=None)


def bigearthnet_s1_to_safetensor(patch_path: str) -> bytes:
    """
    Given the path to a BigEarthNet-S1 patch directory
    (NOT the individual TIFF files), read the individual
    band files in a pre-defined order and convert it
    into a serialized safetensor dictionary.
    """
    # In Python the dictionary insertion order is stable!
    # order the data here to make it clear that we are doing it
    # to order the safetensor entries!
    p = Path(patch_path)
    data = {
        band: read_single_band_raster(p.joinpath(f"{p.stem}_{band}.tif"))
        for band in BIGEARTHNET_S1_ORDERING
    }
    return save(data, metadata=None)


@app.command()
def uc_merced(
    target_dir: TargetDir,
    dataset_dir: DatasetDir,
):
    """
    [UC Merced Land Use Dataset](http://weegee.vision.ucmerced.edu/datasets/landuse.html) converter.

    The LMDB keys will be the names of the UC Merced patches without the
    `.tif` suffix.

    The `safetensor` keys are [`Red`, `Green`, `Blue`] to indicate the respective
    channel meaning.
    """
    # FUTURE: Allow keeping it together and only have a single joined RGB tensor
    # -> This is possible but kinda defeats the purpose of wrapping it in a saftensor
    # For such a small dataset, it would be interesting to know if this extra stacking
    # costs a lot of time.
    log.info(f"Searching for patches in: {dataset_dir}")
    # this could match the file paths directly
    # the lmdb key would be the name itself without SPECTRAL_IMAGE.TIF
    # and the safetensor would be produced from this file
    # Remember: hyspecnet has multiple bands per file!
    patch_paths = fast_find(r".*\d\d\.tif$", dataset_dir, only_dir=False)
    num_patch_paths = len(patch_paths)
    log.debug(f"Found {num_patch_paths} patches.")
    assert num_patch_paths > 0
    env = open_lmdb(target_dir)
    log.debug("Writing UC Merced data into LMDB")
    lmdb_writer(env, patch_paths, encode_stem, uc_merced_to_safetensor)


@app.command()
def eurosat_multi_spectral(
    target_dir: TargetDir,
    dataset_dir: DatasetDir,
    # RGB ?
):
    """
    [EuroSAT Multi-Spectral](https://doi.org/10.5281/zenodo.7711810) converter.

    The LMDB keys will be the names of the EuroSAT_MS patches without the
    `.tif` suffix.

    The `safetensor` keys are the band names from the
    [EuroSAT paper](https://ieeexplore.ieee.org/abstract/document/8736785).

    NOTE: No atmospheric correction has been applied to the dataset
    NOTE: Lower spatial resolution bands were upsampled to 10m spatial resolution
    using cubic-spline interpolation.
    """
    log.info(f"Searching for patches in: {dataset_dir}")
    # this could match the file paths directly
    # the lmdb key would be the name itself without SPECTRAL_IMAGE.TIF
    # and the safetensor would be produced from this file
    # Remember: hyspecnet has multiple bands per file!
    patch_paths = fast_find(r".*\d+\.tif$", dataset_dir, only_dir=False)
    num_patch_paths = len(patch_paths)
    log.debug(f"Found {num_patch_paths} patches.")
    assert num_patch_paths > 0
    env = open_lmdb(target_dir)
    log.debug("Writing EuroSAT_MS data into LMDB")
    # Understand what the Band mapping is!
    lmdb_writer(env, patch_paths, encode_stem, eurosat_ms_to_safetensor)


@app.command()
def hyspecnet_11k(
    target_dir: TargetDir,
    dataset_dir: DatasetDir,
):
    """
    HySpecNet-11k converter.

    The LMDB keys will be the names of the HySpecNet-11k patches without the
    `-SPECTRAL_IMAGE.TIF` suffix.
    The `safetensors` keys are the band numbers prefixed with `B`
    (for example: `B1`, `B12`, `B122`).

    NOTE: Band indexes start with 1 and not 0!
    """
    log.info(f"Searching for patches in: {dataset_dir}")
    # this could match the file paths directly
    # the lmdb key would be the name itself without SPECTRAL_IMAGE.TIF
    # and the safetensor would be produced from this file
    # Remember: hyspecnet has multiple bands per file!
    patch_paths = fast_find(r"ENMAP.*?_L2A.*-Y\d+_X\d+$", dataset_dir, only_dir=True)
    num_patch_paths = len(patch_paths)
    log.debug(f"Found {num_patch_paths} patches.")
    assert num_patch_paths > 0
    env = open_lmdb(target_dir)
    log.debug("Writing HyspecNet-11k data into LMDB")
    lmdb_writer(env, patch_paths, encode_stem, hyspecnet_to_safetensor)


def encode_stem(path: str) -> bytes:
    """
    Given a path extract the stem and encode the string.
    """
    return str(Path(path).stem).encode()


def eurosat_ms_to_safetensor(patch_path: str) -> bytes:
    """
    Given the path to a multi-spectral EuroSAT patch file (`.tif` file),
    read the individual bands and write them as entries
    into a serialized safetensor dictionary.
    The keys map to the band name specified in the [EuroSAT paper](https://ieeexplore.ieee.org/abstract/document/8736785)
    (one of: `B01`, `B02`, `B03`, `B04`, `B05`, `B06`, `B07`, `B08`, `B08A`, `B09`, `B10`, `B11`, `B12`)
    """
    p = Path(patch_path)
    data = {
        name: read_single_band_raster(p, index=idx)
        for idx, name in enumerate(EUROSAT_MS_BANDS, start=1)
    }

    return save(data, metadata=None)


def uc_merced_to_safetensor(patch_path: str) -> bytes:
    """
    Given the path to a UC Merced patch file (`.tif` file),
    read the individual bands and write them as entries
    into a serialized safetensor dictionary.
    The keys map to the color band value (`Red`, `Green`, `Blue`).
    """
    p = Path(patch_path)
    data = {
        color: read_single_band_raster(p, index=idx, is_georeferenced=False)
        for idx, color in UC_MERCED_BAND_IDX_COLOR_MAPPING.items()
    }

    return save(data, metadata=None)


def hyspecnet_to_safetensor(patch_path: str) -> bytes:
    """
    Given the path to a HySpecNet-11k patch directory
    (NOT the individual TIFF file), read the individual
    bands from the SPECTRAL_IMAGE.TIF file and write them as
    entries into a serialized safetensor dictionary.
    The keys are the integer encoded band values.
    """
    # get number of bands for tiff
    # for i in range: read_single band
    p = Path(patch_path)
    data = {
        f"B{band_idx}": read_single_band_raster(
            p.joinpath(f"{p.stem}-SPECTRAL_IMAGE.TIF"), index=band_idx
        )
        for band_idx in range(1, NUM_HYSPECNET_BANDS + 1)
    }
    return save(data, metadata=None)


def fast_find(
    regex: str,
    search_directory: str,
    only_dir: bool = True,
    threads: int = os.cpu_count(),
) -> list[str]:
    """
    Use `fd` to quickly find all files/directories that match a given regular expression.
    Will default to using `os.cpu_count()` number of threads.
    This highly optimized program is especially useful for slow network-attached storage solutions
    or slow hard-drives.
    """
    return subprocess.check_output(
        [
            "fd",
            "--no-ignore",
            "--show-errors",
            f"--threads={threads}",  # use number of available CPU cores by default
            f"--base-directory={search_directory}",
            "--absolute-path",  # absolute path required as we cd to the base-directory
            "--regex",
            regex,
        ]
        + (["--type=directory"] if only_dir else []),
        text=True,
    ).splitlines()


@app.command()
def bigearthnet(
    target_dir: TargetDir,
    bigearthnet_s1_dir: DatasetDir = None,
    bigearthnet_s2_dir: DatasetDir = None,
):
    """
    [BigEarthNet-S1 and BigEarthNet-S2](https://doi.org/10.5281/zenodo.10891137) converter.
    If both source directories are given, both of them will be written to the same LMDB file.

    The LMDB keys will be the names of the BigEarthNet-S1/S2 patches (i.e., no `_BXY.tif` suffix).
    The `safetensors` keys relate to the associate band (for example: `B01`, `B8A`, `B12`, `VV`).
    """
    log.debug("Will first collect all files and ensure that some patches are found.")
    if (bigearthnet_s1_dir is None) and (bigearthnet_s2_dir is None):
        log.error("Please provide at least one directory path")
        exit(-1, "No source directory is specified")

    if bigearthnet_s1_dir is not None:
        log.info(f"Searching for patches in: {bigearthnet_s1_dir}")
        s1_patch_paths = fast_find(
            r"S1[AB]_IW_GRDH_.*_\d+_\d+$", bigearthnet_s1_dir, only_dir=True
        )
        num_s1_patch_paths = len(s1_patch_paths)
        log.debug(f"Found {num_s1_patch_paths} S1 patches.")
        assert num_s1_patch_paths > 0

    if bigearthnet_s2_dir is not None:
        log.info(f"Seaching for patches in: {bigearthnet_s2_dir}")

        s2_patch_paths = fast_find(
            r"S2[AB]_MSIL2A_.*_\d+_\d+$", bigearthnet_s2_dir, only_dir=True
        )
        # contains the paths
        num_s2_patch_paths = len(s2_patch_paths)
        log.debug(f"Found {num_s2_patch_paths} S2 patches.")
        assert num_s2_patch_paths > 0

    # postpone writing until AFTER both dataset files have been assembled.
    # Otherwise an error in the latter CLI argument could produce an incomplete LMDB
    env = open_lmdb(target_dir)

    if bigearthnet_s1_dir is not None:
        log.debug("Writing BigEarthNet-S1 data into LMDB")
        lmdb_writer(env, s1_patch_paths, encode_stem, bigearthnet_s1_to_safetensor)

    if bigearthnet_s2_dir is not None:
        log.debug("Writing BigEarthNet-S2 data into LMDB")
        lmdb_writer(env, s2_patch_paths, encode_stem, bigearthnet_s2_to_safetensor)


def lmdb_writer(env, paths, lmdb_key_extractor_func, safetensor_generator):
    """
    A parallel LMDB writer.
    It takes an already opened LMDB `env` as an input and writes batched
    transactions to the DB.
    It will iterate in parallel over the paths and will call the
    `lmdb_key_extractor_func` and `safetensor_generator` on each provided `path`.
    The data is inserted in a sorted order to ensure stable and repeatable outputs.
    The function will NOT overwrite any data! If data would be overwritten, the program
    halts and exists the program with an error message.
    """
    # insertion order is important for reproducibility!
    paths.sort()
    log.debug("About to serialize data in chunks")
    # Keep the the individual processes around for as long as possible
    # to maximize efficiency
    # Use `spawn` as this is POSIX compliant and will be the default in the future:
    # https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods
    with ProcessPoolExecutor(
        max_workers=None, mp_context=mp.get_context("spawn")
    ) as executor:
        # chunk size limits the number of writes per transaction
        # and the maximum number of futures that needs to be processed
        # FUTURE: tqdm call could be optimized
        for paths_chunk in tqdm(list(chunked(paths, 512))):
            with env.begin(write=True) as txn:
                futures_to_path = {
                    executor.submit(safetensor_generator, path): path
                    for path in paths_chunk
                }
                # To ensure deterministic output, write in order
                # i.e., cannot use `as_completed(futures_to_path)` !
                for future in futures_to_path:
                    if not txn.put(
                        lmdb_key_extractor_func(futures_to_path[future]),
                        future.result(),
                        overwrite=False,
                    ):
                        sys.exit(
                            "Program about to overwriting data in the DB. Stopping execution!"
                        )


def main():
    app()


if __name__ == "__main__":
    main()
