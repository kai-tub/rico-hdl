import os
import typer
from typing import TypeAlias, Optional
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

SSL4EO_S12_S1_ORDERING = ["VH", "VV"]
SSL4EO_S12_S2_L1C_ORDERING = [
    "B2",
    "B3",
    "B4",
    "B8",
    "B5",
    "B6",
    "B7",
    "B8A",
    "B10",
    "B11",
    "B12",
    "B1",
    "B9",
]

SSL4EO_S12_S2_L2A_ORDERING = [
    "B2",
    "B3",
    "B4",
    "B8",
    "B5",
    "B6",
    "B7",
    "B8A",
    "B11",
    "B12",
    "B1",
    "B9",
]

# Defined in the order of the bands!
# Order taken from (and only implicitely confirmed in):
# https://github.com/phelber/EuroSAT/issues/7#issuecomment-916754970
# Visualizing the individual bands supports the ordering, as one
# can see the different interpolation strengths for the 20 and 60m
# bands.
# This should be index band mapping and the ordering within the saftensor
# can then be independent
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

# Same as BigEarthNet ordering
# for whatever reason decided to use lower case here
MAJOR_TOM_S1_ORDERING = ["vh", "vv"]

MAJOR_TOM_S2_ORDERING = [
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

NUM_HYSPECNET_BANDS = 224
# see output of `gdalinfo`
UC_MERCED_BAND_IDX_COLOR_MAPPING = {1: "Red", 2: "Green", 3: "Blue"}

HYDRO_BAND_IDX_BAND_MAPPING = {
    1: "B01",
    2: "B02",
    3: "B03",
    4: "B04",
    5: "B05",
    6: "B06",
    7: "B07",
    8: "B08",
    9: "B8A",
    10: "B09",
    11: "B11",
    12: "B12",
}

GENERAL_HELP_TEXT = """\
This CLI tool is a fast and easy-to-use *r*emote sensing *i*mage format *co*nverter
for *h*igh-throughput *d*eep-*l*earning (rico-hdl).
It iterates over the source files of a given dataset and converts the individual bands
into safetensor dictionary entries and write the result into the high-throughput
LMDB database at the given `target_dir` location.
"""

app = typer.Typer(help=GENERAL_HELP_TEXT, rich_markup_mode="markdown")

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


def ssl4eo_s1_to_safetensor(patch_path: str) -> bytes:
    """
    Given the path to a SSL4EO-S12-S1 patch directory
    (NOT the individual TIFF files), read the individual
    band files in a pre-defined order and convert it
    into a serialized safetensor dictionary.
    """
    # In Python the dictionary insertion order is stable!
    # order the data here to make it clear that we are doing it
    # to order the safetensor entries!
    p = Path(patch_path)
    data = {
        band: read_single_band_raster(p.joinpath(f"{band}.tif"))
        for band in SSL4EO_S12_S1_ORDERING
    }
    return save(data, metadata=None)


def ssl4eo_s2_l1c_to_safetensor(patch_path: str) -> bytes:
    """
    Given the path to a SSL4EO-S12-S2 L1C patch directory
    (NOT the individual TIFF files), read the individual
    band files in a pre-defined order and convert it
    into a serialized safetensor dictionary.
    """
    # In Python the dictionary insertion order is stable!
    # order the data here to make it clear that we are doing it
    # to order the safetensor entries!
    p = Path(patch_path)
    data = {
        band: read_single_band_raster(p.joinpath(f"{band}.tif"))
        for band in SSL4EO_S12_S2_L1C_ORDERING
    }
    return save(data, metadata=None)


def ssl4eo_s2_l2a_to_safetensor(patch_path: str) -> bytes:
    """
    Given the path to a SSL4EO-S12-S2 L2A patch directory
    (NOT the individual TIFF files), read the individual
    band files in a pre-defined order and convert it
    into a serialized safetensor dictionary.
    """
    # In Python the dictionary insertion order is stable!
    # order the data here to make it clear that we are doing it
    # to order the safetensor entries!
    p = Path(patch_path)
    data = {
        band: read_single_band_raster(p.joinpath(f"{band}.tif"))
        for band in SSL4EO_S12_S2_L2A_ORDERING
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
        band: read_single_band_raster(p.joinpath(f"{p.stem}_{band}.tif"))
        for band in BIGEARTHNET_S2_ORDERING
    }
    return save(data, metadata=None)


def bigearthnet_reference_map_to_safetensor(reference_map_path: str) -> bytes:
    """
    Given the path to a BigEarthNet-Reference-Map TIFF file
    (NOT the parent directory), read the single band
    and convert it into a serialized safetensor dictionary with the key
    `Data`.
    """
    p = Path(reference_map_path)
    data = {"Data": read_single_band_raster(p)}
    return save(data, metadata=None)


def major_tom_core_s1_to_safetensor(patch_path: str) -> bytes:
    """
    Given the path to a Major TOM Core S1 patch directory
    (NOT the individual TIFF files), read the individual
    band files in a pre-defined order and convert it
    into a serialized safetensor dictionary.
    """
    # In Python the dictionary insertion order is stable!
    # order the data here to make it clear that we are doing it
    # to order the safetensor entries!
    p = Path(patch_path)
    data = {
        band: read_single_band_raster(p.joinpath(f"{band}.tif"))
        for band in MAJOR_TOM_S1_ORDERING
    }
    return save(data, metadata=None)


def major_tom_core_s2_to_safetensor(patch_path: str) -> bytes:
    """
    Given the path to a Major TOM Core S2 patch directory
    (NOT the individual TIFF files), read the individual
    band files in a pre-defined order and convert it
    into a serialized safetensor dictionary.
    """
    # In Python the dictionary insertion order is stable!
    # order the data here to make it clear that we are doing it
    # to order the safetensor entries!
    p = Path(patch_path)
    data = {
        band: read_single_band_raster(p.joinpath(f"{band}.tif"))
        for band in MAJOR_TOM_S2_ORDERING
    }
    return save(data, metadata=None)


@app.command()
def uc_merced(
    target_dir: TargetDir,
    dataset_dir: DatasetDir,
    num_workers: Annotated[int, typer.Option(min=1)] = None,
):
    """
    [UC Merced Land Use Dataset](http://weegee.vision.ucmerced.edu/datasets/landuse.html) converter.

    The LMDB keys will be the names of the UC Merced patches without the `.tif` suffix.

    The `safetensor` keys are [`Red`, `Green`, `Blue`] to indicate the respective
    channel meaning.

    NOTE: `num_workers` defaults to number of available threads.
    """
    # FUTURE: Allow keeping it together and only have a single joined RGB tensor
    # -> This is possible but kinda defeats the purpose of wrapping it in a saftensor
    # For such a small dataset, it would be interesting to know if this extra stacking
    # costs a lot of time.
    log.info(f"Searching for patches in: {dataset_dir}")
    patch_paths = fast_find(r".*\d\d\.tif$", dataset_dir, only_dir=False)
    num_patch_paths = len(patch_paths)
    log.debug(f"Found {num_patch_paths} patches.")
    assert num_patch_paths > 0
    env = open_lmdb(target_dir)
    log.debug("Writing UC Merced data into LMDB")
    lmdb_writer(
        env, patch_paths, encode_stem, uc_merced_to_safetensor, max_workers=num_workers
    )


@app.command()
def hydro(
    target_dir: TargetDir,
    dataset_dir: DatasetDir,
    num_workers: Annotated[int, typer.Option(min=1)] = None,
):
    """
    [Hydro -- A Foundation Model for Water in Sattelite Imagery](https://github.com/isaaccorley/hydro-foundation-model/tree/main) converter.

    The LMDB keys will be the names of the Hydro patches without the `.tif` suffix.

    The `safetensor` keys are the indexes from the tiff file mapped to the Sentinel-2
    Band value.


    References:
    - Publication: <https://github.com/isaaccorley/hydro-foundation-model/tree/main>
    - Dataset: <https://huggingface.co/datasets/isaaccorley/Hydro/tree/main>
    - Mapping source: <https://github.com/isaaccorley/hydro-foundation-model/issues/4>


    NOTE: `num_workers` defaults to number of available threads.
    """
    log.info(f"Searching for patches in: {dataset_dir}")
    # the lmdb key will be the name itself without .tif suffix
    # and the safetensor would be produced from this file
    # Remember: Hydro has multiple bands per file!
    patch_paths = fast_find(r"patch_\d+.tif$", dataset_dir, only_dir=False)
    num_patch_paths = len(patch_paths)
    log.debug(f"Found {num_patch_paths} patches.")
    assert num_patch_paths > 0
    env = open_lmdb(target_dir)
    log.debug("Writing Hydro data into LMDB")
    lmdb_writer(
        env,
        patch_paths,
        encode_stem,
        hydro_to_safetensor,
        max_workers=num_workers,
    )


# I will only add support for the RGB version if somebody explicitely asks
# for it. I want to encourage users to use the actual tiff data instead.
@app.command()
def eurosat_multi_spectral(
    target_dir: TargetDir,
    dataset_dir: DatasetDir,
    num_workers: Annotated[int, typer.Option(min=1)] = None,
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

    NOTE: `num_workers` defaults to number of available threads.
    """
    log.info(f"Searching for patches in: {dataset_dir}")
    # this could match the file paths directly
    patch_paths = fast_find(r".*\d+\.tif$", dataset_dir, only_dir=False)
    num_patch_paths = len(patch_paths)
    log.debug(f"Found {num_patch_paths} patches.")
    assert num_patch_paths > 0
    env = open_lmdb(target_dir)
    log.debug("Writing EuroSAT_MS data into LMDB")
    # Understand what the Band mapping is!
    lmdb_writer(
        env, patch_paths, encode_stem, eurosat_ms_to_safetensor, max_workers=num_workers
    )


@app.command()
def hyspecnet_11k(
    target_dir: TargetDir,
    dataset_dir: DatasetDir,
    num_workers: Annotated[int, typer.Option(min=1)] = None,
):
    """
    [HySpecNet-11k](https://datadryad.org/stash/dataset/doi:10.5061/dryad.fttdz08zh) converter.

    The LMDB keys will be the names of the HySpecNet-11k patches without the
    `-SPECTRAL_IMAGE.TIF` suffix.
    The `safetensors` keys are the band numbers prefixed with `B`
    (for example: `B1`, `B12`, `B122`).

    NOTE: Band indexes start with 1 and not 0!

    NOTE: `num_workers` defaults to number of available threads.
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
    lmdb_writer(
        env, patch_paths, encode_stem, hyspecnet_to_safetensor, max_workers=num_workers
    )


def encode_stem(path: str) -> bytes:
    """
    Given a path extract the stem and encode the string.
    """
    return str(Path(path).stem).encode()


# yeah, this could be done more generic but it can still be refactored
# if it is really needed in different variations.
def encode_with_parent(path: str, join_char: str = "_") -> bytes:
    """
    Given a path that is at least one parent directory, concatenate the
    directory name and the current file.

    Example: `/home/user/patch/band` -> `patch_band`
    """
    p = Path(path)
    return join_char.join([p.parent.name, p.name]).encode()


def encode_three_levels(path: str, join_char: str = "_") -> bytes:
    """
    Given a path that is at least three levels deep, concatenate the names
    of the three deepest names.

    Example: `/home/user/name/patch` -> `user_name_patch`
    """
    p = Path(path)
    return join_char.join([p.parent.parent.name, p.parent.name, p.name]).encode()


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


def hydro_to_safetensor(patch_path: str) -> bytes:
    """
    Given the path to a Hydro patch file (`.tif` file),
    read the individual bands and write them as entries
    into a serialized safetensor dictionary.
    """
    p = Path(patch_path)
    data = {
        band: read_single_band_raster(p, index=idx, is_georeferenced=False)
        for idx, band in HYDRO_BAND_IDX_BAND_MAPPING.items()
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
    exact_depth: Optional[int] = None,
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
        + (["--type=directory"] if only_dir else [])
        + ([f"--exact-depth={exact_depth}"] if exact_depth is not None else []),
        text=True,
    ).splitlines()


@app.command()
def bigearthnet(
    target_dir: TargetDir,
    bigearthnet_s1_dir: DatasetDir = None,
    bigearthnet_s2_dir: DatasetDir = None,
    bigearthnet_reference_maps_dir: DatasetDir = None,
    num_workers: Annotated[int, typer.Option(min=1)] = None,
):
    """
    [BigEarthNet-S1, BigEarthNet-S2, and BigEarthNet-Reference-Maps](https://doi.org/10.5281/zenodo.10891137) converter.

    If all three source directories are given, all three of them will be written to the same LMDB file.
    The LMDB keys will be the names of the BigEarthNet-S1/S2 patches patches (i.e., no `_BXY.tif` suffix)
    or Reference Maps (_includes_ the `_reference_map` suffix).

    The `safetensors` keys relate to the associate band (for example: `B01`, `B8A`, `B12`, `VV`).
    For the single band Reference-Maps, the `safetensor` key is `Data`.

    NOTE: `num_workers` defaults to number of available threads.
    """
    log.debug("Will first collect all files and ensure that some patches are found.")
    if (
        (bigearthnet_s1_dir is None)
        and (bigearthnet_s2_dir is None)
        and (bigearthnet_reference_maps_dir is None)
    ):
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
        log.info(f"Searching for patches in: {bigearthnet_s2_dir}")
        s2_patch_paths = fast_find(
            r"S2[AB]_MSIL2A_.*_\d+_\d+$", bigearthnet_s2_dir, only_dir=True
        )
        # contains the paths
        num_s2_patch_paths = len(s2_patch_paths)
        log.debug(f"Found {num_s2_patch_paths} S2 patches.")
        assert num_s2_patch_paths > 0

    if bigearthnet_reference_maps_dir is not None:
        log.info(f"Searching for reference maps in: {bigearthnet_reference_maps_dir}")
        reference_maps_paths = fast_find(
            r"S2[AB]_MSIL2A_.*_\d+_\d+_reference_map.tif$",
            bigearthnet_reference_maps_dir,
            only_dir=False,
        )
        # contains the paths
        num_reference_maps_paths = len(reference_maps_paths)
        log.debug(f"Found {num_reference_maps_paths} reference maps.")
        assert num_reference_maps_paths > 0

    # postpone writing until AFTER both dataset files have been assembled.
    # Otherwise an error in the latter CLI argument could produce an incomplete LMDB
    env = open_lmdb(target_dir)

    if bigearthnet_s1_dir is not None:
        log.debug("Writing BigEarthNet-S1 data into LMDB")
        lmdb_writer(
            env,
            s1_patch_paths,
            encode_stem,
            bigearthnet_s1_to_safetensor,
            max_workers=num_workers,
        )

    if bigearthnet_s2_dir is not None:
        log.debug("Writing BigEarthNet-S2 data into LMDB")
        lmdb_writer(
            env,
            s2_patch_paths,
            encode_stem,
            bigearthnet_s2_to_safetensor,
            max_workers=num_workers,
        )

    if bigearthnet_reference_maps_dir is not None:
        log.debug("Writing Reference Maps data into LMDB")
        lmdb_writer(
            env,
            reference_maps_paths,
            encode_stem,
            bigearthnet_reference_map_to_safetensor,
            max_workers=num_workers,
        )


@app.command()
def major_tom_core(
    target_dir: TargetDir,
    s1_dir: DatasetDir = None,
    s2_dir: DatasetDir = None,
    num_workers: Annotated[int, typer.Option(min=1)] = None,
):
    """
    [Major TOM Core S1 & S2](https://github.com/ESA-PhiLab/Major-TOM/tree/main) converter.

    If both source directories are given, both of them will be written to the same LMDB file.
    The LMDB keys will be the names of the patches/product ids (i.e., no band (`_BXY`) suffix) prefixed
    with the grid cell `X_Y_` to generate a unique name.
    The `safetensors` keys relate to the associate band (for example: `B01`, `B8A`, `B12`, `vv`).

    NOTE: Requires the data to be downloaded via the [official download script](https://github.com/ESA-PhiLab/Major-TOM/blob/main/src/metadata_helpers.py).
    NOTE: The `cloud_mask` is NOT encoded in the safetensor.
    NOTE: `num_workers` defaults to number of available threads.
    """
    log.debug("Will first collect all files and ensure that some patches are found.")
    if (s1_dir is None) and (s2_dir is None):
        log.error("Please provide at least one directory path")
        exit(-1, "No source directory is specified")

    if s1_dir is not None:
        log.info(f"Searching for patches in: {s1_dir}")
        s1_patch_paths = fast_find(r"S1[AB]_IW_GRDH_.*_rtc$", s1_dir, only_dir=True)
        num_s1_patch_paths = len(s1_patch_paths)
        log.debug(f"Found {num_s1_patch_paths} S1 patches.")
        assert num_s1_patch_paths > 0

    if s2_dir is not None:
        log.info(f"Seaching for patches in: {s2_dir}")
        s2_patch_paths = fast_find(r"S2[AB]_MSIL2A_.*_[0-9T]+$", s2_dir, only_dir=True)
        # contains the paths
        num_s2_patch_paths = len(s2_patch_paths)
        log.debug(f"Found {num_s2_patch_paths} S2 patches.")
        assert num_s2_patch_paths > 0

    # postpone writing until AFTER both dataset files have been assembled.
    # Otherwise an error in the latter CLI argument could produce an incomplete LMDB
    env = open_lmdb(target_dir)

    if s1_dir is not None:
        log.debug("Writing Major TOM Core S1 data into LMDB")
        lmdb_writer(
            env,
            s1_patch_paths,
            encode_with_parent,
            major_tom_core_s1_to_safetensor,
            max_workers=num_workers,
        )

    if s2_dir is not None:
        log.debug("Writing Major TOM Core data into LMDB")
        lmdb_writer(
            env,
            s2_patch_paths,
            encode_with_parent,
            major_tom_core_s2_to_safetensor,
            max_workers=num_workers,
        )


@app.command()
def ssl4eo_s12(
    target_dir: TargetDir,
    s1_dir: DatasetDir = None,
    s2_l1c_dir: DatasetDir = None,
    s2_l2a_dir: DatasetDir = None,
    num_workers: Annotated[int, typer.Option(min=1)] = None,
):
    """
    [SSL4EO-S12 Sentinel-1, Sentinel-2 L1C, and Sentinel-2 L2A](https://github.com/zhu-xlab/SSL4EO_S12-S12) converter.

    If all source directories are given, they will be written to the same LMDB file.
    The LMDB keys will be the normalized path to the patches where the two parent
    directories are merged with `_`.

    For example, the path:

    - `s1/0000200/S1A_IW_GRDH_1SDV_20200607T010800_20200607T010825_032904_03CFBA_D457/`

    would have the key

    - `s1_0000200_S1A_IW_GRDH_1SDV_20200607T010800_20200607T010825_032904_03CFBA_D457`

    and the path:

    - `s2a/0000200/20200604T054639_20200604T054831_T43RCP`

    would have the key

    - `s2a_0000200_20200604T054639_20200604T054831_T43RCP`

    ---

    The `safetensors` keys relate to the associate band (for example: `B1`, `B8A`, `VV`, `B10`),
    which depends on the selected sub-dataset.

    NOTE: We recommend to download the dataset from huggingface, as the download is much more reliable.
    To unpack the data simply run `cat s1*.tar.gz | tar -xzf -`
    NOTE: `num_workers` defaults to number of available threads.
    """
    log.debug("Will first collect all files and ensure that some patches are found.")

    if (s1_dir is None) and (s2_l1c_dir is None) and (s2_l2a_dir is None):
        log.error("Please provide at least one directory path")
        exit(-1, "No source directory is specified")

    if s1_dir is not None:
        log.info(f"Searching for patches in: {s1_dir}")
        # use fastest matching logic; will fail if directory has been touched or changed
        s1_patch_paths = fast_find(".", s1_dir, only_dir=True, exact_depth=2)
        num_s1_patch_paths = len(s1_patch_paths)
        log.debug(f"Found {num_s1_patch_paths} S1 patches.")
        assert num_s1_patch_paths > 0

    if s2_l1c_dir is not None:
        log.info(f"Seaching for patches in: {s2_l1c_dir}")
        s2_l1c_patch_paths = fast_find(".", s2_l1c_dir, only_dir=True, exact_depth=2)
        # use fastest matching logic; will fail if directory has been touched or changed
        num_s2_l1c_patch_paths = len(s2_l1c_patch_paths)
        log.debug(f"Found {num_s2_l1c_patch_paths} S2 L1C patches.")
        assert num_s2_l1c_patch_paths > 0

    if s2_l2a_dir is not None:
        log.info(f"Seaching for patches in: {s2_l2a_dir}")
        s2_l2a_patch_paths = fast_find(".", s2_l2a_dir, only_dir=True, exact_depth=2)
        # use fastest matching logic; will fail if directory has been touched or changed
        num_s2_l2a_patch_paths = len(s2_l2a_patch_paths)
        log.debug(f"Found {num_s2_l2a_patch_paths} S2 L2A patches.")
        assert num_s2_l2a_patch_paths > 0

    # postpone writing until AFTER both dataset files have been assembled.
    # Otherwise an error in the latter CLI argument could produce an incomplete LMDB
    env = open_lmdb(target_dir)

    # Above we are matching all directories that are two levels deep relative to
    # the given base directory. As the s2-l2a and s2-l1c sub-paths are identical
    # for a given tile, we need to embed the base directory name `s2c` and `s2a`
    # to allow writing a single LMDB file.
    # For consistency, we do the same for the S1 data
    if s1_dir is not None:
        log.debug("Writing SSL4EO-S12-S1 data into LMDB")
        lmdb_writer(
            env,
            s1_patch_paths,
            encode_three_levels,
            ssl4eo_s1_to_safetensor,
            max_workers=num_workers,
        )

    if s2_l1c_dir is not None:
        log.debug("Writing SSL4EO-S12-S2 L1C data into LMDB")
        lmdb_writer(
            env,
            s2_l1c_patch_paths,
            encode_three_levels,
            ssl4eo_s2_l1c_to_safetensor,
            max_workers=num_workers,
        )

    if s2_l2a_dir is not None:
        log.debug("Writing SSL4EO-S12-S2 L2A data into LMDB")
        lmdb_writer(
            env,
            s2_l2a_patch_paths,
            encode_three_levels,
            ssl4eo_s2_l2a_to_safetensor,
            max_workers=num_workers,
        )


def lmdb_writer(
    env, paths, lmdb_key_extractor_func, safetensor_generator, max_workers=None
):
    """
    A parallel LMDB writer.
    It takes an already opened LMDB `env` as an input and writes batched
    transactions to the DB.
    It will iterate in parallel over the paths and will call the
    `lmdb_key_extractor_func` and `safetensor_generator` on each provided `path`.
    The data is inserted in a sorted order to ensure stable and repeatable outputs.
    The function will NOT overwrite any data! If data would be overwritten, the program
    halts and exists the program with an error message.

    The number of parallel writers can be controlled via `max_workers`.
    """
    # insertion order is important for reproducibility!
    paths.sort()
    log.debug("About to serialize data in chunks")
    # Keep the the individual processes around for as long as possible
    # to maximize efficiency
    # Use `spawn` as this is POSIX compliant and will be the default in the future:
    # https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods
    with ProcessPoolExecutor(
        max_workers=max_workers, mp_context=mp.get_context("spawn")
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
                    p = futures_to_path[future]
                    if not txn.put(
                        lmdb_key_extractor_func(p),
                        future.result(),
                        overwrite=False,
                    ):
                        sys.exit(
                            f"Program about to overwriting data in the DB: with source {str(p)} Stopping execution!"
                        )


def main():
    app()


if __name__ == "__main__":
    main()
