# Testing Guide 🧪

This guide explains how to run tests for the SnowMapPy package.

## Quick Test Commands

### Unit Tests
```bash
# Test core quality control functions
python tests/test_core/test_quality.py

# Test cloud processing structure
python tests/test_cloud/test_basic_cloud.py

# Test local processing structure  
python tests/test_local/test_basic_local.py
```

### Real Cloud Processing Test
```bash
# Test with actual Google Earth Engine data
python tests/test_cloud/real_cloud_test.py
```

**⚠️ Note**: Real cloud tests require:
- Google Earth Engine authentication (`earthengine authenticate`)
- Internet connection
- Several minutes to complete

## Test Structure

- **`test_core/`**: Tests for shared functionality
- **`test_cloud/`**: Tests for Google Earth Engine processing
- **`test_local/`**: Tests for local file processing
- **`results/`**: Test output files

## Expected Results

### Unit Tests
- ✅ Should pass without external dependencies
- ✅ Tests core logic and structure
- ✅ Fast execution (< 1 second)

### Real Cloud Test
- ✅ Downloads real MODIS data from GEE
- ✅ Processes data with quality control
- ✅ Creates output files in `tests/results/cloud/`
- ✅ Takes 5-15 minutes depending on data size

## Troubleshooting

**Import Errors**: Make sure you're running from the package directory
**Authentication Errors**: Run `earthengine authenticate` first
**Missing Files**: Check that test data exists in `tests/data_to_test/` 