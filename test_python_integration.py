import lmdb
import rasterio
import safetensors
import numpy as np
from pathlib import Path
from safetensors.numpy import deserialize, load_file, load
import os
import pytest
import subprocess

def read_single_band_raster(path):
    with rasterio.open(path) as r:
        return r.read(1)

@pytest.fixture(scope="session")
def s1_root():
    str_p = os.environ.get("ENCODER_S1_PATH") or "./tiffs/BigEarthNet/S1/"
    p = Path(str_p)
    assert p.exists()
    assert p.is_dir()
    return p

@pytest.fixture(scope="session")
def s2_root():
    str_p = os.environ.get("ENCODER_S2_PATH") or "./tiffs/BigEarthNet/S2/"
    p = Path(str_p)
    assert p.exists()
    assert p.is_dir()
    return p

# https://docs.pytest.org/en/6.2.x/tmpdir.html#tmpdir-factory-example@pytest.fixture(scope="session")
@pytest.fixture
def encoded_bigearthnet_s1_s2_path(s1_root, s2_root, tmpdir_factory):
    tmp_path = tmpdir_factory.mktemp("lmdb")
    executable = os.environ.get("ENCODER_EXEC_PATH")
    assert executable, "Executable ENCODER_EXEC_PATH wasn't set. This should be setting by the code that executes pytest!"
    # This should make it easier to separately test different versions of the binary and the appimage as well
    subprocess.run([executable, f"--bigearthnet-s1-root={s1_root}", f"--bigearthnet-s2-root={s2_root}", tmp_path], check=True)
    return tmp_path

def test_python_integration(s1_root, s2_root, encoded_bigearthnet_s1_s2_path):
    s1_data = {file: read_single_band_raster(file) for file in s1_root.glob("**/*.tif*")}
    s2_data = {file: read_single_band_raster(file) for file in s2_root.glob("**/*.tif*")}
    source_data = {**s1_data, **s2_data}
    env = lmdb.open(str(encoded_bigearthnet_s1_s2_path), readonly=True)
    
    with env.begin(write=False) as txn:
        cur = txn.cursor()
        decoded_lmdb_data = {k.decode("utf-8"): load(v) for (k, v) in cur}
    
    # The encoded data is nested inside of another safetensor dictionary, where the inner keys are derived from the band suffix
    decoded_values = [v for outer_v in decoded_lmdb_data.values() for v in outer_v.values()]
    
    # Simply check if the data remains identical, as this is the only _true_ thing I care about from the Python viewpoint
    # If the keys/order or anything else is wrong, it isn't part of the integration test but should be handled separately as a unit test!
    for (source_key, source_value) in source_data.items():
        assert any(np.array_equal(source_value, decoded_value) for decoded_value in decoded_values), f"Couldn't find data in the LMDB database that matches the data from: {source_key}"
