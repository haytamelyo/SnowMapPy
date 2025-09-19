# SnowMapPy 🌨️

A Python package for processing MODIS NDSI (Normalized Difference Snow Index) data from local files and Google Earth Engine. Designed for hydrologists, geographers, and water resource managers, SnowMapPy simplifies snow cover analysis with minimal Python expertise required.

---

## 📋 Table of Contents

- [Features](#features)
- [Installation](#installation)
  - [Option 1: Install with pip](#option-1-install-with-pip)
  - [Option 2: Run with Docker](#option-2-run-with-docker)
  - [Option 3: Install with Conda (Coming soon...)](#option-3-install-with-conda-coming-soon)
- [Quick Start](#quick-start)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## ✨ Features

- **Cloud Processing**: Process MODIS NDSI data directly from Google Earth Engine.
- **Local Processing**: Handle locally stored MODIS NDSI files.
- **Quality Control**: Mask invalid data using advanced techniques.
- **Temporal Interpolation**: Fill missing data points efficiently.
- **Spatial Operations**: Clip data to regions of interest.
- **Data Export**: Save processed data in Zarr format.

---

## 🚀 Installation

SnowMapPy requires Python 3.8 or higher. We recommend creating a virtual environment for installation.

### Option 1: Install with pip

1. **Create a Virtual Environment**  
   ```bash
   python -m venv snowmappy_env
   source snowmappy_env/bin/activate  # macOS/Linux
   snowmappy_env\Scripts\activate     # Windows
   ```

2. **Install SnowMapPy**  
   ```bash
   pip install SnowMapPy
   ```

### Option 2: Run with Docker

1. **Pull the Docker Image**  
   ```bash
   docker pull your-dockerhub-username/snowmappy:1.0.3
   ```

2. **Run the Container**  
   ```bash
   docker run -it your-dockerhub-username/snowmappy:1.0.3
   ```

3. **Mount Local Data (Optional)**  
   To process local files, mount your data directory:
   ```bash
   docker run -it -v /path/to/data:/workspace your-dockerhub-username/snowmappy:1.0.3
   ```

### Option 3: Install with Conda (Coming soon...)

Install SnowMapPy directly from Conda-Forge:
```bash
conda install -c conda-forge snowmappy
```

---

## 🎯 Quick Start

### Cloud Processing Example

```python
from SnowMapPy.cloud.processor import process_modis_ndsi_cloud

# Process MODIS NDSI data from Google Earth Engine
result = process_modis_ndsi_cloud(
    project_name="your-gee-project",
    shapefile_path="path/to/roi.shp",
    start_date="2023-01-01",
    end_date="2023-01-31",
    output_path="output/",
    file_name="snow_cover"
)
```

### Local Processing Example

```python
from SnowMapPy.local.processor import process_modis_ndsi_local

# Process locally stored MODIS NDSI files
result = process_modis_ndsi_local(
    mod_dir="path/to/MOD/files/",
    myd_dir="path/to/MYD/files/",
    dem_file="path/to/dem.tif",
    output_path="output/",
    file_name="local_snow_cover"
)
```

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### 1. **GDAL or Proj Library Not Found**
- **Solution for Conda**: Ensure you installed the package from Conda-Forge:
  ```bash
  conda install -c conda-forge snowmappy
  ```

#### 2. **Earth Engine Authentication Fails**
- **Solution**: Re-authenticate:
  ```bash
  earthengine authenticate --force
  ```

#### 3. **Memory Errors During Processing**
- **Solutions**:
  - Reduce the date range or spatial extent.
  - Increase virtual memory/swap space.
  - Use a machine with more RAM.

---

## 🤝 Contributing

1. Fork the repository.
2. Create a feature branch.
3. Commit your changes.
4. Push to the branch.
5. Open a Pull Request.

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
