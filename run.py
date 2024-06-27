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
from more_itertools import chunked
from tqdm import tqdm
from concurrent.futures import as_completed, ProcessPoolExecutor
import multiprocessing as mp

# I do not believe that this is necessary.
# I could create a list of strings for each call and write that into a shared_memory region
# but I believe that chunking the entire data per process and then iterating over the chunks
# Just use spawn to create new sub-interpreters as the time of creating them the first time should be almost negligible.
#

log = structlog.get_logger()

BIGEARTHNET_S2_ORDERING = [
    "B02", "B03", "B04", "B08", "B05", "B06", "B07", "B8A", "B10", "B11", "B12", "B01", "B09",
]

def read_single_band_raster(path: str):
    with rasterio.open(path) as r:
        return r.read(1)

def s2_safetensor_generator(lmdb_key: str, files: list[str]) -> bytes:
    # In Python the dictionary insertion order is stable!
    # order the data here to make it clear that we are doing it
    # to order the safetensor entries!
    files = sorted(files, key=lambda f: BIGEARTHNET_S2_ORDERING.index(f.rsplit(".", 1)[0][-3:]))
    data = {f.rsplit(".", 1)[0][-3:]: read_single_band_raster(f) for f in files}
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
        num_s2_files = len(s2_files)

        assert num_s2_files > 0

        log.debug(f"Found {num_s2_files} S2 files")

        # group by the prefix and
        grouped = defaultdict(list)
        for f in s2_files:
            # remove the file-extension and band suffix
            grouped[
                f.rsplit(".", 1)[0].rsplit("_", 1)[0]
            ].append(f)
        # remove the large collection of Path items
        del s2_files

        log.debug("Checking that each patch directory is complete")
        for group, value_list in grouped.items():
            assert len(value_list) == 12, f"Patch has missing files: {group}"

        # these groups are necessary to extract the lmdb key
        # the safetensors key should be derived from the actual path
        # and the underlying file!

        log.debug(f"Creating LMDB database: {target_dir}")
        # 1TB for map_size
        env = lmdb.open(str(target_dir), readonly=False, create=True, map_size=(1 * 1024 * 1024 * 1024 * 1024))

        # there is no need to order the keys, as data will be ordered by LMDB
        # lmdb_keys = natsorted(grouped.keys())
        log.debug("About to serialize data in chunks")
        # HERE:
        # create chunks as lists so that the underlying process functions can be called
        # env.begin(write=True) must be created in each underlying process
        # > One simultaneous write transaction is allowed,
        #
        # LMDB will probably hold the connection open and serialize the writing on its own
        # -> Presumably the goal should be to have parallel producers that generate the
        # safetensor byte data and that is then consumed by a single consumer, ideally
        # without copying the data across processes, i.e. using shared memory
        # since it is only a 'bytes' type at this stage
        # use a multiprocessing.Queue to easily share results, even if shared_memory would be better
        # using the same ProcessPool assign all of them the appropriate key, paths combination
        # and then let them produce and consume the results, writing them into the lmdb file
        with ProcessPoolExecutor(max_workers=None, mp_context=mp.get_context("spawn")) as executor:
            # chunk size limits the number of writes per transaction
            # and the maximum number of futures that needs to be processed
            for keys_chunk in tqdm(list(chunked(grouped.keys(), 512))):
                with env.begin(write=True) as txn:
                    log.debug(f"First key of the chunk is: {keys_chunk[0]}")
                    futures_to_lmdb_key = {executor.submit(s2_safetensor_generator, lmdb_key, grouped[lmdb_key]): lmdb_key for lmdb_key in keys_chunk}
                    for future in as_completed(futures_to_lmdb_key):
                        if not txn.put(str(futures_to_lmdb_key[future]).encode(), future.result(), overwrite=False):
                            sys.exit("Program is overwriting data in the DB! This should never happen!")

                    # for key in keys_chunk:
                    #   if not txn.put(str(key).encode(), s2_safetensor_generator(key, grouped[key]), overwrite=False):
                    #             sys.exit("Program is overwriting data in the DB! This should never happen!")

if __name__ == "__main__":
    typer.run(main)
