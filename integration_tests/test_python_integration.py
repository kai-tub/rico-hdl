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
def bigearthnet_s1_root() -> Path:
    str_p = os.environ.get("RICO_HDL_S1_PATH") or "./tiffs/BigEarthNet/BigEarthNet-S1/"
    p = Path(str_p)
    assert p.exists()
    assert p.is_dir()
    return p


@pytest.fixture(scope="session")
def bigearthnet_s2_root() -> Path:
    str_p = os.environ.get("RICO_HDL_S2_PATH") or "./tiffs/BigEarthNet/BigEarthNet-S2/"
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
def ssl4eo_s12_s1_root() -> Path:
    str_p = os.environ.get("RICO_HDL_SSL4EO_S12_S1_PATH") or "./tiffs/SSL4EO-S12/s1/"
    p = Path(str_p)
    assert p.exists()
    assert p.is_dir()
    return p


@pytest.fixture(scope="session")
def ssl4eo_s12_s2_l1c_root() -> Path:
    str_p = (
        os.environ.get("RICO_HDL_SSL4EO_S12_S2_L1C_PATH") or "./tiffs/SSL4EO-S12/s2c/"
    )
    p = Path(str_p)
    assert p.exists()
    assert p.is_dir()
    return p


@pytest.fixture(scope="session")
def ssl4eo_s12_s2_l2a_root() -> Path:
    str_p = (
        os.environ.get("RICO_HDL_SSL4EO_S12_S2_L2A_PATH") or "./tiffs/SSL4EO-S12/s2a/"
    )
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
def hydro_root() -> Path:
    str_p = os.environ.get("RICO_HDL_HYDRO_PATH") or "./tiffs/Hydro/"
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


@pytest.fixture(scope="session")
def major_tom_core_s1_root() -> Path:
    str_p = (
        os.environ.get("RICO_HDL_MAJOR_TOM_CORE_S1_PATH")
        or "./tiffs/Major-TOM-Core/S1RTC/"
    )
    p = Path(str_p)
    assert p.exists()
    assert p.is_dir()
    return p


@pytest.fixture(scope="session")
def major_tom_core_s2_root() -> Path:
    str_p = (
        os.environ.get("RICO_HDL_MAJOR_TOM_CORE_S2_PATH")
        or "./tiffs/Major-TOM-Core/S2L2A/"
    )
    p = Path(str_p)
    assert p.exists()
    assert p.is_dir()
    return p


@pytest.fixture
def encoded_major_tom_core_path(
    major_tom_core_s1_root, major_tom_core_s2_root, tmpdir_factory
) -> Path:
    tmp_path = tmpdir_factory.mktemp("lmdb")
    subprocess.run(
        [
            "rico-hdl",
            "major-tom-core",
            f"--s1-dir={major_tom_core_s1_root}",
            f"--s2-dir={major_tom_core_s2_root}",
            f"--target-dir={tmp_path}",
        ],
        check=True,
    )
    return Path(tmp_path)


# https://docs.pytest.org/en/6.2.x/tmpdir.html#tmpdir-factory-example@pytest.fixture(scope="session")
@pytest.fixture
def encoded_bigearthnet_s1_s2_path(
    bigearthnet_s1_root, bigearthnet_s2_root, tmpdir_factory
) -> Path:
    tmp_path = tmpdir_factory.mktemp("lmdb")
    subprocess.run(
        [
            "rico-hdl",
            "bigearthnet",
            f"--bigearthnet-s1-dir={bigearthnet_s1_root}",
            f"--bigearthnet-s2-dir={bigearthnet_s2_root}",
            f"--target-dir={tmp_path}",
        ],
        check=True,
    )
    return Path(tmp_path)


@pytest.fixture
def encoded_ssl4eo_s12_path(
    ssl4eo_s12_s1_root, ssl4eo_s12_s2_l1c_root, ssl4eo_s12_s2_l2a_root, tmpdir_factory
) -> Path:
    tmp_path = tmpdir_factory.mktemp("lmdb")
    subprocess.run(
        [
            "rico-hdl",
            "ssl4eo-s12",
            f"--s1-dir={ssl4eo_s12_s1_root}",
            f"--s2-l1c-dir={ssl4eo_s12_s2_l1c_root}",
            f"--s2-l2a-dir={ssl4eo_s12_s2_l2a_root}",
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
def encoded_hydro_path(hydro_root, tmpdir_factory) -> Path:
    tmp_path = tmpdir_factory.mktemp("hydro_lmdb")
    subprocess.run(
        [
            "rico-hdl",
            "hydro",
            f"--dataset-dir={hydro_root}",
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
    bigearthnet_s1_root,
    bigearthnet_s2_root,
    encoded_bigearthnet_s1_s2_path,
    bigearthnet_lmdb_ref_path,
):
    s1_data = {
        file: read_single_band_raster(file)
        for file in bigearthnet_s1_root.glob("**/*.tif")
    }
    s2_data = {
        file: read_single_band_raster(file)
        for file in bigearthnet_s2_root.glob("**/*.tif")
    }
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
    bigearthnet_s1_root,
    bigearthnet_s2_root,
    encoded_bigearthnet_s1_s2_path,
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


def test_major_tom_core_integration(
    major_tom_core_s1_root, major_tom_core_s2_root, encoded_major_tom_core_path
):
    env = lmdb.open(str(encoded_major_tom_core_path), readonly=True)

    with env.begin(write=False) as txn:
        cur = txn.cursor()
        decoded_lmdb_data = {k.decode("utf-8"): load(v) for (k, v) in cur}

    assert decoded_lmdb_data.keys() == set(
        [
            "0U_199R_S1A_IW_GRDH_1SDV_20220703T043413_20220703T043438_043931_053E87_rtc",
            "897U_171R_S1B_IW_GRDH_1SDV_20210827T012624_20210827T012653_028425_036437_rtc",
            "0U_199R_S2A_MSIL2A_20220706T085611_N0400_R007_T33NZA_20220706T153419",
            "199U_1099R_S2B_MSIL2A_20200223T032739_N9999_R018_T48QUE_20230924T183543",
        ]
    )

    sample_s1_safetensors_dict = decoded_lmdb_data.get(
        "0U_199R_S1A_IW_GRDH_1SDV_20220703T043413_20220703T043438_043931_053E87_rtc",
    )
    sample_s2_safetensors_dict = decoded_lmdb_data.get(
        "0U_199R_S2A_MSIL2A_20220706T085611_N0400_R007_T33NZA_20220706T153419"
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
                "vv",
                "vh",
            ]
        )
        == safetensors_s1_keys
    )

    assert all(arr.shape == (1068, 1068) for arr in sample_s1_safetensors_dict.values())
    assert all(arr.dtype == "float32" for arr in sample_s1_safetensors_dict.values())

    assert all(arr.dtype == "uint16" for arr in sample_s2_safetensors_dict.values())
    assert all(
        sample_s2_safetensors_dict[key].shape == (1068, 1068)
        for key in ["B02", "B03", "B04", "B08"]
    )
    assert all(
        sample_s2_safetensors_dict[key].shape == (534, 534)
        for key in ["B05", "B06", "B07", "B8A", "B11", "B12"]
    )
    assert all(
        sample_s2_safetensors_dict[key].shape == (178, 178) for key in ["B01", "B09"]
    )


def test_ssl4eo_s12_integration(
    ssl4eo_s12_s1_root,
    ssl4eo_s12_s2_l1c_root,
    ssl4eo_s12_s2_l2a_root,
    encoded_ssl4eo_s12_path,
):
    env = lmdb.open(str(encoded_ssl4eo_s12_path), readonly=True)

    with env.begin(write=False) as txn:
        cur = txn.cursor()
        decoded_lmdb_data = {k.decode("utf-8"): load(v) for (k, v) in cur}

    assert decoded_lmdb_data.keys() == set(
        [
            "s1_0000200_S1A_IW_GRDH_1SDV_20200607T010800_20200607T010825_032904_03CFBA_D457",
            "s1_0000200_S1A_IW_GRDH_1SDV_20200903T131212_20200903T131237_034195_03F8F5_AC1C",
            "s2a_0000200_20200604T054639_20200604T054831_T43RCP",
            "s2a_0000200_20200813T054639_20200813T054952_T43RCP",
            "s2c_0000200_20200604T054639_20200604T054831_T43RCP",
            "s2c_0000200_20200823T054639_20200823T055618_T43RCP",
        ]
    )

    sample_s1_safetensors_dict = decoded_lmdb_data.get(
        "s1_0000200_S1A_IW_GRDH_1SDV_20200607T010800_20200607T010825_032904_03CFBA_D457"
    )
    sample_s2_l1c_safetensors_dict = decoded_lmdb_data.get(
        "s2c_0000200_20200604T054639_20200604T054831_T43RCP"
    )
    sample_s2_l2a_safetensors_dict = decoded_lmdb_data.get(
        "s2a_0000200_20200604T054639_20200604T054831_T43RCP"
    )
    safetensors_s1_keys = sample_s1_safetensors_dict.keys()
    safetensors_s2_l1c_keys = sample_s2_l1c_safetensors_dict.keys()
    safetensors_s2_l2a_keys = sample_s2_l2a_safetensors_dict.keys()
    assert (
        set(
            [
                "B1",
                "B2",
                "B3",
                "B4",
                "B5",
                "B6",
                "B7",
                "B8",
                "B8A",
                "B9",
                "B10",
                "B11",
                "B12",
            ]
        )
        == safetensors_s2_l1c_keys
    )
    assert (
        set(
            [
                "B1",
                "B2",
                "B3",
                "B4",
                "B5",
                "B6",
                "B7",
                "B8",
                "B8A",
                "B9",
                "B11",
                "B12",
            ]
        )
        == safetensors_s2_l2a_keys
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

    # IMPORTANT!
    # The SSL4EO-S12 authors didn't pay attention to the resulting size of the patches!
    # Some have an extra row/column of pixels!
    # This assertion does NOT hold over the entire dataset!
    assert all(arr.shape == (264, 264) for arr in sample_s1_safetensors_dict.values())
    assert all(arr.dtype == "float32" for arr in sample_s1_safetensors_dict.values())

    assert all(arr.dtype == "uint16" for arr in sample_s2_l1c_safetensors_dict.values())
    assert all(
        sample_s2_l1c_safetensors_dict[key].shape == (264, 264)
        for key in ["B2", "B3", "B4", "B8"]
    )
    assert all(
        sample_s2_l1c_safetensors_dict[key].shape == (132, 132)
        for key in ["B5", "B6", "B7", "B8A", "B11", "B12"]
    )
    assert all(
        sample_s2_l1c_safetensors_dict[key].shape == (44, 44)
        for key in ["B1", "B9", "B10"]
    )

    assert all(arr.dtype == "uint16" for arr in sample_s2_l2a_safetensors_dict.values())
    assert all(
        sample_s2_l2a_safetensors_dict[key].shape == (264, 264)
        for key in ["B2", "B3", "B4", "B8"]
    )
    assert all(
        sample_s2_l2a_safetensors_dict[key].shape == (132, 132)
        for key in ["B5", "B6", "B7", "B8A", "B11", "B12"]
    )
    assert all(
        sample_s2_l2a_safetensors_dict[key].shape == (44, 44) for key in ["B1", "B9"]
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


def test_hydro_integration(hydro_root, encoded_hydro_path):
    env = lmdb.open(str(encoded_hydro_path), readonly=True)

    with env.begin(write=False) as txn:
        cur = txn.cursor()
        decoded_lmdb_data = {k.decode("utf-8"): load(v) for (k, v) in cur}

    lmdb_keys = decoded_lmdb_data.keys()
    assert lmdb_keys == set(
        [
            "patch_0",
            "patch_1",
            "patch_10",
            "patch_100",
            "patch_1000",
            "patch_10000",
            "patch_100000",
        ]
    )

    sample_safetensors_dict = decoded_lmdb_data.get("patch_0")
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
                "B8A",
                "B09",
                "B11",
                "B12",
            ]
        )
        == safetensors_keys
    )

    assert all(arr.shape == (256, 256) for arr in sample_safetensors_dict.values())
    assert all(arr.dtype == "uint16" for arr in sample_safetensors_dict.values())


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
