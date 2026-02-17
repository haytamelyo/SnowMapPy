# Visualization

Create maps, animations, and time series plots from SnowMapPy output.

---

## Overview

This guide covers various visualization techniques for snow cover data.

---

## Static Maps

### Basic Snow Cover Map

```python
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

ds = xr.open_zarr('./output/snow_cover.zarr')

# Select a winter day
data = ds['NDSI'].sel(time='2020-02-15', method='nearest')

fig, ax = plt.subplots(
    figsize=(10, 8),
    subplot_kw={'projection': ccrs.PlateCarree()}
)

# Plot data
im = data.plot(
    ax=ax,
    transform=ccrs.PlateCarree(),
    cmap='Blues',
    vmin=0, vmax=100,
    add_colorbar=False
)

# Add features
ax.add_feature(cfeature.BORDERS, linestyle='-', alpha=0.5)
ax.add_feature(cfeature.COASTLINE)
ax.gridlines(draw_labels=True, alpha=0.3)

# Colorbar
cbar = plt.colorbar(im, ax=ax, shrink=0.7, pad=0.05)
cbar.set_label('NDSI (%)')

ax.set_title('Snow Cover - February 15, 2020', fontsize=14)
plt.tight_layout()
plt.savefig('snow_map.png', dpi=200, bbox_inches='tight')
plt.show()
```

### Multi-Panel Comparison

```python
import xarray as xr
import matplotlib.pyplot as plt

ds = xr.open_zarr('./output/snow_cover.zarr')

# Select seasonal dates
dates = ['2020-01-15', '2020-04-15', '2020-07-15', '2020-10-15']
titles = ['Winter', 'Spring', 'Summer', 'Fall']

fig, axes = plt.subplots(2, 2, figsize=(12, 10))

for ax, date, title in zip(axes.flat, dates, titles):
    data = ds['NDSI'].sel(time=date, method='nearest')
    im = data.plot(
        ax=ax,
        cmap='Blues',
        vmin=0, vmax=100,
        add_colorbar=False
    )
    ax.set_title(f'{title} ({date})')
    ax.set_aspect('equal')

# Shared colorbar
fig.subplots_adjust(right=0.85)
cbar_ax = fig.add_axes([0.88, 0.15, 0.02, 0.7])
fig.colorbar(im, cax=cbar_ax, label='NDSI (%)')

plt.savefig('seasonal_comparison.png', dpi=150)
plt.show()
```

---

## Time Series Plots

### Regional Mean

```python
import xarray as xr
import matplotlib.pyplot as plt
import pandas as pd

ds = xr.open_zarr('./output/snow_cover.zarr')

# Calculate regional mean
regional_mean = ds['NDSI'].mean(dim=['x', 'y'])

# Plot
fig, ax = plt.subplots(figsize=(14, 5))
regional_mean.plot(ax=ax, linewidth=0.8, color='steelblue')

ax.set_xlabel('Date')
ax.set_ylabel('Mean NDSI (%)')
ax.set_title('Regional Snow Cover Time Series')
ax.grid(True, alpha=0.3)

# Add monthly smoothing
monthly = regional_mean.resample(time='1M').mean()
monthly.plot(ax=ax, linewidth=2, color='red', label='Monthly mean')
ax.legend()

plt.tight_layout()
plt.savefig('timeseries.png', dpi=150)
plt.show()
```

### Multiple Elevations

```python
import xarray as xr
import matplotlib.pyplot as plt
import numpy as np

ds = xr.open_zarr('./output/snow_cover.zarr')
dem = xr.open_zarr('./output/dem.zarr')['elevation']  # If available

# Define elevation zones
zones = [
    (2000, 2500, 'Low (2000-2500m)'),
    (2500, 3000, 'Mid (2500-3000m)'),
    (3000, 4000, 'High (3000-4000m)')
]

fig, ax = plt.subplots(figsize=(14, 5))

for low, high, label in zones:
    mask = (dem >= low) & (dem < high)
    zone_data = ds['NDSI'].where(mask).mean(dim=['x', 'y'])
    zone_data.plot(ax=ax, label=label, linewidth=1.5)

ax.set_xlabel('Date')
ax.set_ylabel('Mean NDSI (%)')
ax.set_title('Snow Cover by Elevation Zone')
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('elevation_timeseries.png', dpi=150)
plt.show()
```

---

## Animations

### Basic Animation

```python
import xarray as xr
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import matplotlib.dates as mdates

ds = xr.open_zarr('./output/snow_cover.zarr')

fig, ax = plt.subplots(figsize=(10, 8))

# Initialize
im = ax.imshow(
    ds['NDSI'].isel(time=0).values,
    cmap='Blues',
    vmin=0, vmax=100,
    extent=[
        float(ds.x.min()), float(ds.x.max()),
        float(ds.y.min()), float(ds.y.max())
    ],
    origin='lower'
)
cbar = plt.colorbar(im, ax=ax, label='NDSI (%)')
title = ax.set_title('')

def update(frame):
    data = ds['NDSI'].isel(time=frame).values
    im.set_array(data)
    date = str(ds.time.values[frame])[:10]
    title.set_text(f'Snow Cover - {date}')
    return im, title

# Create animation
anim = FuncAnimation(
    fig, update,
    frames=len(ds.time),
    interval=100,
    blit=True
)

# Save as GIF
anim.save('snow_animation.gif', writer='pillow', fps=10)
print("Saved: snow_animation.gif")
```

### HTML Animation (Interactive)

```python
import xarray as xr
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from IPython.display import HTML

ds = xr.open_zarr('./output/snow_cover.zarr')

fig, ax = plt.subplots(figsize=(10, 8))
im = ax.imshow(
    ds['NDSI'].isel(time=0).values,
    cmap='Blues', vmin=0, vmax=100,
    extent=[float(ds.x.min()), float(ds.x.max()),
            float(ds.y.min()), float(ds.y.max())],
    origin='lower'
)
plt.colorbar(im, ax=ax, label='NDSI (%)')
title = ax.set_title('')

def update(frame):
    im.set_array(ds['NDSI'].isel(time=frame).values)
    title.set_text(f'Snow Cover - {str(ds.time.values[frame])[:10]}')
    return im, title

anim = FuncAnimation(fig, update, frames=len(ds.time), interval=100)

# Display in Jupyter
HTML(anim.to_jshtml())
```

---

## Statistical Visualizations

### Snow Cover Duration

```python
import xarray as xr
import matplotlib.pyplot as plt

ds = xr.open_zarr('./output/snow_cover.zarr')

# Count days with snow (NDSI > 50%)
snow_days = (ds['NDSI'] > 50).sum(dim='time')

fig, ax = plt.subplots(figsize=(10, 8))
im = snow_days.plot(
    ax=ax,
    cmap='YlGnBu',
    cbar_kwargs={'label': 'Days with snow (NDSI > 50%)'}
)
ax.set_title(f'Snow Cover Duration ({ds.time.values[0][:4]})')
plt.savefig('snow_duration.png', dpi=150)
plt.show()
```

### Snow Cover Variability

```python
import xarray as xr
import matplotlib.pyplot as plt

ds = xr.open_zarr('./output/snow_cover.zarr')

# Calculate coefficient of variation
mean = ds['NDSI'].mean(dim='time')
std = ds['NDSI'].std(dim='time')
cv = (std / mean * 100).where(mean > 0)

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Mean
mean.plot(ax=axes[0], cmap='Blues', cbar_kwargs={'label': 'NDSI (%)'})
axes[0].set_title('Mean Snow Cover')

# CV
cv.plot(ax=axes[1], cmap='Oranges', vmax=100, cbar_kwargs={'label': 'CV (%)'})
axes[1].set_title('Coefficient of Variation')

plt.tight_layout()
plt.savefig('snow_variability.png', dpi=150)
plt.show()
```

---

## Interactive Visualization

### With hvPlot

```python
import xarray as xr
import hvplot.xarray

ds = xr.open_zarr('./output/snow_cover.zarr')

# Interactive time slider
plot = ds['NDSI'].hvplot(
    x='x', y='y',
    cmap='Blues',
    clim=(0, 100),
    widget_type='scrubber',
    widget_location='bottom',
    frame_width=600,
    frame_height=500
)

# Save to HTML
hvplot.save(plot, 'interactive_snow.html')
```

### With Folium (Web Map)

```python
import xarray as xr
import folium
import numpy as np
from folium import raster_layers

ds = xr.open_zarr('./output/snow_cover.zarr')
data = ds['NDSI'].sel(time='2020-02-15', method='nearest')

# Create folium map
center = [float(data.y.mean()), float(data.x.mean())]
m = folium.Map(location=center, zoom_start=7)

# Add raster overlay
folium.raster_layers.ImageOverlay(
    image=data.values,
    bounds=[
        [float(data.y.min()), float(data.x.min())],
        [float(data.y.max()), float(data.x.max())]
    ],
    colormap=lambda x: (0.1, 0.4, 0.8, x/100),  # Blue colormap
    opacity=0.7
).add_to(m)

m.save('snow_webmap.html')
print("Saved: snow_webmap.html")
```

---

## Publication-Quality Figures

```python
import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# Set publication style
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 10,
    'axes.linewidth': 0.8,
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,
})

ds = xr.open_zarr('./output/snow_cover.zarr')
data = ds['NDSI'].sel(time='2020-02-15', method='nearest')

fig, ax = plt.subplots(figsize=(3.5, 3))  # Single column width

im = ax.imshow(
    data.values,
    cmap='Blues',
    vmin=0, vmax=100,
    extent=[float(data.x.min()), float(data.x.max()),
            float(data.y.min()), float(data.y.max())],
    origin='lower'
)

ax.set_xlabel('Longitude (°)')
ax.set_ylabel('Latitude (°)')
ax.xaxis.set_major_locator(mticker.MaxNLocator(5))
ax.yaxis.set_major_locator(mticker.MaxNLocator(5))

cbar = plt.colorbar(im, ax=ax, pad=0.02, shrink=0.9)
cbar.set_label('NDSI (%)', fontsize=9)

plt.tight_layout()
plt.savefig('figure_publication.pdf', dpi=300, bbox_inches='tight')
plt.savefig('figure_publication.png', dpi=300, bbox_inches='tight')
```
