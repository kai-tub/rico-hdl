# rico-hdl

> A fast and easy-to-use **r**emote sensing **i**mage format **co**nverter for **h**igh-throughput **d**eep-**l**earning (rico-hdl).

<img alt="Powered by nix" src="https://img.shields.io/badge/Powered%20By-Nix-blue?style=flat&logo=snowflake"> <a href="https://arxiv.org/abs/2407.03653"><img src="https://img.shields.io/badge/arXiv-2407.03653-b31b1b.svg" alt="arxiv link"></a> <img alt="Static Badge" src="https://img.shields.io/badge/AppImage-Available-blue?style=flat&logo=files">
<img alt="Static Badge Docker" src="https://img.shields.io/badge/Docker-Available-blue?style=flat&logo=docker&link=ghcr.io%2Fkai-tub%2Frico-hdl">
<img alt="Static Badge MIT License" src="https://img.shields.io/badge/License-MIT-blue?style=flat&link=https%3A%2F%2Fopensource.org%2Flicenses%2Fmit-0">
<img alt="Tests Status Badge" src="https://github.com/kai-tub/rico-hdl/actions/workflows/nix.yml/badge.svg">

## Overview

The core idea is to run the encoder on a supported remote sensing dataset and use the resulting
output to efficiently train deep-learning models.
The encoder converts the remote sensing images into a DL-optimized format.
The resulting output will provide significantly higher throughput than the original
remote sensing images (patches)
and should be used instead of the unprocessed dataset.
The data is encoded in a DL-framework independent format, ensuring flexible use.
Concretely, the image files are converted into the [safetensors][s] format and stored inside the
[LMDB][LMDB] key-value database.

> [!IMPORTANT]
> The encoded image data values are _identical_ to the data values from the original dataset!

To access the data with Python, install the [LMDB][LMDB] and [safetensors][s] packages.

### Download

Great care has been taken to ensure the application can effortlessly run on different environments
without requiring additional dependencies on the server.
To make this possible, the application is packaged in two different ways as an:

- [AppImage](https://appimage.org/) and
- [OCI Container (often called Docker image)](https://opencontainers.org/).

To run the application on any x86-64 Linux server, we recommend to use the `AppImage`:
- [rico-hdl.AppImage](https://github.com/kai-tub/rico-hdl/releases/latest/download/rico-hdl.AppImage)

The docker image can be used to run it on other operating systems:
- [ghcr.io/kai-tub/rico-hdl:latest](https://github.com/kai-tub/rico-hdl/pkgs/container/rico-hdl)

## Supported Remote Sensing Datasets

Currently, `rico-hdl` supports:
- [BigEarthNet-S1 v2.0](#bigearthnet-example)
- [BigEarthNet-S2 v2.0](#bigearthnet-example)
- [BigEarthNet-MM v2.0](#bigearthnet-example)
- [BigEarthNet-Reference-Maps v2.0](#bigearthnet-example)
- [HySpecNet-11k](#hyspecnet-11k-example)
- [UC Merced Land Use](#uc-merced-land-use-example)
- [EuroSAT](#eurosat-example)
- [SSL4EO-S12](#ssl4eo-s12-example)
- [Major-Tom-Core](#major-tom-core-example)
- [Hydro](#hydro)

Additional datasets will be added in the near future.

### [BigEarthNet][ben] Example

First, [download the rico-hdl](#Download) binary and install
the Python [lmdb][pyl] and [saftensors][pys] packages.
Then, to convert the Sentinel-1 and Sentinel-2 patches from the [BigEarthNet v2.0][ben]
dataset into the optimized format, call the application with:

```bash
rico-hdl bigearthnet --bigearthnet-s1-dir <S1_ROOT_DIR> --bigearthnet-s2-dir <S2_ROOT_DIR> --bigearthnet-reference-maps <REREFERENCE_MAPS_DIR> --target-dir Encoded-BigEarthNet
```

In BigEarthNet, for each patch each band is stored as a separate file with the associate band as a suffix (`_B01`, `_B12`, `_VV`, ...).
The reference maps are stored as TIFF files with a `_reference_maps` suffix.
The encoder groups all image files with the same name/prefix and stores the data as a [safetensors][s] dictionary,
where the `safetensors` dictionary's key is the band name (`B01`, `B12`, `VV`, ...) for the patches
and `Reference_Map` for the single-band reference maps.

<details>
  <summary>Example Input</summary>

```
├── <S1_ROOT_DIR>
│  └── S1A_IW_GRDH_1SDV_20170613T165043
│     └── S1A_IW_GRDH_1SDV_20170613T165043_33UUP_70_48
│        ├── S1A_IW_GRDH_1SDV_20170613T165043_33UUP_70_48_VH.tif
│        └── S1A_IW_GRDH_1SDV_20170613T165043_33UUP_70_48_VV.tif
├── <S2_ROOT_DIR>
│   └── S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP
│       └── S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP_75_43
│           ├── S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP_75_43_B01.tif
│           ├── S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP_75_43_B02.tif
│           ├── S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP_75_43_B03.tif
│           ├── S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP_75_43_B04.tif
│           ├── S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP_75_43_B05.tif
│           ├── S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP_75_43_B06.tif
│           ├── S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP_75_43_B07.tif
│           ├── S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP_75_43_B08.tif
│           ├── S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP_75_43_B09.tif
│           ├── S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP_75_43_B8A.tif
│           ├── S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP_75_43_B11.tif
│           └── S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP_75_43_B12.tif
└── Reference_Maps
    └── S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP
        └── S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP_26_57
            └── S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP_26_57_reference_map.tif
```

</details>

<details>
  <summary>LMDB Result</summary>

```
'S1A_IW_GRDH_1SDV_20170613T165043_33UUP_70_48':
  {
    'VH': <120x120 float32 safetensors image data>
    'VV': <120x120 float32 safetensors image data>
  },
'S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP_75_43':
  {
    'B01': <30x30   uint16 safetensors image data>,
    'B02': <120x120 uint16 safetensors image data>,
    'B03': <120x120 uint16 safetensors image data>,
    'B04': <120x120 uint16 safetensors image data>,
    'B05': <60x60   uint16 safetensors image data>,
    'B06': <60x60   uint16 safetensors image data>,
    'B07': <60x60   uint16 safetensors image data>,
    'B08': <120x120 uint16 safetensors image data>,
    'B8A': <60x60   uint16 safetensors image data>,
    'B09': <30x30   uint16 safetensors image data>,
    'B11': <60x60   uint16 safetensors image data>,
    'B12': <60x60   uint16 safetensors image data>,
  }
'S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP_26_57_reference_map':
  {
    'Data': <120x120 uint16 safetensors image data>,
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

# path to the encoded dataset/output of rico-hdl
encoded_path = Path("./Encoded-BigEarthNet")

# Make sure to only open the environment once
# and not everytime an item is accessed.
env = lmdb.open(str(encoded_path), readonly=True)

with env.begin() as txn:
  # string encoding is required to map the string to an LMDB key
  safetensor_dict = load(txn.get("S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP".encode()))

rgb_bands = ["B04", "B03", "B02"]
rgb_tensor = np.stack([safetensor_dict[b] for b in rgb_bands])
assert rgb_tensor.shape == (3, 120, 120)
```


> [!TIP]
> Remember to use the appropriate `load` function for a given deep-learning library.

The [ConfigILM](https://github.com/lhackel-tub/ConfigILM) library provides [an
LMDB reader example](https://github.com/lhackel-tub/ConfigILM/blob/main/configilm/extra/BENv2_utils.py)
that shows how to utilize the encoded data for high-throughput deep-learning.

### [HySpecNet-11k][hyspecnet] Example

First, [download the rico-hdl](#Download) binary and install
the Python [lmdb][pyl] and [saftensors][pys] packages.
Then, to convert the patches from the [HySpecNet-11k][hyspecnet]
dataset into the optimized format, call the application with:

```bash
rico-hdl hyspecnet-11k --dataset-dir <HYSPECNET_ROOT_DIR> --dataset-dir Encoded-HySpecNet
```

In [HySpecNet-11k][hyspecnet], each patch contains 224 bands.
The encoder will convert each patch into a [safetensors][s]
dictionary, where the band index prefixed with `B` is the key (for example, `B1`, `B201`)
of the safetensor dictionary.

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
  <summary>LMDB Result</summary>

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

encoded_path = "Encoded-HySpecNet"

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

### [UC Merced Land Use][ucmerced] Example

First, [download the rico-hdl](#Download) binary and install
the Python [lmdb][pyl] and [saftensors][pys] packages.
Then, to convert the patches from the [UC Merced Land Use][ucmerced]
dataset into the optimized format, call the application with:

```bash
rico-hdl uc-merced --dataset-dir <UC_MERCED_LAND_USE_ROOT_DIR> --dataset-dir Encoded-UC-Merced
```

In [UC Merced][ucmerced], each patch contains 3 bands (RGB).
The encoder will convert each patch into a [safetensors][s]
dictionary, where the band's color interpretation is the key (one of `Red`, `Green`, `Blue`)
of the safetensor dictionary.

<details>
  <summary>Example Input</summary>

```
integration_tests/tiffs/UCMerced_LandUse
└── Images
   ├── airplane
   │  ├── airplane00.tif
   │  └── airplane42.tif
   └── forest
      ├── forest10.tif
      └── forest99.tif
```
</details>

<details>
  <summary>LMDB Result</summary>

```
'airplane00':
  {
    'Red':   <256x256 uint8 safetensors image data>
    'Green': <256x256 uint8 safetensors image data>
    'Blue':  <256x256 uint8 safetensors image data>
  },
'airplane42':
  {
    'Red':   <256x256 uint8 safetensors image data>
    'Green': <256x256 uint8 safetensors image data>
    'Blue':  <256x256 uint8 safetensors image data>
  },
'forest10':
  {
    'Red':   <256x256 uint8 safetensors image data>
    'Green': <256x256 uint8 safetensors image data>
    'Blue':  <256x256 uint8 safetensors image data>
  },
'forest99':
  {
    'Red':   <256x256 uint8 safetensors image data>
    'Green': <256x256 uint8 safetensors image data>
    'Blue':  <256x256 uint8 safetensors image data>
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

encoded_path = "Encoded-UC-Merced"

# Make sure to only open the environment once
# and not everytime an item is accessed.
env = lmdb.open(str(encoded_path), readonly=True)

with env.begin() as txn:
  # string encoding is required to map the string to an LMDB key
  safetensor_dict = load(txn.get("airplane00".encode()))

tensor = np.stack([safetensor_dict[key] for key in ["Red", "Green", "Blue"]])
assert tensor.shape == (3, 256, 256)
```

### [EuroSAT][euro] Example

First, [download the rico-hdl](#Download) binary and install
the Python [lmdb][pyl] and [saftensors][pys] packages.
Then, to convert the patches from the [EuroSAT][euro] multi-spectral
dataset into the optimized format, call the application with:

```bash
rico-hdl eurosat-multi-spectral --dataset-dir <EURO_SAT_MS_ROOT_DIR> --dataset-dir Encoded-EuroSAT-MS
```

In [EuroSAT][euro], each patch contains 13 bands from a Sentinel-2 L1C tile.
The encoder will convert each patch into a [safetensors][s]
where the dictionary's key is the band name (`B01`, `B02`,..., `B10`, `B11`, `B12`, `B08A`)
of the safetensor dictionary.

<details>
  <summary>Example Input</summary>

```
integration_tests/tiffs/EuroSAT_MS
├── AnnualCrop
│  └── AnnualCrop_1.tif
├── Pasture
│  └── Pasture_300.tif
└── SeaLake
   └── SeaLake_3000.tif
```
</details>

<details>
  <summary>LMDB Result</summary>

```
'AnnualCrop_1':
  {
    'B01':   <64x64 uint16 safetensors image data>,
    'B02':   <64x64 uint16 safetensors image data>,
    'B03':   <64x64 uint16 safetensors image data>,
    'B04':   <64x64 uint16 safetensors image data>,
    'B05':   <64x64 uint16 safetensors image data>,
    'B06':   <64x64 uint16 safetensors image data>,
    'B07':   <64x64 uint16 safetensors image data>,
    'B08':   <64x64 uint16 safetensors image data>,
    'B09':   <64x64 uint16 safetensors image data>,
    'B10':   <64x64 uint16 safetensors image data>,
    'B11':   <64x64 uint16 safetensors image data>,
    'B12':   <64x64 uint16 safetensors image data>,
    'B08A':  <64x64 uint16 safetensors image data>,
  },
'Pasture_300':
  {
    'B01':   <64x64 uint16 safetensors image data>,
    'B02':   <64x64 uint16 safetensors image data>,
    'B03':   <64x64 uint16 safetensors image data>,
    'B04':   <64x64 uint16 safetensors image data>,
    'B05':   <64x64 uint16 safetensors image data>,
    'B06':   <64x64 uint16 safetensors image data>,
    'B07':   <64x64 uint16 safetensors image data>,
    'B08':   <64x64 uint16 safetensors image data>,
    'B09':   <64x64 uint16 safetensors image data>,
    'B10':   <64x64 uint16 safetensors image data>,
    'B11':   <64x64 uint16 safetensors image data>,
    'B12':   <64x64 uint16 safetensors image data>,
    'B08A':  <64x64 uint16 safetensors image data>,
  },
'SeaLake_3000':
  {
    'B01':   <64x64 uint16 safetensors image data>,
    'B02':   <64x64 uint16 safetensors image data>,
    'B03':   <64x64 uint16 safetensors image data>,
    'B04':   <64x64 uint16 safetensors image data>,
    'B05':   <64x64 uint16 safetensors image data>,
    'B06':   <64x64 uint16 safetensors image data>,
    'B07':   <64x64 uint16 safetensors image data>,
    'B08':   <64x64 uint16 safetensors image data>,
    'B09':   <64x64 uint16 safetensors image data>,
    'B10':   <64x64 uint16 safetensors image data>,
    'B11':   <64x64 uint16 safetensors image data>,
    'B12':   <64x64 uint16 safetensors image data>,
    'B08A':  <64x64 uint16 safetensors image data>,
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

encoded_path = "Encoded-EuroSAT-MS"

# Make sure to only open the environment once
# and not everytime an item is accessed.
env = lmdb.open(str(encoded_path), readonly=True)

with env.begin() as txn:
  # string encoding is required to map the string to an LMDB key
  safetensor_dict = load(txn.get("AnnualCrop_1".encode()))

tensor = np.stack([safetensor_dict[key] for key in [
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
  "B08A"
]])
assert tensor.shape == (13, 64, 64)
```

### [SSL4EO-S12][ssl4eo-s12] Example

First, [download the rico-hdl](#Download) binary and install
the Python [lmdb][pyl] and [saftensors][pys] packages.
Then, to convert the Sentinel-1, Sentinel-2 L1C, and Sentinel-2 L2A
patches from the [SSL4EO-S12][ssl4eo-s12]
dataset into the optimized format, call the application with:

```bash
rico-hdl ssl4eo-s12 --s1-dir <S1_ROOT_DIR> --s2-l1c-dir <S2_L1C_ROOT_DIR> --s2-l2a-dir <S2_L2A_ROOT_DIR> --target-dir Encoded-SSL4EO-S12
```

In [SSL4EO-S12][ssl4eo-s12], each band is stored as a separate file with the associate band as a name (`B1.tif`, `B9.tif`, `B10.tif`, `VV.tif`, ...).
The encoder groups all image files with the same name/prefix and stores the data as a [safetensors][s] dictionary,
where the dictionary's key is the band name (`B1`, `B9`, `B10`, `VV`, ...).

<details>
  <summary>Example Input</summary>

```
<SSL4EO-S12 ROOT DIRECTORY>
├── s1
│  └── 0000200
│     ├── S1A_IW_GRDH_1SDV_20200607T010800_20200607T010825_032904_03CFBA_D457
│     │  ├── metadata.json
│     │  ├── VH.tif
│     │  └── VV.tif
│     └── S1A_IW_GRDH_1SDV_20200903T131212_20200903T131237_034195_03F8F5_AC1C
│        ├── metadata.json
│        ├── VH.tif
│        └── VV.tif
├── s2a
│  └── 0000200
│     ├── 20200604T054639_20200604T054831_T43RCP
│     │  ├── B1.tif
│     │  ├── B2.tif
│     │  ├── B3.tif
│     │  ├── B4.tif
│     │  ├── B5.tif
│     │  ├── B6.tif
│     │  ├── B7.tif
│     │  ├── B8.tif
│     │  ├── B8A.tif
│     │  ├── B9.tif
│     │  ├── B11.tif
│     │  ├── B12.tif
│     │  └── metadata.json
│     └── 20200813T054639_20200813T054952_T43RCP
│        ├── B1.tif
│        ├── B2.tif
│        ├── B3.tif
│        ├── B4.tif
│        ├── B5.tif
│        ├── B6.tif
│        ├── B7.tif
│        ├── B8.tif
│        ├── B8A.tif
│        ├── B9.tif
│        ├── B11.tif
│        ├── B12.tif
│        └── metadata.json
└── s2c
   └── 0000200
      ├── 20200604T054639_20200604T054831_T43RCP
      │  ├── B1.tif
      │  ├── B2.tif
      │  ├── B3.tif
      │  ├── B4.tif
      │  ├── B5.tif
      │  ├── B6.tif
      │  ├── B7.tif
      │  ├── B8.tif
      │  ├── B8A.tif
      │  ├── B9.tif
      │  ├── B10.tif
      │  ├── B11.tif
      │  ├── B12.tif
      │  └── metadata.json
      └── 20200823T054639_20200823T055618_T43RCP
         ├── B1.tif
         ├── B2.tif
         ├── B3.tif
         ├── B4.tif
         ├── B5.tif
         ├── B6.tif
         ├── B7.tif
         ├── B8.tif
         ├── B8A.tif
         ├── B9.tif
         ├── B10.tif
         ├── B11.tif
         ├── B12.tif
         └── metadata.json
```

</details>

<details>
  <summary>LMDB Result</summary>

Note: We merge the patch directory with the two upper parent directories.
This path merging ensures that values are unique and that the entire
SSL4EO-S12 dataset can be stored in a single LMDB database.

And the authors of SSL4EO-S12 did not ensure that the resulting patches have
a consistent size! There are some patches that have an additional row/column

```
's1_0000200_S1A_IW_GRDH_1SDV_20200607T010800_20200607T010825_032904_03CFBA_D457':
  {
    'VH': <264x264 float32 safetensors image data>
    'VV': <264x264 float32 safetensors image data>
  },
's1_0000200_S1A_IW_GRDH_1SDV_20200903T131212_20200903T131237_034195_03F8F5_AC1C':
  {
    'VH': <264x264 float32 safetensors image data>
    'VV': <264x264 float32 safetensors image data>
  },
's2a_0000200_20200604T054639_20200604T054831_T43RCP': {
    'B1':  <44x44   uint16 safetensors image data>
    'B2':  <264x264 uint16 safetensors image data>
    'B3':  <264x264 uint16 safetensors image data>
    'B4':  <264x264 uint16 safetensors image data>
    'B5':  <132x132 uint16 safetensors image data>
    'B6':  <132x132 uint16 safetensors image data>
    'B7':  <132x132 uint16 safetensors image data>
    'B8':  <132x132 uint16 safetensors image data>
    'B8A': <132x132 uint16 safetensors image data>
    'B9':  <44x44   uint16 safetensors image data>
    'B10': <44x44   uint16 safetensors image data>
    'B11': <132x132 uint16 safetensors image data>
    'B12': <132x132 uint16 safetensors image data>
  },
's2a_0000200_20200813T054639_20200813T054952_T43RCP': {
    'B1':  <44x44   uint16 safetensors image data>
    'B2':  <264x264 uint16 safetensors image data>
    'B3':  <264x264 uint16 safetensors image data>
    'B4':  <264x264 uint16 safetensors image data>
    'B5':  <132x132 uint16 safetensors image data>
    'B6':  <132x132 uint16 safetensors image data>
    'B7':  <132x132 uint16 safetensors image data>
    'B8':  <132x132 uint16 safetensors image data>
    'B8A': <132x132 uint16 safetensors image data>
    'B9':  <44x44   uint16 safetensors image data>
    'B10': <44x44   uint16 safetensors image data>
    'B11': <132x132 uint16 safetensors image data>
    'B12': <132x132 uint16 safetensors image data>
  },
's2c_0000200_20200604T054639_20200604T054831_T43RCP': {
    'B1':  <44x44   uint16 safetensors image data>
    'B2':  <264x264 uint16 safetensors image data>
    'B3':  <264x264 uint16 safetensors image data>
    'B4':  <264x264 uint16 safetensors image data>
    'B5':  <132x132 uint16 safetensors image data>
    'B6':  <132x132 uint16 safetensors image data>
    'B7':  <132x132 uint16 safetensors image data>
    'B8':  <132x132 uint16 safetensors image data>
    'B8A': <132x132 uint16 safetensors image data>
    'B9':  <44x44   uint16 safetensors image data>
    'B11': <132x132 uint16 safetensors image data>
    'B12': <132x132 uint16 safetensors image data>
  },
's2c_0000200_20200823T054639_20200823T055618_T43RCP': {
    'B1':  <44x44   uint16 safetensors image data>
    'B2':  <264x264 uint16 safetensors image data>
    'B3':  <264x264 uint16 safetensors image data>
    'B4':  <264x264 uint16 safetensors image data>
    'B5':  <132x132 uint16 safetensors image data>
    'B6':  <132x132 uint16 safetensors image data>
    'B7':  <132x132 uint16 safetensors image data>
    'B8':  <132x132 uint16 safetensors image data>
    'B8A': <132x132 uint16 safetensors image data>
    'B9':  <44x44   uint16 safetensors image data>
    'B11': <132x132 uint16 safetensors image data>
    'B12': <132x132 uint16 safetensors image data>
  },
```

</details>

The following code shows how to access the converted database:

```python
import lmdb
# import desired deep-learning library:
# numpy, torch, tensorflow, paddle, flax, mlx
from safetensors.numpy import load
from pathlib import Path

# path to the encoded dataset/output of rico-hdl
encoded_path = Path("./Encoded-SSL4EO-S12")

# Make sure to only open the environment once
# and not everytime an item is accessed.
env = lmdb.open(str(encoded_path), readonly=True)

with env.begin() as txn:
  # string encoding is required to map the string to an LMDB key
  safetensor_dict = load(txn.get("s2c_0000200_20200823T054639_20200823T055618_T43RCP".encode()))

rgb_bands = ["B4", "B3", "B2"]
rgb_tensor = np.stack([safetensor_dict[b] for b in rgb_bands])
assert rgb_tensor.shape == (3, 264, 264)
```

## [Major-TOM-Core][major-tom] Example

First, [download the rico-hdl](#Download) binary and install
the Python [lmdb][pyl] and [saftensors][pys] packages.
Then, to convert the Sentinel-1 and Sentinel-2 patches from the [Major-TOM-Core][major-tom]
dataset into the optimized format, call the application with:

```bash
rico-hdl major-tom-core --s1-dir <S1_ROOT_DIR> --s2-dir <S2_ROOT_DIR> --target-dir encoded-major-tom
```

In Major-TOM-Core, each band is stored as a separate file with the associate band as the name (`B01.tif`, `B12.tif`, `vv.tif`, ...).
The directory that contains the bands is the associated product id/patch and
is uniquely identifiable if it is combined with the associated grid cell id (parent directory).
The encoder groups all unique patches (`<grid_cell>_<product_id>`) and stores the data as a [safetensors][s] dictionary,
where the dictionary's key is the band name (`B01`, `B12`, `vv`, ...).

> [!NOTE]
> The encoder will _not_ encode the `thumbnail.png` nor the `cloud_mask.tif` band!

<details>
  <summary>Example Input</summary>

```
├── <S1_ROOT_DIR>
│  └── 897U
│     └── 897U_171R
│        └── S1B_IW_GRDH_1SDV_20210827T012624_20210827T012653_028425_036437_rtc
│           ├── thumbnail.png
│           ├── vh.tif
│           └── vv.tif
└── <S2_ROOT_DIR>
   └── 199U
      └── 199U_1099R
         └── S2B_MSIL2A_20200223T032739_N9999_R018_T48QUE_20230924T183543
            ├── B01.tif
            ├── B02.tif
            ├── B03.tif
            ├── B04.tif
            ├── B05.tif
            ├── B06.tif
            ├── B07.tif
            ├── B08.tif
            ├── B09.tif
            ├── B8A.tif
            ├── B11.tif
            ├── B12.tif
            ├── cloud_mask.tif
            └── thumbnail.png
```

</details>

<details>
  <summary>LMDB Result</summary>

Note: We merge the patch directory with the parent directories.
This path merging ensures that values are unique.

And the authors of Major-Tom-Core did not ensure that the resulting patches have
a consistent size! There are some patches that have a different size, like
`195D_241R/S1B_IW_GRDH_1SDV_20200419T165643_20200419T165708_021215_028426_rtc/vv.tif`
with a pixel size of `(1424, 1424) instead of (1068, 1424)` and where each pixel is
`7.5x7.5 m` instead of `10x10 m` (most likely the patch has been accidentally interpolated).

```
'897U_171R_S1B_IW_GRDH_1SDV_20210827T012624_20210827T012653_028425_036437_rtc':
  {
    'vh': <1068x1068 float32 safetensors image data>
    'vv': <1068x1068 float32 safetensors image data>
  },
'199U_1099R_S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP':
  {
    'B01': <178x178   uint16 safetensors image data>,
    'B02': <1068x1068 uint16 safetensors image data>,
    'B03': <1068x1068 uint16 safetensors image data>,
    'B04': <1068x1068 uint16 safetensors image data>,
    'B05': <534x534   uint16 safetensors image data>,
    'B06': <534x534   uint16 safetensors image data>,
    'B07': <534x534   uint16 safetensors image data>,
    'B08': <1068x1068 uint16 safetensors image data>,
    'B8A': <534x534   uint16 safetensors image data>,
    'B09': <178x178   uint16 safetensors image data>,
    'B11': <534x534   uint16 safetensors image data>,
    'B12': <534x534   uint16 safetensors image data>,
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

# path to the encoded dataset/output of rico-hdl
encoded_path = Path("./encoded-major-tom")

# Make sure to only open the environment once
# and not everytime an item is accessed.
env = lmdb.open(str(encoded_path), readonly=True)

with env.begin() as txn:
  # string encoding is required to map the string to an LMDB key
  safetensor_dict = load(txn.get("199U_1099R_S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP".encode()))

rgb_bands = ["B04", "B03", "B02"]
rgb_tensor = np.stack([safetensor_dict[b] for b in rgb_bands])
assert rgb_tensor.shape == (3, 1068, 1068)
```


> [!TIP]
> Remember to use the appropriate `load` function for a given deep-learning library.

### [Hydro][hydro] Example

First, [download the rico-hdl](#Download) binary and install
the Python [lmdb][pyl] and [saftensors][pys] packages.
Then, to convert the patches from the [Hydro][hydro]
dataset into the optimized format, call the application with:

```bash
rico-hdl hydro --dataset-dir <HYDRO_ROOT_DIR> --dataset-dir Encoded-Hydro
```

In [Hydro][hydro], each patch contains 12 bands.
The encoder will convert each patch into a [safetensors][s]
dictionary, where each key is the band name (`B01`, `B02`, ... `B8A`, `B09`, `B11`, `B12`)
of the safetensors dictionary.

<details>
  <summary>Example Input</summary>

```
Hydro
├── patch_0.tif
└── patch_1.tif
```
</details>

<details>
  <summary>LMDB Result</summary>

```
'patch_0':
  {
    'B01': <256x256 uint16 safetensors image data>,
    'B02': <256x256 uint16 safetensors image data>,
    'B03': <256x256 uint16 safetensors image data>,
    'B04': <256x256 uint16 safetensors image data>,
    'B05': <256x256 uint16 safetensors image data>,
    'B06': <256x256 uint16 safetensors image data>,
    'B07': <256x256 uint16 safetensors image data>,
    'B08': <256x256 uint16 safetensors image data>,
    'B8A': <256x256 uint16 safetensors image data>,
    'B09': <256x256 uint16 safetensors image data>,
    'B11': <256x256 uint16 safetensors image data>,
    'B12': <256x256 uint16 safetensors image data>,
  },
'patch_1':
  {
    'B01': <256x256 uint16 safetensors image data>,
    'B02': <256x256 uint16 safetensors image data>,
    'B03': <256x256 uint16 safetensors image data>,
    'B04': <256x256 uint16 safetensors image data>,
    'B05': <256x256 uint16 safetensors image data>,
    'B06': <256x256 uint16 safetensors image data>,
    'B07': <256x256 uint16 safetensors image data>,
    'B08': <256x256 uint16 safetensors image data>,
    'B8A': <256x256 uint16 safetensors image data>,
    'B09': <256x256 uint16 safetensors image data>,
    'B11': <256x256 uint16 safetensors image data>,
    'B12': <256x256 uint16 safetensors image data>,
  },
```

</details>

```python
import lmdb
import numpy as np
# import desired deep-learning library:
# numpy, torch, tensorflow, paddle, flax, mlx
from safetensors.numpy import load
from pathlib import Path

encoded_path = "Encoded-Hydro"

# Make sure to only open the environment once
# and not everytime an item is accessed.
env = lmdb.open(str(encoded_path), readonly=True)

with env.begin() as txn:
  # string encoding is required to map the string to an LMDB key
  safetensor_dict = load(txn.get("patch_0".encode()))

tensor = np.stack(
  [
    safetensor_dict[key]
    for key in [
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
  ]
)
assert tensor.shape == (12, 256, 256)
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
to remote sensing datasets for deep-learning.
Remote sensing deep-learning datasets typically consist of small images
(usually around 120px x 120px) with varying resolutions based on the selected band
(e.g., BigEarthNet's highest resolution is 120px x 120px and the lowest is 20px x 20px).
These images are randomly accessed during training, which differs from the access patterns
in classical machine-learning applications or applications that calculate zonal statistics.
These characteristics make array-structured data formats less suitable for deep-learning applications.

</details>

## Citation

If you use this work, please cite:

```bibtex
@article{clasen2024refinedbigearthnet,
  title={reBEN: Refined BigEarthNet Dataset for Remote Sensing Image Analysis},
  author={Clasen, Kai Norman and Hackel, Leonard and Burgert, Tom and Sumbul, Gencer and Demir, Beg{\"u}m and Markl, Volker},
  year={2024},
  eprint={2407.03653},
  archivePrefix={arXiv},
  primaryClass={cs.CV},
  url={https://arxiv.org/abs/2407.03653},
}
```

[ben]: https://bigearth.net
[LMDB]: https://www.symas.com/lmdb
[s]: https://huggingface.co/docs/safetensors/index
[hyspecnet]: https://hyspecnet.rsim.berlin/
[pyl]: https://lmdb.readthedocs.io/en/release/
[pys]: https://github.com/huggingface/safetensors
[ucmerced]: http://weegee.vision.ucmerced.edu/datasets/landuse.html
[euro]: https://zenodo.org/records/7711810
[ssl4eo-s12]: https://github.com/zhu-xlab/SSL4EO-S12
[major-tom]: https://github.com/ESA-PhiLab/Major-TOM
[hydro]: https://github.com/isaaccorley/hydro-foundation-model/tree/main
