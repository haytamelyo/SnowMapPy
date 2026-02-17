# Multi-Year Analysis

Process multiple decades of snow cover data and analyze long-term trends.

---

## Overview

This example demonstrates how to:

1. Process multiple years of data efficiently
2. Combine yearly datasets
3. Analyze long-term trends

---

## Strategy: Process in Yearly Chunks

For multi-decadal analysis, process one year at a time to manage memory:

```python
from SnowMapPy import process_modis_ndsi_cloud
from pathlib import Path
import xarray as xr

# Configuration
PROJECT = "your-gee-project"
SHAPEFILE = "study_area.shp"
OUTPUT_DIR = Path("./output")
YEARS = range(2000, 2024)  # 24 years

# Process each year
for year in YEARS:
    print(f"\n{'='*50}")
    print(f"Processing {year}")
    print('='*50)
    
    result, counters = process_modis_ndsi_cloud(
        project_name=PROJECT,
        shapefile_path=SHAPEFILE,
        start_date=f"{year}-01-01",
        end_date=f"{year}-12-31",
        output_path=str(OUTPUT_DIR),
        output_name=f"snow_cover_{year}",
        interpolation_method="nearest"
    )
    
    print(f"  Completed: {len(result.time)} days processed")
```

---

## Combine Yearly Datasets

After processing, combine into a single dataset:

```python
import xarray as xr
from pathlib import Path

# Find all yearly files
output_dir = Path("./output")
zarr_files = sorted(output_dir.glob("snow_cover_*.zarr"))

print(f"Found {len(zarr_files)} yearly datasets")

# Load and concatenate
datasets = []
for zarr_path in zarr_files:
    ds = xr.open_zarr(zarr_path)
    datasets.append(ds)
    print(f"  Loaded {zarr_path.name}: {len(ds.time)} days")

# Concatenate along time dimension
combined = xr.concat(datasets, dim='time')
combined = combined.sortby('time')

print(f"\nCombined dataset: {len(combined.time)} days")
print(f"  From {combined.time.values[0]} to {combined.time.values[-1]}")

# Save combined dataset
combined.to_zarr("./output/snow_cover_2000_2023.zarr", mode='w')
```

---

## Trend Analysis

### Annual Snow Cover Statistics

```python
import xarray as xr
import pandas as pd
import matplotlib.pyplot as plt

# Load combined data
ds = xr.open_zarr("./output/snow_cover_2000_2023.zarr")

# Calculate annual mean snow cover
annual_mean = ds['NDSI'].groupby('time.year').mean(dim='time').mean(dim=['x', 'y'])

# Create DataFrame for analysis
df = pd.DataFrame({
    'year': annual_mean.year.values,
    'mean_ndsi': annual_mean.values
})

# Linear trend
from scipy import stats
slope, intercept, r_value, p_value, std_err = stats.linregress(
    df['year'], df['mean_ndsi']
)

print(f"Trend: {slope:.3f} NDSI/year")
print(f"R²: {r_value**2:.3f}")
print(f"p-value: {p_value:.4f}")

# Plot
fig, ax = plt.subplots(figsize=(12, 5))
ax.bar(df['year'], df['mean_ndsi'], color='steelblue', alpha=0.7)
ax.plot(df['year'], intercept + slope * df['year'], 'r--', 
        label=f'Trend: {slope:.3f}/year (p={p_value:.3f})')
ax.set_xlabel('Year')
ax.set_ylabel('Mean NDSI (%)')
ax.set_title('Annual Mean Snow Cover (2000-2023)')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('annual_trend.png', dpi=150)
```

### Snow Season Analysis

```python
import xarray as xr
import pandas as pd
import matplotlib.pyplot as plt

ds = xr.open_zarr("./output/snow_cover_2000_2023.zarr")

# Calculate snow season metrics for each year
results = []

for year in range(2000, 2023):
    # Water year: October to September
    start = f"{year}-10-01"
    end = f"{year+1}-09-30"
    
    wy_data = ds['NDSI'].sel(time=slice(start, end))
    
    # Regional mean time series
    regional_ts = wy_data.mean(dim=['x', 'y'])
    
    # Snow season metrics (NDSI > 50%)
    snow_days = (regional_ts > 50).sum().values
    max_snow = regional_ts.max().values
    
    # First and last snow day
    snow_mask = regional_ts > 50
    if snow_mask.any():
        first_snow = regional_ts.time[snow_mask].values[0]
        last_snow = regional_ts.time[snow_mask].values[-1]
    else:
        first_snow = None
        last_snow = None
    
    results.append({
        'water_year': f"{year}-{year+1}",
        'snow_days': snow_days,
        'max_ndsi': max_snow,
        'first_snow': first_snow,
        'last_snow': last_snow
    })

df = pd.DataFrame(results)
print(df)
```

### Spatial Trend Maps

```python
import xarray as xr
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt

ds = xr.open_zarr("./output/snow_cover_2000_2023.zarr")

# Calculate pixel-wise trend
def calculate_trend(y):
    """Calculate linear trend slope."""
    if np.all(np.isnan(y)):
        return np.nan
    x = np.arange(len(y))
    mask = ~np.isnan(y)
    if mask.sum() < 3:
        return np.nan
    slope, _, _, _, _ = stats.linregress(x[mask], y[mask])
    return slope

# Annual means per pixel
annual_mean = ds['NDSI'].groupby('time.year').mean(dim='time')

# Apply trend calculation
trend_map = xr.apply_ufunc(
    calculate_trend,
    annual_mean,
    input_core_dims=[['year']],
    vectorize=True,
    dask='parallelized',
    output_dtypes=[float]
)

# Plot trend map
fig, ax = plt.subplots(figsize=(10, 8))
trend_map.plot(
    ax=ax,
    cmap='RdBu',
    center=0,
    vmin=-2, vmax=2,
    cbar_kwargs={'label': 'NDSI trend (%/year)'}
)
ax.set_title('Snow Cover Trends (2000-2023)')
plt.tight_layout()
plt.savefig('trend_map.png', dpi=150)
```

---

## Memory Considerations

For very long time series:

1. **Process yearly** - Don't try to process 20+ years at once
2. **Use Dask** - Keep data lazy until computation
3. **Stream results** - Calculate and save statistics incrementally

```python
# Example: Incremental statistics calculation
import xarray as xr
import numpy as np

# Initialize accumulators
sum_ndsi = None
count = 0

for year in range(2000, 2024):
    ds = xr.open_zarr(f"./output/snow_cover_{year}.zarr")
    
    # Compute annual mean
    annual = ds['NDSI'].mean(dim='time').compute()
    
    if sum_ndsi is None:
        sum_ndsi = annual
    else:
        sum_ndsi = sum_ndsi + annual
    count += 1
    
    # Clear memory
    del ds, annual

# Final climatology
climatology = sum_ndsi / count
climatology.to_netcdf("climatology_2000_2023.nc")
```
