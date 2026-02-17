# Installation

This guide covers all installation methods for SnowMapPy.

---

## Prerequisites

Before installing SnowMapPy, ensure you have:

- **Python 3.11 or higher**
- A Google Earth Engine account (free for research)
- Sufficient disk space for output data

!!! tip "Recommended Setup"
    
    We recommend using a virtual environment to avoid dependency conflicts:
    
    ```bash
    python -m venv snowmappy-env
    source snowmappy-env/bin/activate  # Linux/macOS
    snowmappy-env\Scripts\activate     # Windows
    ```

---

## Installation Methods

### :material-package-variant: PyPI (Recommended)

Install the latest stable release from PyPI:

```bash
pip install SnowMapPy
```

### :material-update: Upgrade Existing Installation

To upgrade to the latest version:

```bash
pip install --upgrade SnowMapPy
```

### :material-source-branch: Development Version

Install the latest development version directly from GitHub:

```bash
pip install git+https://github.com/haytamelyo/SnowMapPy.git
```

### :material-download: From Source

For development or to modify the code:

```bash
# Clone the repository
git clone https://github.com/haytamelyo/SnowMapPy.git
cd SnowMapPy

# Install in editable mode
pip install -e .
```

---

## Dependencies

SnowMapPy automatically installs the following dependencies:

| Package | Purpose |
|---------|---------|
| `earthengine-api` | Google Earth Engine access |
| `xarray`, `dask` | Lazy data loading and manipulation |
| `zarr` | Efficient data storage |
| `numba` | JIT-compiled kernels |
| `geopandas` | Vector data handling |
| `rasterio` | Raster I/O |
| `numpy` | Array operations |
| `tqdm` | Progress indicators |
| `rich` | Console formatting |
| `click` | CLI framework |

---

## Google Earth Engine Setup

SnowMapPy requires Google Earth Engine authentication. If you haven't set this up:

### 1. Create a GEE Account

Visit [Google Earth Engine](https://earthengine.google.com/) and sign up for an account.

!!! note
    
    GEE is free for research, education, and nonprofit use.

### 2. Create a Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note your **project ID** (e.g., `my-gee-project`)

### 3. Authenticate

Run the following command to authenticate:

```bash
earthengine authenticate
```

This will:

1. Open a browser window for Google sign-in
2. Generate authentication credentials
3. Save credentials to your local machine

!!! tip "Service Account Authentication"
    
    For automated workflows or servers, use a service account:
    
    ```python
    import ee
    
    credentials = ee.ServiceAccountCredentials(
        'your-service-account@project.iam.gserviceaccount.com',
        'path/to/private-key.json'
    )
    ee.Initialize(credentials, project='your-project-id')
    ```

---

## Verify Installation

Test that everything is working:

```python
import SnowMapPy as smp

# Check version
print(f"SnowMapPy version: {smp.__version__}")

# Test GEE connection
from SnowMapPy.cloud import initialize_gee
initialize_gee(project="your-gee-project")
print("Google Earth Engine connected successfully!")
```

Expected output:

```
SnowMapPy version: 1.0.0
Google Earth Engine connected successfully!
```

---

## Troubleshooting

### Common Issues

??? failure "ImportError: No module named 'SnowMapPy'"
    
    **Cause**: Package not installed or wrong Python environment.
    
    **Solution**: 
    ```bash
    # Verify you're in the correct environment
    which python  # Linux/macOS
    where python  # Windows
    
    # Reinstall
    pip install SnowMapPy
    ```

??? failure "EEException: Not signed in"
    
    **Cause**: Google Earth Engine credentials not set.
    
    **Solution**:
    ```bash
    earthengine authenticate
    ```

??? failure "EEException: Project not found"
    
    **Cause**: Invalid or missing project ID.
    
    **Solution**: 
    
    1. Verify your project exists in [Google Cloud Console](https://console.cloud.google.com/)
    2. Enable the Earth Engine API for your project
    3. Use the correct project ID (not name)

??? failure "MemoryError during processing"
    
    **Cause**: Insufficient RAM for the study area size.
    
    **Solution**:
    
    - Use a smaller study area
    - Process in yearly chunks instead of multi-decade
    - Ensure server-side reprojection is enabled (default)

---

## Optional Dependencies

For development and testing:

```bash
pip install SnowMapPy[dev]
```

This installs:

- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting
- `black` - Code formatting
- `mypy` - Type checking

---

## Next Steps

Once installed, proceed to:

- [Quick Start](quickstart.md) - Run your first analysis
- [GEE Setup](gee-setup.md) - Detailed Google Earth Engine configuration
