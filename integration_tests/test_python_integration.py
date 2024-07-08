# I am kinda duplicating code.
# The main goal of these tests is to ensure that the data is not empty
# which may happen over time.
# And that the data can be loaded from the LMDB afterwards without any issues.
# This should ensure that the safetensor format also remains functional and reproducible
# But I do not think that I have to check if all encoded arrays remain identical for all datasets.
import lmdb
import rasterio
import numpy as np
from safetensors.numpy import load
import os
from pathlib import Path
import pytest
import subprocess
import hashlib
from rico_hdl.rico_hdl import EUROSAT_MS_BANDS


def read_single_band_raster(path):
    with rasterio.open(path) as r:
        return r.read(1)


@pytest.fixture(scope="session")
def s1_root() -> Path:
    str_p = os.environ.get("RICO_HDL_S1_PATH") or "./tiffs/BigEarthNet/BigEarthNet-S1/"
    p = Path(str_p)
    assert p.exists()
    assert p.is_dir()
    return p


@pytest.fixture(scope="session")
def bigearthnet_lmdb_ref_path() -> Path:
    str_p = os.environ.get("RICO_HDL_LMDB_REF_PATH") or "./BigEarthNet_LMDB/"
    p = Path(str_p)
    assert p.exists()
    assert p.is_dir()
    return p


@pytest.fixture(scope="session")
def s2_root() -> Path:
    str_p = os.environ.get("RICO_HDL_S2_PATH") or "./tiffs/BigEarthNet/BigEarthNet-S2/"
    p = Path(str_p)
    assert p.exists()
    assert p.is_dir()
    return p


@pytest.fixture(scope="session")
def hyspecnet_root() -> Path:
    str_p = os.environ.get("RICO_HDL_HYSPECNET_PATH") or "./tiffs/HySpecNet-11k/"
    p = Path(str_p)
    assert p.exists()
    assert p.is_dir()
    return p


@pytest.fixture(scope="session")
def uc_merced_root() -> Path:
    str_p = os.environ.get("RICO_HDL_UC_MERCED_PATH") or "./tiffs/UCMerced_LandUse/"
    p = Path(str_p)
    assert p.exists()
    assert p.is_dir()
    return p


@pytest.fixture(scope="session")
def eurosat_ms_root() -> Path:
    str_p = os.environ.get("RICO_HDL_EUROSAT_MS_PATH") or "./tiffs/EUROSAT_MS/"
    p = Path(str_p)
    assert p.exists()
    assert p.is_dir()
    return p


# https://docs.pytest.org/en/6.2.x/tmpdir.html#tmpdir-factory-example@pytest.fixture(scope="session")
@pytest.fixture
def encoded_bigearthnet_s1_s2_path(s1_root, s2_root, tmpdir_factory) -> Path:
    tmp_path = tmpdir_factory.mktemp("lmdb")
    # This should make it easier to separately test different versions of the binary and the appimage as well
    subprocess.run(
        [
            "rico-hdl",
            "bigearthnet",
            f"--bigearthnet-s1-dir={s1_root}",
            f"--bigearthnet-s2-dir={s2_root}",
            f"--target-dir={tmp_path}",
        ],
        check=True,
    )
    return Path(tmp_path)


@pytest.fixture
def encoded_hyspecnet_path(hyspecnet_root, tmpdir_factory) -> Path:
    tmp_path = tmpdir_factory.mktemp("hyspec_lmdb")
    subprocess.run(
        [
            "rico-hdl",
            "hyspecnet-11k",
            f"--dataset-dir={hyspecnet_root}",
            f"--target-dir={tmp_path}",
        ],
        check=True,
    )
    return Path(tmp_path)


@pytest.fixture
def encoded_uc_merced_path(uc_merced_root, tmpdir_factory) -> Path:
    tmp_path = tmpdir_factory.mktemp("uc_merced_lmdb")
    subprocess.run(
        [
            "rico-hdl",
            "uc-merced",
            f"--dataset-dir={uc_merced_root}",
            f"--target-dir={tmp_path}",
        ],
        check=True,
    )
    return Path(tmp_path)


@pytest.fixture
def encoded_eurosat_ms_path(eurosat_ms_root, tmpdir_factory) -> Path:
    tmp_path = tmpdir_factory.mktemp("eurosat_ms_lmdb")
    subprocess.run(
        [
            "rico-hdl",
            "eurosat-multi-spectral",
            f"--dataset-dir={eurosat_ms_root}",
            f"--target-dir={tmp_path}",
        ],
        check=True,
    )
    return Path(tmp_path)


def test_bigearthnet_integration(
    s1_root, s2_root, encoded_bigearthnet_s1_s2_path, bigearthnet_lmdb_ref_path
):
    s1_data = {file: read_single_band_raster(file) for file in s1_root.glob("**/*.tif")}
    s2_data = {file: read_single_band_raster(file) for file in s2_root.glob("**/*.tif")}
    source_data = {**s1_data, **s2_data}
    env = lmdb.open(str(encoded_bigearthnet_s1_s2_path), readonly=True)

    with env.begin(write=False) as txn:
        cur = txn.cursor()
        decoded_lmdb_data = {k.decode("utf-8"): load(v) for (k, v) in cur}

    # The encoded data is nested inside of another safetensor dictionary, where the inner keys are derived from the band suffix
    decoded_values = [
        v for outer_v in decoded_lmdb_data.values() for v in outer_v.values()
    ]

    # Simply check if the data remains identical, as this is the only _true_ thing I care about from the Python viewpoint
    # If the keys/order or anything else is wrong, it isn't part of the integration test but should be handled separately as a unit test!
    for source_key, source_value in source_data.items():
        assert any(
            np.array_equal(source_value, decoded_value)
            for decoded_value in decoded_values
        ), f"Couldn't find data in the LMDB database that matches the data from: {source_key}"

    # LMDB consistency check
    with encoded_bigearthnet_s1_s2_path.joinpath("data.mdb").open(mode="rb") as f:
        encoded_hash = hashlib.file_digest(f, "sha256").hexdigest()

    with bigearthnet_lmdb_ref_path.joinpath("data.mdb").open(mode="rb") as f:
        reference_hash = hashlib.file_digest(f, "sha256").hexdigest()

    assert (
        encoded_hash == reference_hash
    ), "The newly generated LMDB file has a different hash compared to the reference one!"


def read_all_hyspecnet_bands(path):
    """
    Given a path to a GeoTIFF return all bands as a dictionary,
    where the key is the unformatted band index (starting from 1)
    as a string and the value the array data
    """
    with rasterio.open(path) as r:
        return {f"B{i}": r.read(i) for i in range(1, r.count + 1)}


def test_hyspecnet_integration(hyspecnet_root, encoded_hyspecnet_path):
    source_file_data = {
        file: read_all_hyspecnet_bands(file)
        for file in hyspecnet_root.glob("**/*SPECTRAL_IMAGE.TIF")
    }
    assert len(source_file_data) > 0

    # code to create the directory
    # ./result/bin/encoder --hyspecnet-11k <PATH> hyspec_artifacts/
    env = lmdb.open(str(encoded_hyspecnet_path), readonly=True)

    with env.begin(write=False) as txn:
        cur = txn.cursor()
        decoded_lmdb_data = {k.decode("utf-8"): load(v) for (k, v) in cur}

    # The encoded data is nested inside of another safetensor dictionary,
    # where the inner keys are derived from the band number as a string
    decoded_dicts = [d for d in decoded_lmdb_data.values()]

    # Simply check if the data remains identical, as this is the only _true_ thing I care about from the Python viewpoint
    # Here I iterate over all file name and raster data as dictionaries pairs
    # and then for each raster data dictionary iterate over all key-value pairs, where the key is the band name
    # in the same style as the LMDB file and check if the LMDB file contained a matching array from
    # a safetensors dictionary accessed via the shared band name as key.
    for source_file, source_data_dict in source_file_data.items():
        for source_key, source_data in source_data_dict.items():
            assert any(
                np.array_equal(source_data, decoded_dict[source_key])
                for decoded_dict in decoded_dicts
            ), f"Couldn't find data in the LMDB database that matches the data from: {source_file}:{source_key}"


def read_all_uc_merced_bands(path):
    """
    Given a path to a UC Merced TIFF file return all bands as a dictionary,
    where the keys are the color value
    """
    with rasterio.open(path) as r:
        return {key: r.read(i) for i, key in enumerate(["Red", "Green", "Blue"], 1)}


@pytest.mark.filterwarnings("ignore:Dataset has no geotransform")
def test_uc_merced_integration(uc_merced_root, encoded_uc_merced_path):
    source_file_data = {
        file: read_all_uc_merced_bands(file) for file in uc_merced_root.glob("**/*.tif")
    }
    assert len(source_file_data) > 0

    # code to create the directory
    # ./result/bin/encoder --hyspecnet-11k <PATH> hyspec_artifacts/
    env = lmdb.open(str(encoded_uc_merced_path), readonly=True)

    with env.begin(write=False) as txn:
        cur = txn.cursor()
        decoded_lmdb_data = {k.decode("utf-8"): load(v) for (k, v) in cur}

    # The encoded data is nested inside of another safetensor dictionary,
    # where the inner keys are derived from color mapping
    decoded_dicts = [d for d in decoded_lmdb_data.values()]

    # Simply check if the data remains identical, as this is the only _true_ thing I care about from the Python viewpoint
    # Here I iterate over all file name and raster data as dictionaries pairs
    # and then for each raster data dictionary iterate over all key-value pairs, where the key is the band name
    # in the same style as the LMDB file and check if the LMDB file contained a matching array from
    # a safetensors dictionary accessed via the shared band name as key.
    for source_file, source_data_dict in source_file_data.items():
        for source_key, source_data in source_data_dict.items():
            assert any(
                np.array_equal(source_data, decoded_dict[source_key])
                for decoded_dict in decoded_dicts
            ), f"Couldn't find data in the LMDB database that matches the data from: {source_file}:{source_key}"


def read_all_eurosat_ms_bands(path):
    """
    Given a path to a TIFF file return all bands as a dictionary,
    where the keys are the EuroSAT MS band value
    """
    with rasterio.open(path) as r:
        return {key: r.read(i) for i, key in enumerate(EUROSAT_MS_BANDS, start=1)}


def test_eurosat_integration(eurosat_ms_root, encoded_eurosat_ms_path):
    source_file_data = {
        file: read_all_eurosat_ms_bands(file)
        for file in eurosat_ms_root.glob("**/*.tif")
    }
    assert len(source_file_data) > 0

    env = lmdb.open(str(encoded_eurosat_ms_path), readonly=True)

    with env.begin(write=False) as txn:
        cur = txn.cursor()
        decoded_lmdb_data = {k.decode("utf-8"): load(v) for (k, v) in cur}

    # The encoded data is nested inside of another safetensor dictionary,
    # where the inner keys are derived from color mapping
    decoded_dicts = [d for d in decoded_lmdb_data.values()]

    # Simply check if the data remains identical, as this is the only _true_ thing I care about from the Python viewpoint
    # Here I iterate over all file name and raster data as dictionaries pairs
    # and then for each raster data dictionary iterate over all key-value pairs, where the key is the band name
    # in the same style as the LMDB file and check if the LMDB file contained a matching array from
    # a safetensors dictionary accessed via the shared band name as key.
    for source_file, source_data_dict in source_file_data.items():
        for source_key, source_data in source_data_dict.items():
            assert any(
                np.array_equal(source_data, decoded_dict[source_key])
                for decoded_dict in decoded_dicts
            ), f"Couldn't find data in the LMDB database that matches the data from: {source_file}:{source_key}"
