# rs-tensor-encoder

> a fast and easy-to-use application that converts popular remote sensing datasets into
> a flexible deep-learning optimized data format for efficient, high-throughput DL model training.

<img alt="Powered by nix" src="https://img.shields.io/badge/Powered%20By-Nix-blue?style=flat&logo=snowflake"> <img alt="Static Badge" src="https://img.shields.io/badge/AppImage-Available-blue?style=flat&logo=files">
<img alt="Static Badge Docker" src="https://img.shields.io/badge/Docker-Available-blue?style=flat&logo=docker&link=ghcr.io%2Fkai-tub%2Frs-tensor-encoder">
<img alt="Static Badge MIT License" src="https://img.shields.io/badge/License-MIT-blue?style=flat&link=https%3A%2F%2Fopensource.org%2Flicenses%2Fmit-0">
<img alt="Tests Status Badge" src="https://github.com/kai-tub/rs-tensor-encoder/actions/workflows/nix.yml/badge.svg">

## Overview

The core idea is to run the encoder _once_ on a supported remote sensing dataset.
The encoder will convert the remote sensing images into a DL-optimized format.
The resulting file will provide significantly higher throughput than the original
remote sensing images (patches)
and should be used instead of the unprocessed dataset.
The data is encoded in a DL-library independent format, ensuring flexible use.
Concretely, the image files are converted into the [safetensors][s] format and stored inside the
[LMDB][LMDB] key-value database.

> [!IMPORTANT]
> The encoded image data values are _identical_ to the data values from the original dataset!

To access the data with Python, install the [LMDB][LMDB] and [safetensors][s] packages.

### Download

Great care has been taken to ensure that the application can effortlessly run on different environments
without requiring additional dependencies on the server.
To make this possible, the application is packaged in two different ways as an:

- [AppImage](https://appimage.org/) and an
- [OCI Container (often called Docker image)](https://opencontainers.org/).

To run the application on any x86-64 Linux server, we recommend to use the `AppImage`:
- [rs-tensor-encoder.AppImage](https://github.com/kai-tub/rs-tensor-encoder/releases/latest/download/rs-tensor-encoder.AppImage)

The docker image can be used to run it on other operating systems:
- [ghcr.io/kai-tub/rs-tensor-encoder:latest](https://github.com/kai-tub/rs-tensor-encoder/pkgs/container/rs-tensor-encoder)

### Supported Remote Sensing Datasets

Currently, `rs-tensor-encoder` supports:
- [BigEarthNet-S1 v2.0][ben]
- [BigEarthNet-S2 v2.0][ben]
- [BigEarthNet-MM v2.0 (joining S1 + S2)][ben]
- [HySpecNet-11k][hyspecnet]

Additional datasets will be added in the near future!

## [BigEarthNet][ben] Example

First, [downloaded the rs-tensor-encoder](#Download) binary and install
the [lmdb][pyl] and [saftensors][pys] Python packages.
Then, to convert the Sentinel-1 and Sentinel-2 patches from the [BigEarthNet v2.0][ben]
dataset into the optimized format, call the application with:

```bash
rs-tensor-encoder --bigearthnet-s1-root <S1_ROOT_DIR> --bigearthnet-s2-root <S2_ROOT_DIR> Encoded-BigEarthNet
```

In BigEarthNet, each band is stored as a separate file with the associate band as a suffix (`_B01`, `_B12`, `_VV`, ...).
The encoder groups all image files with the same name/prefix and stores the data as a [safetensors][s] dictionary,
where the dictionary's key is the band name (`B01`, `B12`, `VV`, ...).

<details>
  <summary>Example Input</summary>

```
<S1_ROOT_DIR>
└── S1A_IW_GRDH_1SDV_20170613T165043_33UUP_65_63
   ├── S1A_IW_GRDH_1SDV_20170613T165043_33UUP_65_63_VH.tif
   └── S1A_IW_GRDH_1SDV_20170613T165043_33UUP_65_63_VV.tif
<S2_ROOT_DIR>
└── S2A_MSIL2A_20180526T100031_N9999_R122_T34WFU_14_23
   ├── S2A_MSIL2A_20180526T100031_N9999_R122_T34WFU_14_23_B01.tiff
   ├── S2A_MSIL2A_20180526T100031_N9999_R122_T34WFU_14_23_B02.tiff
   ├── S2A_MSIL2A_20180526T100031_N9999_R122_T34WFU_14_23_B03.tiff
   ├── S2A_MSIL2A_20180526T100031_N9999_R122_T34WFU_14_23_B04.tiff
   ├── S2A_MSIL2A_20180526T100031_N9999_R122_T34WFU_14_23_B05.tiff
   ├── S2A_MSIL2A_20180526T100031_N9999_R122_T34WFU_14_23_B06.tiff
   ├── S2A_MSIL2A_20180526T100031_N9999_R122_T34WFU_14_23_B07.tiff
   ├── S2A_MSIL2A_20180526T100031_N9999_R122_T34WFU_14_23_B08.tiff
   ├── S2A_MSIL2A_20180526T100031_N9999_R122_T34WFU_14_23_B09.tiff
   ├── S2A_MSIL2A_20180526T100031_N9999_R122_T34WFU_14_23_B8A.tiff
   ├── S2A_MSIL2A_20180526T100031_N9999_R122_T34WFU_14_23_B11.tiff
   └── S2A_MSIL2A_20180526T100031_N9999_R122_T34WFU_14_23_B12.tiff
```

</details>

<details>
  <summary>LMDB result</summary> 

```
'S1A_IW_GRDH_1SDV_20170613T165043_33UUP_65_63': 
  {
    'VH': <120x120 float32 safetensors image data>
    'VV': <120x120 float32 safetensors image data>
  },
'S2A_MSIL2A_20180526T100031_N9999_R122_T34WFU_14_23':
  {
    'B01': <120x120 uint16 safetensors image data>,
    'B02': <120x120 uint16 safetensors image data>,
    'B03': <120x120 uint16 safetensors image data>,
    'B04': <120x120 uint16 safetensors image data>,
    'B05': <120x120 uint16 safetensors image data>,
    'B06': <120x120 uint16 safetensors image data>,
    'B07': <120x120 uint16 safetensors image data>,
    'B08': <120x120 uint16 safetensors image data>,
    'B8A': <120x120 uint16 safetensors image data>,
    'B09': <120x120 uint16 safetensors image data>,
    'B11': <120x120 uint16 safetensors image data>,
    'B12': <120x120 uint16 safetensors image data>,
  }
```
  
</details>

The following code shows how to access the converted database:

```python
import lmdb
# import desired deep-learning library:
# numpy, torch, tensorflow, paddle, flax, mlx
from safetensors.numpy import load
from pathlib import Path

# path to the encoded dataset/output of rs-tensor-encoder
encoded_path = Path("./Encoded-BigEarthNet")

# Make sure to only open the environment once
# and not everytime an item is accessed.
env = lmdb.open(str(encoded_path), readonly=True)

with env.begin() as txn:
  # string encoding is required to map the string to an LMDB key
  safetensor_dict = load(txn.get("S2A_MSIL2A_20180526T100031_N9999_R122_T34WFU_14_23".encode()))

rgb_bands = ["B04", "B03", "B02"]
rgb_tensor = np.stack([safetensor_dict[b] for b in rgb_bands])
assert rgb_tensor.shape == (3, 120, 120) 
```


> [!TIP]
> Remember to use the appropriate `load` function for a given deep-learning library.

The [ConfigILM](https://github.com/lhackel-tub/ConfigILM) library provides [an excellent
LMDB reader example](https://github.com/lhackel-tub/ConfigILM/blob/main/configilm/extra/BENv2_utils.py)
that shows how to utilize the encoded data for high-throughput deep-learning.

### [HySpecNet-11k][hyspecnet] Example

First, [downloaded the rs-tensor-encoder](#Download) binary and install
the [lmdb][pyl] and [saftensors][pys] Python packages.
Then, to convert the patches from the [HySpecNet-11k][hyspecnet]
dataset into the optimized format, call the application with:

```bash
rs-tensor-encoder --hyspecnet <HYSPECNET_ROOT_DIR> encoded-hyspecnet
```

In [HySpecNet-11k][hyspecnet], each patch contains 224 bands.
The encoder will convert each patch into a [safetensors][s]
dictionary, where the band index prefixed with `B` is the key (for example, `B1`, `B201`).

<details>
  <summary>Example Input</summary>

```
integration_tests/tiffs/HySpecNet-11k
├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X03110438
│  ├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X03110438-QL_PIXELMASK.TIF
│  ├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X03110438-QL_QUALITY_CIRRUS.TIF
│  ├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X03110438-QL_QUALITY_CLASSES.TIF
│  ├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X03110438-QL_QUALITY_CLOUD.TIF
│  ├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X03110438-QL_QUALITY_CLOUDSHADOW.TIF
│  ├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X03110438-QL_QUALITY_HAZE.TIF
│  ├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X03110438-QL_QUALITY_SNOW.TIF
│  ├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X03110438-QL_QUALITY_TESTFLAGS.TIF
│  ├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X03110438-QL_SWIR.TIF
│  ├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X03110438-QL_VNIR.TIF
│  ├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X03110438-SPECTRAL_IMAGE.TIF
│  └── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X03110438-THUMBNAIL.jpg
└── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X04390566
   ├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X04390566-QL_PIXELMASK.TIF
   ├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X04390566-QL_QUALITY_CIRRUS.TIF
   ├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X04390566-QL_QUALITY_CLASSES.TIF
   ├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X04390566-QL_QUALITY_CLOUD.TIF
   ├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X04390566-QL_QUALITY_CLOUDSHADOW.TIF
   ├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X04390566-QL_QUALITY_HAZE.TIF
   ├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X04390566-QL_QUALITY_SNOW.TIF
   ├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X04390566-QL_QUALITY_TESTFLAGS.TIF
   ├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X04390566-QL_SWIR.TIF
   ├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X04390566-QL_VNIR.TIF
   ├── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X04390566-SPECTRAL_IMAGE.TIF
   └── ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X04390566-THUMBNAIL.jpg
```
</details>

<details>
  <summary>LMDB result</summary>

> [!INFO]
> The encoder will only process the image data (`SPECTRAL_IMAGE.TIF`)
> and skip over the quality indicator and thumbnail files.

```
'ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X03110438':
  {
    'B1': <128x128 int16 safetensors image data>
    'B2': <128x128 int16 safetensors image data>
     ⋮
    'B10': <128x128 int16 safetensors image data>
    'B11': <128x128 int16 safetensors image data>
     ⋮
    'B100': <128x128 int16 safetensors image data>
    'B101': <128x128 int16 safetensors image data>
     ⋮
    'B223': <128x128 int16 safetensors image data>
    'B224': <128x128 int16 safetensors image data>
  },
'ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X04390566':
  {
    'B1': <128x128 int16 safetensors image data>
    'B2': <128x128 int16 safetensors image data>
     ⋮
    'B10': <128x128 int16 safetensors image data>
    'B11': <128x128 int16 safetensors image data>
     ⋮
    'B100': <128x128 int16 safetensors image data>
    'B101': <128x128 int16 safetensors image data>
     ⋮
    'B223': <128x128 int16 safetensors image data>
    'B224': <128x128 int16 safetensors image data>
  }
```

</details>

```python
import lmdb
import numpy as np
# import desired deep-learning library:
# numpy, torch, tensorflow, paddle, flax, mlx
from safetensors.numpy import load
from pathlib import Path

encoded_path = "encoded-hyspecnet"

# Make sure to only open the environment once
# and not everytime an item is accessed.
env = lmdb.open(str(encoded_path), readonly=True)

with env.begin() as txn:
  # string encoding is required to map the string to an LMDB key
  safetensor_dict = load(txn.get("ENMAP01-____L2A-DT0000004950_20221103T162438Z_001_V010110_20221118T145147Z-Y01460273_X04390566".encode()))

hyspecnet_bands = range(1, 225)
# recommendation from HySpecNet-11k paper 
skip_bands = [126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 160, 161, 162, 163, 164, 165, 166]
tensor = np.stack([safetensor_dict[f"B{k}"] for k in hyspecnet_bands if k not in skip_bands])
assert tensor.shape == (202, 128, 128)
```


## Design

<details>
  <summary>
    Why safetensors?
  </summary>

The main advantage of the [safetensors][s] format is its [_fast_](https://huggingface.co/docs/safetensors/speed)
and deep-learning independent tensor serialization capability.
This allows teams with different deep-learning framework preferences to utilize the same data without issues.
Please refer to [the official documentation](https://huggingface.co/docs/safetensors/index) to discover more benefits
of the [safetensors][s] format.

</details>

<details>
<summary>
  Why LMDB?
</summary>

[LMDB][LMDB] is an in-memory key-value store known for its reliability and high performance.
It effectively utilizes the operating system's buffer cache and allows seamless parallel read access.
These properties make it an excellent choice for environments where multiple users require access to the same data,
which is common in deep-learning research.

One significant advantage of choosing [LMDB][LMDB] over more array-structured solutions like 
[netcdf](https://www.unidata.ucar.edu/software/netcdf/) or [Zarr](https://zarr.dev/)
is that it is better aligned with the access patterns and dataset characteristics specific
to remote sensing deep-learning datasets.
Remote sensing deep-learning datasets typically consist of small images
(usually around 120px x 120px) with varying resolutions based on the selected band
(e.g., BigEarthNet's highest resolution is 120px x 120px and the lowest is 20px x 20px).
These images are randomly accessed during training, which differs from the access patterns
in classical machine-learning applications or applications that calculate zonal statistics.
These characteristics make array-structured data formats less suitable for deep-learning applications.

</details>


[ben]: https://bigearth.net
[LMDB]: https://www.symas.com/lmdb
[s]: https://huggingface.co/docs/safetensors/index
[hyspecnet]: https://hyspecnet.rsim.berlin/
[pyl]: https://lmdb.readthedocs.io/en/release/
[pys]: https://github.com/huggingface/safetensors
