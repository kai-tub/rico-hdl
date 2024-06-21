import os
import typer
from typing_extensions import Annotated
import lmdb
from safetensors.numpy import save
import sys
import rasterio
from pathlib import Path
import subprocess
import structlog
from collections import defaultdict
from natsort import natsorted
from more_itertools import chunked
from tqdm import tqdm
from concurrent import futures

log = structlog.get_logger()

BIGEARTHNET_S2_ORDERING = [
    "B02", "B03", "B04", "B08", "B05", "B06", "B07", "B8A", "B10", "B11", "B12", "B01", "B09",
]

def read_single_band_raster(path):
    with rasterio.open(path) as r:
        return r.read(1)

def s2_safetensor_generator(lmdb_key: str, files: list[Path]) -> bytes:
    # In Python the dictionary insertion order is stable!
    # order the data here to make it clear that we are doing it
    # to order the safetensor entries!
    files = sorted(files, key=lambda f: BIGEARTHNET_S2_ORDERING.index(f.stem[-3:]))
    data = {f.stem[-3:]: read_single_band_raster(f) for f in files}
    return save(data, metadata=None)


def main(
    bigearthnet_s2_directory: Annotated[
        Path,
        typer.Option(
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
        )
    ],
    target_dir: Annotated[
        Path,
        typer.Option(
            exists=False,
            resolve_path=True,
        )
    ]):
        log.info(f"Loading data from: {bigearthnet_s2_directory}")

        s2_files = subprocess.check_output(
           [
               "fd",
               "--type=file",
               "--no-ignore",
               "--show-errors",
               f"--threads={os.cpu_count()}", # use number of available CPU cores by default
               f"--base-directory={bigearthnet_s2_directory}",
               "--absolute-path",
               "--regex",
               "S2[AB]_MSIL2A_.*_B[018][0-9A].tiff?$",
            ],
            text=True
        ).splitlines()
        s2_files = [Path(f) for f in s2_files]

        num_s2_files = len(s2_files)

        assert num_s2_files > 0

        log.debug(f"Found {num_s2_files} S2 files")

        # group by the prefix and
        grouped = defaultdict(list)
        for f in s2_files:
            # remove the band suffix
            grouped[f.stem.rsplit("_", 1)[0]].append(f)

        log.debug("Checking that each patch directory is complete")
        for group, value_list in grouped.items():
            assert len(value_list) == 12, f"Patch has missing files: {group}"

        # these groups are necessary to extract the lmdb key
        # the safetensors key should be derived from the actual path
        # and the underlying file!

        log.debug(f"Creating LMDB database: {target_dir}")
        # 1TB for map_size
        env = lmdb.open(str(target_dir), readonly=False, create=True, map_size=(1 * 1024 * 1024 * 1024 * 1024))

        lmdb_keys = natsorted(grouped.keys())
        log.debug("About to serialize data in chunks")
        for keys_chunk in tqdm(chunked(lmdb_keys, 512)):
            with env.begin(write=True) as txn:
                log.debug(f"First key of the chunk is: {keys_chunk[0]}")
                with futures.ThreadPoolExecutor(max_workers=64) as executor:
                    future_to_key = {executor.submit(writer, txn, key, grouped[key]): key for key in keys_chunk}
                    for future in futures.as_completed(future_to_key):
                        if not future.result():
                            sys.exit(f"Program is overwriting data {future_to_key[future]} in the DB! This should never happen!")

                # for key in keys_chunk:
                    # if not txn.put(str(key).encode(), s2_safetensor_generator(key, grouped[key]), overwrite=False):

def writer(txn, key: Path, files):
    return txn.put(str(key).encode(), s2_safetensor_generator(key, files))

if __name__ == "__main__":
    typer.run(main)
