# CLI Reference

SnowMapPy includes a command-line interface for processing without writing Python code.

---

## Overview

The CLI provides access to all major SnowMapPy functions from the terminal.

```bash
# General help
snowmappy --help

# Version
snowmappy --version
```

---

## Commands

### `process`

Process MODIS NDSI snow cover data.

```bash
snowmappy process [OPTIONS]
```

#### Required Options

| Option | Description |
|--------|-------------|
| `--project`, `-p` | Google Earth Engine project ID |
| `--shapefile`, `-s` | Path to study area shapefile |
| `--start`, `-start` | Start date (YYYY-MM-DD) |
| `--end`, `-e` | End date (YYYY-MM-DD) |
| `--output`, `-o` | Output directory path |

#### Optional Options

| Option | Default | Description |
|--------|---------|-------------|
| `--interpolation`, `-i` | `nearest` | Interpolation method |
| `--spatial-correction`, `-sc` | `elevation_mean` | Spatial correction method |
| `--dtype`, `-d` | `float16` | Output data type |
| `--compression`, `-c` | `zstd` | Compression codec |
| `--name`, `-n` | Auto-generated | Custom output filename |

#### Examples

**Basic usage:**

```bash
snowmappy process \
    --project my-gee-project \
    --shapefile study_area.shp \
    --start 2020-01-01 \
    --end 2020-12-31 \
    --output ./output
```

**Full options:**

```bash
snowmappy process \
    --project my-gee-project \
    --shapefile study_area.shp \
    --start 2015-10-01 \
    --end 2020-09-30 \
    --output ./output \
    --interpolation linear \
    --spatial-correction elevation_mean \
    --dtype float32 \
    --compression zstd \
    --name atlas_snow_cover
```

**Short form:**

```bash
snowmappy process \
    -p my-gee-project \
    -s study_area.shp \
    --start 2020-01-01 \
    -e 2020-12-31 \
    -o ./output \
    -i nearest
```

---

### `info`

Display information about a processed dataset.

```bash
snowmappy info [PATH]
```

#### Arguments

| Argument | Description |
|----------|-------------|
| `PATH` | Path to Zarr dataset |

#### Example

```bash
snowmappy info ./output/study_area_NDSI.zarr
```

Output:
```
Dataset: study_area_NDSI.zarr
============================
Dimensions:
  time: 366
  y: 350
  x: 280

Coordinates:
  time: 2020-01-01 to 2020-12-31
  y: 31.0 to 34.5
  x: -8.5 to -5.0

Variables:
  NDSI: float16 (366, 350, 280)

Size on disk: 45.2 MB
```

---

### `export`

Export processed data to other formats.

```bash
snowmappy export [OPTIONS] INPUT OUTPUT
```

#### Arguments

| Argument | Description |
|----------|-------------|
| `INPUT` | Path to Zarr dataset |
| `OUTPUT` | Output file path |

#### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--format`, `-f` | Auto-detect | Output format (`geotiff`, `netcdf`) |
| `--time`, `-t` | All | Time index or range |

#### Examples

**Export to GeoTIFF (single time):**

```bash
snowmappy export \
    ./output/snow_cover.zarr \
    ./exports/snow_day1.tif \
    --time 0
```

**Export to NetCDF:**

```bash
snowmappy export \
    ./output/snow_cover.zarr \
    ./exports/snow_cover.nc \
    --format netcdf
```

---

## Interpolation Methods

| Value | CLI Flag | Description |
|-------|----------|-------------|
| Nearest | `-i nearest` | Nearest neighbor |
| Linear | `-i linear` | Linear interpolation |
| Cubic | `-i cubic` | Cubic spline |

---

## Spatial Correction Methods

| Value | CLI Flag | Description |
|-------|----------|-------------|
| None | `-sc none` | No correction |
| Elevation Mean | `-sc elevation_mean` | DEM-based |

---

## Batch Processing with Shell Scripts

Process multiple years:

=== "Bash (Linux/macOS)"
    ```bash
    #!/bin/bash
    PROJECT="my-gee-project"
    SHAPEFILE="study_area.shp"
    OUTPUT="./output"
    
    for YEAR in {2015..2020}; do
        echo "Processing $YEAR..."
        snowmappy process \
            -p $PROJECT \
            -s $SHAPEFILE \
            --start ${YEAR}-01-01 \
            -e ${YEAR}-12-31 \
            -o $OUTPUT \
            -n snow_cover_${YEAR}
    done
    ```

=== "PowerShell (Windows)"
    ```powershell
    $PROJECT = "my-gee-project"
    $SHAPEFILE = "study_area.shp"
    $OUTPUT = "./output"
    
    2015..2020 | ForEach-Object {
        Write-Host "Processing $_..."
        snowmappy process `
            -p $PROJECT `
            -s $SHAPEFILE `
            --start "$_-01-01" `
            -e "$_-12-31" `
            -o $OUTPUT `
            -n "snow_cover_$_"
    }
    ```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `EE_PROJECT` | Default GEE project ID |
| `SNOWMAPPY_OUTPUT` | Default output directory |

Using environment variables:

```bash
export EE_PROJECT="my-gee-project"
export SNOWMAPPY_OUTPUT="./output"

# Now project and output are optional
snowmappy process \
    -s study_area.shp \
    --start 2020-01-01 \
    -e 2020-12-31
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | File not found |
| 4 | GEE authentication error |
