# Examples

Real-world workflow examples and Jupyter notebooks for SnowMapPy.

---

## Example Gallery

<div class="grid cards" markdown>

-   :material-map:{ .lg .middle } **Basic Processing**

    ---

    Process one year of snow cover data for a study area.
    
    [:octicons-arrow-right-24: View example](basic-processing.md)

-   :material-chart-timeline:{ .lg .middle } **Multi-Year Analysis**

    ---

    Process multiple decades and analyze trends.
    
    [:octicons-arrow-right-24: View example](multi-year.md)

-   :material-export:{ .lg .middle } **Export Workflows**

    ---

    Export to GeoTIFF, NetCDF, and other formats.
    
    [:octicons-arrow-right-24: View example](export.md)

-   :material-chart-line:{ .lg .middle } **Visualization**

    ---

    Create maps, animations, and time series plots.
    
    [:octicons-arrow-right-24: View example](visualization.md)

</div>

---

## Quick Examples

### Minimal Processing

The simplest possible processing workflow:

```python
from SnowMapPy import process_modis_ndsi_cloud

result, counters = process_modis_ndsi_cloud(
    project_name="your-project",
    shapefile_path="study_area.shp",
    start_date="2020-01-01",
    end_date="2020-12-31",
    output_path="./output"
)
```

### Custom Configuration

Full control over processing parameters:

```python
from SnowMapPy import process_modis_ndsi_cloud

result, counters = process_modis_ndsi_cloud(
    project_name="your-project",
    shapefile_path="study_area.shp",
    start_date="2015-10-01",
    end_date="2020-09-30",
    output_path="./output",
    interpolation_method="linear",
    spatial_correction_method="elevation_mean",
    output_dtype="float32",
    compression="zstd",
    output_name="atlas_snow_5years"
)
```

### Batch Processing

Process multiple regions or time periods:

```python
from SnowMapPy import process_modis_ndsi_cloud
from pathlib import Path

# Define regions
regions = [
    "region_north.shp",
    "region_central.shp", 
    "region_south.shp"
]

# Process each region
for region in regions:
    region_name = Path(region).stem
    print(f"Processing {region_name}...")
    
    result, counters = process_modis_ndsi_cloud(
        project_name="your-project",
        shapefile_path=region,
        start_date="2020-01-01",
        end_date="2020-12-31",
        output_path="./output",
        output_name=f"snow_{region_name}"
    )
    
    print(f"  Completed: {counters['interpolated_pixels']} pixels filled")
```

### Extract Time Series

Extract and analyze time series at specific locations:

```python
import xarray as xr
import matplotlib.pyplot as plt

# Load processed data
ds = xr.open_zarr('./output/snow_cover.zarr')

# Define analysis points
points = {
    "Station A": (33.5, -7.2),
    "Station B": (32.8, -6.5),
    "Station C": (34.1, -7.8)
}

# Extract and plot time series
fig, ax = plt.subplots(figsize=(12, 6))

for name, (lat, lon) in points.items():
    ts = ds['NDSI'].sel(y=lat, x=lon, method='nearest')
    ax.plot(ds.time, ts, label=name, linewidth=1.5)

ax.set_xlabel('Date')
ax.set_ylabel('NDSI (%)')
ax.set_title('Snow Cover Time Series')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('timeseries.png', dpi=150)
```

---

## Jupyter Notebooks

Interactive notebooks are available in the repository:

| Notebook | Description |
|----------|-------------|
| `test_snowmappy.ipynb` | Basic usage and testing |
| `test_interpolation_accuracy.ipynb` | Compare interpolation methods |
| `test_parameter_combinations.ipynb` | Parameter sensitivity analysis |

To run notebooks:

```bash
# Clone repository
git clone https://github.com/haytamelyo/SnowMapPy.git
cd SnowMapPy

# Install with notebook support
pip install -e .
pip install jupyter

# Start Jupyter
jupyter notebook
```
