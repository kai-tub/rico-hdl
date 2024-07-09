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


def test_reproducibility_and_data_consistency(
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


def test_bigearthnet_integration(
    s1_root, s2_root, encoded_bigearthnet_s1_s2_path, bigearthnet_lmdb_ref_path
):
    env = lmdb.open(str(encoded_bigearthnet_s1_s2_path), readonly=True)

    with env.begin(write=False) as txn:
        cur = txn.cursor()
        decoded_lmdb_data = {k.decode("utf-8"): load(v) for (k, v) in cur}

    assert decoded_lmdb_data.keys() == set(
        [
            "S1A_IW_GRDH_1SDV_20170613T165043_33UUP_70_48",
            "S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP_75_43",
        ]
    )

    sample_s1_safetensors_dict = decoded_lmdb_data.get(
        "S1A_IW_GRDH_1SDV_20170613T165043_33UUP_70_48"
    )
    sample_s2_safetensors_dict = decoded_lmdb_data.get(
        "S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP_75_43"
    )
    safetensors_s1_keys = sample_s1_safetensors_dict.keys()
    safetensors_s2_keys = sample_s2_safetensors_dict.keys()
    assert (
        set(
            [
                "B01",
                "B02",
                "B03",
                "B04",
                "B05",
                "B06",
                "B07",
                "B08",
                "B8A",
                "B09",
                "B11",
                "B12",
            ]
        )
        == safetensors_s2_keys
    )
    assert (
        set(
            [
                "VV",
                "VH",
            ]
        )
        == safetensors_s1_keys
    )

    assert all(arr.shape == (120, 120) for arr in sample_s1_safetensors_dict.values())
    assert all(arr.dtype == "float32" for arr in sample_s1_safetensors_dict.values())

    assert all(arr.dtype == "uint16" for arr in sample_s2_safetensors_dict.values())
    assert all(
        sample_s2_safetensors_dict[key].shape == (120, 120)
        for key in ["B02", "B03", "B04", "B08"]
    )
    assert all(
        sample_s2_safetensors_dict[key].shape == (60, 60)
        for key in ["B05", "B06", "B07", "B8A", "B11", "B12"]
    )
    assert all(
        sample_s2_safetensors_dict[key].shape == (20, 20) for key in ["B01", "B09"]
    )


def test_hyspecnet_integration(hyspecnet_root, encoded_hyspecnet_path):
    env = lmdb.open(str(encoded_hyspecnet_path), readonly=True)

    with env.begin(write=False) as txn:
        cur = txn.cursor()
        decoded_lmdb_data = {k.decode("utf-8"): load(v) for (k, v) in cur}

    lmdb_keys = decoded_lmdb_data.keys()

    # only have two samples
    assert len(lmdb_keys) == 2

    assert (
        "ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X03110438"
        in lmdb_keys
    )
    assert (
        "ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X04390566"
        in lmdb_keys
    )

    sample_safetensors_dict = decoded_lmdb_data.get(
        "ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X03110438"
    )
    safetensors_keys = sample_safetensors_dict.keys()
    assert "B1" in safetensors_keys
    assert "B100" in safetensors_keys
    assert "B224" in safetensors_keys

    assert "B0" not in safetensors_keys
    assert "B01" not in safetensors_keys
    assert "B225" not in safetensors_keys

    assert all(arr.shape == (128, 128) for arr in sample_safetensors_dict.values())
    assert all(arr.dtype == "int16" for arr in sample_safetensors_dict.values())


@pytest.mark.filterwarnings("ignore:Dataset has no geotransform")
def test_uc_merced_integration(uc_merced_root, encoded_uc_merced_path):
    env = lmdb.open(str(encoded_uc_merced_path), readonly=True)

    with env.begin(write=False) as txn:
        cur = txn.cursor()
        decoded_lmdb_data = {k.decode("utf-8"): load(v) for (k, v) in cur}

    lmdb_keys = decoded_lmdb_data.keys()
    assert lmdb_keys == set(["airplane00", "airplane42", "forest10", "forest99"])

    sample_safetensors_dict = decoded_lmdb_data.get("airplane00")
    safetensors_keys = sample_safetensors_dict.keys()
    assert set(["Red", "Green", "Blue"]) == safetensors_keys

    assert all(arr.shape == (256, 256) for arr in sample_safetensors_dict.values())
    assert all(arr.dtype == "uint8" for arr in sample_safetensors_dict.values())


def test_eurosat_integration(eurosat_ms_root, encoded_eurosat_ms_path):
    env = lmdb.open(str(encoded_eurosat_ms_path), readonly=True)

    with env.begin(write=False) as txn:
        cur = txn.cursor()
        decoded_lmdb_data = {k.decode("utf-8"): load(v) for (k, v) in cur}

    decoded_lmdb_data.keys() == set(["AnnualCrop_1", "Pasture_300", "SeaLake_3000"])

    sample_safetensors_dict = decoded_lmdb_data.get("AnnualCrop_1")
    safetensors_keys = sample_safetensors_dict.keys()
    assert (
        set(
            [
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
        )
        == safetensors_keys
    )

    assert all(arr.shape == (64, 64) for arr in sample_safetensors_dict.values())
    assert all(arr.dtype == "uint16" for arr in sample_safetensors_dict.values())
