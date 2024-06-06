# rs-tensor-encoder
> a fast and easy to use application that converts popular remote sensing dataset into
a flexible DL-optimized data format for efficient and high-throughput DL model training.

<!-- TODO: Add img.shields for License, Tests, version, docker, appimage -->

## Overview

## Usage

To use it on any Linux server we recommend to use the `AppImage`:

We also provide docker image for convenience:

### Example

To convert the Sentinel-1 and Sentinel-2 patches from the [BigEarthNet-MM v2.0][ben]
dataset into the optimized format, call the application with:

```bash
rs-tensor-encoder --bigearthnet-s1-root <S1_ROOT_DIR> --bigearthnet-s2-root <S2_ROOT_DIR> Encoded-BigEarthNet
```

The resulting file will provide significantly higher throughput compared to the original
[GeoTIFF](https://www.ogc.org/standard/geotiff/) patches.
The data is encoded in a DL-library independent format, ensuring flexible use.
To access the data from within Python, ensure to have the [LMDB][LMDB] and [safetensors][safetensors]
packages installed.

TODO: Add comment about how the keys/images are generated and what should happen with the metadata

```python
import lmdb
import safetensors
from pathlib import Path

# path to the encoded dataset/output of rs-tensor-encoder
encoded_path = Path("./Encoded-BigEarthNet")

env = lmdb.open(str(encoded_path), readonly=True)

with env.begin() as txn:
  txn.get("")
```

### Supported Remote Sensing Datasets

Currently, `rs-tensor-encoder` supports:
- [BigEarthNet-S1 v2.0][ben]
- [BigEarthNet-S2 v2.0][ben]
- [BigEarthNet-MM (joining S1 + S2) v2.0][ben]

Additional datasets will be added in the near future!

## Design

- [LMDB][LMDB]
- [safetensors][safetensors]

Why [safetensors][safetensors]?

Why LMDB?

[ben]: https://bigearth.net
[LMDB]: https://www.symas.com/lmdb
[safetensors]: https://huggingface.co/docs/safetensors/index
