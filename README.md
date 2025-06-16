# SnowMapPy

A Python Package for Automated Snow Cover Mapping and Monitoring in the Mediterranean Atlas Mountains.

## Table of content

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Modules](#modules)
- [Contributing](#contributing)
- [License](#license)

## Features

The package significantly enhances the efficiency and effectiveness of snow hydrology research by automating key processes and providing robust tools for data analysis and model development. This enables researchers to focus more on refining model inputs and interpreting results, ultimately advancing the understanding and management of snow-related water resources.
Currently, the package is tailored for the MODIS NDSI snow cover data, specifically from the Terra and Aqua satellite products. All currently available functions are adapted to efficiently handle and process this data. Users can automate data preparation with minimal inputs, including directories for the data, DEM, shapefile, and the output location, making it easy to organize and prepare datasets. For time series analysis, users need only add the directories for Aqua and Terra data (processed in previous steps), the DEM, output location, and a static filename for all images.

**Easy**: Designed with simplicity in mind, the package requires only a few key directories, allowing users to process data seamlessly. For example, the data preparation function needs a data directory, DEM directory, shapefile directory, and a save directory, while the time series function only requires directories for the processed Aqua and Terra data, DEM, output location, and the static filename.

**Flexible**: The package offers extensive flexibility, giving users control over data reprojection and output formats. If needed, the data can be reprojected to match the coordinate reference system (CRS) of a specific input (e.g., prioritizing MODIS CRS will reproject and reshape the DEM accordingly). Additionally, the package supports the flexible Zarr format for output storage, allowing users to either use the default chunk size and compressor or run an optimal combination algorithm to identify the best chunking and compression settings for efficient storage.

**Open source**: As an open-source project, the package encourages collaboration and continuous improvement from the community. Users can freely access, modify, and contribute to the codebase, ensuring transparency and fostering innovation in snow hydrology research. 

## Installation

### Requirements

- Python 3.8 or higher
- Dependencies:
    - `os`, `sys`, `tqdm`, `zarr`, `json`, `numpy`, `scipy`, `xarray`, `joblib`, `pandas`, `affine`, `datetime`, `rasterio`, `geopandas`, `numcodecs`

To install, run:

```bash
pip install git+
```

Alternatively, clone the repository and install dependencies manually:

```bash
git clone 
cd your-repo-name
pip install -r requirements.txt
```

## Quick Start

1. **Prepare data**:
   ```python
   from local_data.prepare_modis import prepare_modis

   prepare_modis(
      data_dir="/path/to/modis_data",
      dem_dir="/path/to/dem",
      shapefile_dir="/path/to/roi_shapefile",
      save_dir="/path/to/output"
   )
   ```

2. **Time series**:
   ```python
   from local_data.time_serie import modis_time_serie

   modis_time_serie(
      aqua_dir="/path/to/aqua_data",
      terra_dir="/path/to/terra_data",
      dem_dir="/path/to/processed_dem",
      output_dir="/path/to/time_series_output",
      filename="MODIS_time_series"
   )
   ```

## Modules

A breakdown of the current modules:

- **clipping.py**: Handles spatial clipping of datasets.
- **data_io.py**: Responsible for data loading and saving.
- **file_handling.py**: Manages file paths, formats, and error handling.
- **prepare_modis.py**: Preprocesses MODIS data by reprojecting, alligning and clipping it to a defined region.
- **reprojection.py**: Handles reprojection of datasets.
- **temporal_interpolation.py**: Interpolates data across time.
- **time_serie.py**: Manages and processes time series data.

## Contributing

Contributions are welcome!

## License
