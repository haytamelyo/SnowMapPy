# Algorithm Overview

This page explains the scientific foundation of SnowMapPy's gap-filling algorithm.

---

## The Cloud Problem

MODIS (Moderate Resolution Imaging Spectroradiometer) provides daily snow cover observations at 500m resolution. However, cloud contamination significantly reduces usable observations:

!!! warning "Challenge"
    
    On average, **40-70% of daily MODIS observations** are obscured by clouds, depending on the region and season.

This creates gaps in snow cover time series that must be filled for continuous monitoring.

---

## Gap-Filling Strategy

SnowMapPy uses a **spatio-temporal gap-filling approach** that combines:

1. **Sensor Fusion** - Combining Terra and Aqua observations
2. **Temporal Interpolation** - Using nearby dates to fill gaps
3. **Spatial Correction** - DEM-based elevation thresholds

### The 6-Day Moving Window

The core algorithm uses a 6-day moving window centered on each target date:

```
Window: [-3, -2, -1, 0, +1, +2]
        ↑               ↑
     3 days before   2 days after
```

For each pixel on day `t`:

1. Collect observations from days `t-3` to `t+2`
2. Remove cloud-contaminated values
3. Apply the selected interpolation method
4. Output the gap-filled value

!!! info "Why 6 Days?"
    
    The window captures typical cloud clearing timescales while preserving snow dynamics. A larger window would smooth rapid melt events; a smaller window would leave more gaps.

---

## Sensor Fusion

MODIS operates on two satellites:

| Satellite | Pass Time | Product |
|-----------|-----------|---------|
| **Terra** | ~10:30 AM | MOD10A1 |
| **Aqua** | ~1:30 PM | MYD10A1 |

SnowMapPy combines both for maximum coverage:

```python
# Fusion logic (simplified)
for each pixel:
    if terra_valid:
        use terra_value  # Morning observation preferred
    elif aqua_valid:
        use aqua_value   # Afternoon as backup
    else:
        mark_as_gap      # Fill later
```

!!! success "Why Prefer Terra?"
    
    Morning observations (Terra) typically have:
    
    - Less afternoon cloud buildup
    - Lower atmospheric water vapor
    - More consistent sun angles

---

## Gap-Filling Process

After sensor fusion, remaining gaps are filled using temporal interpolation:

### Step 1: Extract Window Values

For target pixel $(x, y)$ on day $t$:

$$
W_{t} = \{v_{t-3}, v_{t-2}, v_{t-1}, v_{t}, v_{t+1}, v_{t+2}\}
$$

where $v_i$ is the pixel value on day $i$.

### Step 2: Identify Valid Values

Remove gaps and cloud flags:

$$
V_{t} = \{v_i \in W_t : v_i \neq \text{NoData}\}
$$

### Step 3: Interpolate

Apply the selected method (nearest, linear, or cubic) using the valid values and their temporal positions.

### Step 4: Apply Spatial Correction

If enabled, adjust the interpolated value based on DEM-derived elevation thresholds.

---

## Quality Assurance

SnowMapPy applies QA filtering to remove unreliable observations:

| NDSI_Snow_Cover Value | Interpretation | Action |
|-----------------------|----------------|--------|
| 0-100 | Valid NDSI | Keep |
| 200 | Missing data | Mark as gap |
| 201 | No decision | Mark as gap |
| 211 | Night | Mark as gap |
| 237 | Inland water | Preserve |
| 239 | Ocean | Preserve |
| 250 | Cloud | Mark as gap |
| 254 | Detector saturated | Mark as gap |
| 255 | Fill value | Mark as gap |

---

## Performance Considerations

The algorithm processes time series **pixel-by-pixel** using Numba JIT compilation:

```python
@njit(parallel=True)
def process_time_series(data, ...):
    for i in prange(n_pixels):  # Parallel loop
        for t in range(n_times):
            # Process each pixel-time combination
            interpolated[i, t] = interpolate(...)
```

!!! tip "Performance"
    
    Numba JIT compilation provides **50-200x speedup** over pure Python/NumPy implementations.

---

## Validation

The algorithm has been validated against:

- In-situ snow station measurements
- Landsat snow products (30m validation)
- Regional snow cover maps

See the [Scientific Foundation](../index.md#medal_military-scientific-foundation) section for detailed validation results.

---

## Next Steps

- [Interpolation Methods](interpolation.md) - Choose the right interpolation
- [Spatial Correction](spatial-correction.md) - DEM-based adjustments
