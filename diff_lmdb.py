import hashlib

import lmdb
import numpy as np
import safetensors.numpy
import typer

hash_fn = hashlib.sha256


class PrintLater:
    def __init__(self):
        self._header = []
        self._buffer = []

    def header(self, *args, **kwargs):
        self._header.append((args, kwargs))

    def print(self, *args, **kwargs):
        self._buffer.append((args, kwargs))

    def show(self):
        for args, kwargs in self._header:
            print(*args, **kwargs)
        for args, kwargs in self._buffer:
            print(*args, **kwargs)

    def flush(self, with_header=True):
        self.show()
        self._buffer.clear()
        if with_header:
            self._header.clear()

    def clear(self):
        self._header.clear()
        self._buffer.clear()

    def __eq__(self, other):
        if not isinstance(other, PrintLater):
            return NotImplemented
        return self._buffer == other._buffer


def inspect_lmdb_file(
        lmdb_file: str = "../_data/rust_version",
        num_samples: int = 25,
        show: bool = True
):
    pl = PrintLater()
    pl.header(f"LMDB file: {lmdb_file}")
    env = lmdb.open(
        lmdb_file,
        readonly=True,
        lock=False,
        meminit=False,
        readahead=False,
        map_size=8 * 1024 ** 3,  # 8GB blocked for caching
        max_spare_txns=16,  # expected number of concurrent transactions (e.g. threads/workers)
    )
    with env.begin() as txn:
        # read all keys
        keys = list(txn.cursor().iternext(values=False))
    s1_keys = [key for key in keys if key.startswith(b"S1")]
    s2_keys = [key for key in keys if key.startswith(b"S2")]
    # sort keys
    s1_keys.sort()
    s2_keys.sort()
    # read first num_samples elements
    for key in s1_keys[:num_samples]:
        with env.begin() as txn:
            img_bytes = txn.get(key)
        img = safetensors.numpy.load(img_bytes)
        # stack all bands
        img = np.stack([img[b] for b in sorted(img.keys())])
        # calculate hash and print
        pl.print(f"{key}: {hash_fn(img.tobytes()).hexdigest()} {img.sum():>15} {img.mean():.5f} {img.std():.5f}")
    # read first num_samples elements
    for key in s2_keys[:num_samples // 3]:
        with env.begin() as txn:
            img_bytes = txn.get(key)
        img = safetensors.numpy.load(img_bytes)
        # stack all bands
        img_120 = np.stack([img[b] for b in sorted(img.keys()) if img[b].shape[0] == 120])
        img_60 = np.stack([img[b] for b in sorted(img.keys()) if img[b].shape[0] == 60])
        img_20 = np.stack([img[b] for b in sorted(img.keys()) if img[b].shape[0] == 20])
        # calculate hash and print
        pl.print(
            f"{key}_120: {hash_fn(img_120.tobytes()).hexdigest()} {img_120.sum():>15} {img_120.mean():10.5f} {img_120.std():10.5f}")
        pl.print(
            f"{key}_60 : {hash_fn(img_60.tobytes()).hexdigest()} {img_60.sum():>15} {img_60.mean():10.5f} {img_60.std():10.5f}")
        pl.print(
            f"{key}_20 : {hash_fn(img_20.tobytes()).hexdigest()} {img_20.sum():>15} {img_20.mean():10.5f} {img_20.std():10.5f}")
    if show:
        pl.show()
    return pl


def compare_lmdb_files(
        lmdb_file1: str = "../_data/rust_version",
        lmdb_file2: str = "../_data/python_version",
        num_samples: int = 25
):
    pl1 = inspect_lmdb_file(lmdb_file1, num_samples, show=False)
    pl2 = inspect_lmdb_file(lmdb_file2, num_samples, show=False)
    if pl1 == pl2:
        print("Files are identical")
    else:
        print("Files are different")
        print("File 1:")
        pl1.show()
        print("File 2:")
        pl2.show()


if __name__ == "__main__":
    typer.run(compare_lmdb_files)

