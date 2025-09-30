#!/usr/bin/env python3
"""
Real Cloud Processing Test for SnowMapPy Package

This script tests the actual cloud processing functionality using Google Earth Engine.
It downloads and processes real MODIS NDSI data with quality control.

Usage:
    python test_real_cloud_processing.py

Configuration:
    Edit the CONFIG section below to customize:
    - Google Earth Engine project name
    - Authentication method
    - Date range
    - Region of interest
    - Output settings
"""

import os
import sys
import xarray as xr
from datetime import datetime
import traceback

# Add the package directory to the path to enable imports
current_dir = os.path.dirname(os.path.abspath(__file__))
package_dir = os.path.dirname(os.path.dirname(current_dir))  # Go up two levels to reach package root
sys.path.insert(0, package_dir)

# =============================================================================
# CONFIGURATION - EDIT THESE VALUES
# =============================================================================

# Google Earth Engine Configuration
GEE_PROJECT_NAME = "ee-pfe2025"  # Your GEE project name

# Authentication Method (choose one):
# Option 1: Service Account (recommended for automated testing)
USE_SERVICE_ACCOUNT = False
SERVICE_ACCOUNT_KEY_PATH = "path/to/your/service-account-key.json"

# Option 2: Personal Account (interactive)
USE_PERSONAL_ACCOUNT = True
# If using personal account, you'll need to authenticate manually

# Data Processing Configuration
START_DATE = "2016-07-01"  # Start date for data download
END_DATE = "2016-07-30"    # End date for data download

# Region of Interest (ROI)
# Option 1: Use shapefile
USE_SHAPEFILE = True
SHAPEFILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),  # Go up to package root
    'tests', 
    'data_to_test', 
    'SHP', 
    'NewSA.shp'
)

# Option 2: Use bounding box coordinates
USE_BOUNDING_BOX = False
BOUNDING_BOX = {
    'west': -10.0,   # Western longitude
    'east': 5.0,     # Eastern longitude  
    'south': 35.0,   # Southern latitude
    'north': 45.0    # Northern latitude
}

# Output Configuration
OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),  # Go up to package root
    'tests', 
    'results', 
    'cloud'
)
OUTPUT_FILENAME = "cloud_result"
SAVE_ORIGINAL_DATA = False

# Processing Options
PROCESSING_OPTIONS = {
    'apply_quality_control': True,
    'interpolate_missing': True,
    'save_intermediate': False
}

# =============================================================================
# TEST FUNCTIONS
# =============================================================================

def setup_authentication():
    """
    Set up Google Earth Engine authentication and project initialization.
    """
    print("🔐 Setting up Google Earth Engine...")
    
    try:
        import ee
        
        # Step 1: Try to authenticate and initialize with project
        try:
            # Initialize with project (this is the correct way)
            ee.Initialize(project=GEE_PROJECT_NAME, opt_url='https://earthengine-highvolume.googleapis.com')
            print("✅ Already authenticated with Google Earth Engine")
            print(f"✅ Project initialized: {GEE_PROJECT_NAME}")
        except Exception as auth_error:
            print(f"🔐 Authentication needed: {auth_error}")
            print("   Attempting to authenticate...")
            
            try:
                # Try to authenticate first
                ee.Authenticate()
                # Then initialize with project
                ee.Initialize(project=GEE_PROJECT_NAME, opt_url='https://earthengine-highvolume.googleapis.com')
                print("✅ Authentication successful!")
                print(f"✅ Project initialized: {GEE_PROJECT_NAME}")
            except Exception as auth_fail:
                print(f"❌ Authentication failed: {auth_fail}")
                print("\n🔧 Manual Authentication Required:")
                print("   1. Open a terminal/command prompt")
                print("   2. Run: earthengine authenticate")
                print("   3. Follow the authentication prompts")
                print("   4. Then run this script again")
                print("\n   Or try running this in a Jupyter notebook for interactive authentication.")
                return False
        
        print("\n✅ Google Earth Engine setup completed successfully!")
        return True
            
    except ImportError:
        print("❌ Earth Engine API not installed")
        print("   Please install it with: pip install earthengine-api")
        return False
    except Exception as e:
        print(f"❌ Authentication setup failed: {e}")
        print("   Try running: earthengine authenticate")
        return False

def validate_inputs():
    """
    Validate all input parameters before processing.
    """
    print("🔍 Validating inputs...")
    
    errors = []
    
    # Check project name
    if not GEE_PROJECT_NAME:
        errors.append("GEE_PROJECT_NAME is not set")
    
    # Check dates
    try:
        datetime.strptime(START_DATE, "%Y-%m-%d")
        datetime.strptime(END_DATE, "%Y-%m-%d")
    except ValueError:
        errors.append("Invalid date format. Use YYYY-MM-DD")
    
    # Check shapefile if using it
    if USE_SHAPEFILE and not os.path.exists(SHAPEFILE_PATH):
        errors.append(f"Shapefile not found: {SHAPEFILE_PATH}")
    
    # Check output directory
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    except Exception as e:
        errors.append(f"Cannot create output directory: {e}")
    
    if errors:
        print("❌ Input validation failed:")
        for error in errors:
            print(f"   - {error}")
        return False
    
    print("✅ Input validation passed")
    return True

def test_cloud_processing():
    """
    Test the actual cloud processing functionality.
    """
    print("=" * 80)
    print("🌨️  Real Cloud Processing Test")
    print("=" * 80)
    
    # Print configuration
    print(f"\n📋 Configuration:")
    print(f"   Project: {GEE_PROJECT_NAME}")
    print(f"   Date Range: {START_DATE} to {END_DATE}")
    print(f"   Output: {OUTPUT_DIR}")
    print(f"   Filename: {OUTPUT_FILENAME}")
    
    if USE_SHAPEFILE:
        print(f"   ROI: Shapefile ({SHAPEFILE_PATH})")
    elif USE_BOUNDING_BOX:
        print(f"   ROI: Bounding Box {BOUNDING_BOX}")
    
    # Validate inputs
    if not validate_inputs():
        return False
    
    # Setup authentication
    if not setup_authentication():
        return False
    
    try:
        # Import the cloud processor
        print("\n📦 Importing cloud processor...")
        
        # Test if we can import the module directly
        try:
            from cloud.processor import process_modis_ndsi_cloud
            print("✅ Cloud processor imported successfully")
        except ImportError as import_error:
            print(f"❌ Import Error: {import_error}")
            print("\n🔧 Trying alternative import method...")
            
            # Try importing the module directly
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "cloud_processor", 
                os.path.join(package_dir, "cloud", "processor.py")
            )
            cloud_processor = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cloud_processor)
            process_modis_ndsi_cloud = cloud_processor.process_modis_ndsi_cloud
            print("✅ Cloud processor imported using alternative method")
        
        # Prepare arguments
        kwargs = {
            'project_name': GEE_PROJECT_NAME,
            'start_date': START_DATE,
            'end_date': END_DATE,
            'output_path': OUTPUT_DIR,
            'file_name': OUTPUT_FILENAME,
            'save_original_data': SAVE_ORIGINAL_DATA
        }
        
        # Add ROI
        if USE_SHAPEFILE:
            kwargs['shapefile_path'] = SHAPEFILE_PATH
        elif USE_BOUNDING_BOX:
            kwargs['bounding_box'] = BOUNDING_BOX
        
        print(f"\n🚀 Starting cloud processing...")
        start_time = datetime.now()
        
        # Process MODIS NDSI data
        result = process_modis_ndsi_cloud(**kwargs)
        
        end_time = datetime.now()
        processing_time = end_time - start_time
        
        print(f"\n✅ Cloud processing completed successfully!")
        print(f"   Processing time: {processing_time}")
        print(f"   Output saved to: {OUTPUT_DIR}")
        
        # Check output files
        expected_files = []
        
        # Always expect the main processed time series file
        expected_files.append(f"{OUTPUT_FILENAME}.zarr")
        
        # Only expect original data files if SAVE_ORIGINAL_DATA is True
        if SAVE_ORIGINAL_DATA:
            expected_files.extend([
                f"{OUTPUT_FILENAME}_MOD_value.zarr",
                f"{OUTPUT_FILENAME}_MOD_class.zarr", 
                f"{OUTPUT_FILENAME}_MYD_value.zarr",
                f"{OUTPUT_FILENAME}_MYD_class.zarr"
            ])
        
        print(f"\n📁 Checking output files...")
        print(f"   SAVE_ORIGINAL_DATA: {SAVE_ORIGINAL_DATA}")
        created_files = []
        for filename in expected_files:
            file_path = os.path.join(OUTPUT_DIR, filename)
            if os.path.exists(file_path):
                print(f"   ✅ {filename}")
                created_files.append(filename)
            else:
                print(f"   ❌ {filename} (not found)")
        
        # Display results summary
        print(f"\n📊 Results Summary:")
        print(f"   Files created: {len(created_files)}/{len(expected_files)}")
        print(f"   Processing time: {processing_time}")
        print(f"   Project used: {GEE_PROJECT_NAME}")
        print(f"   Save original data: {SAVE_ORIGINAL_DATA}")
        
        if result is not None:
            print(f"   Return value: {type(result).__name__}")
        
        return len(created_files) > 0
        
    except ImportError as e:
        print(f"\n❌ Import Error: {e}")
        print("   Please ensure all required packages are installed:")
        print("   pip install earthengine-api geemap xarray numpy pandas geopandas")
        print("\n🔧 Additional troubleshooting:")
        print("   1. Make sure you're running from the correct directory")
        print("   2. Check that all package files exist")
        print("   3. Verify the package structure is correct")
        return False
        
    except Exception as e:
        print(f"\n❌ Error during cloud processing: {e}")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Traceback:")
        traceback.print_exc()
        return False

def analyze_results():
    """
    Analyze the results if files were created.
    """
    print("\n" + "=" * 80)
    print("📊 Results Analysis")
    print("=" * 80)
    
    try:
        # Check if any Zarr files exist
        zarr_files = []
        for filename in os.listdir(OUTPUT_DIR):
            if filename.endswith('.zarr') and os.path.isdir(os.path.join(OUTPUT_DIR, filename)):
                zarr_files.append(filename)
        
        if not zarr_files:
            print("❌ No Zarr files found for analysis")
            return
        
        print(f"Found {len(zarr_files)} Zarr files:")
        for filename in zarr_files:
            print(f"   📁 {filename}")
        
        # Try to load and analyze one file
        if zarr_files:
            sample_file = os.path.join(OUTPUT_DIR, zarr_files[0])
            print(f"\n🔍 Analyzing sample file: {zarr_files[0]}")
            
            try:
                ds = xr.open_zarr(sample_file)
                print(f"   Dataset type: {type(ds)}")
                print(f"   Dimensions: {dict(ds.dims)}")
                print(f"   Variables: {list(ds.data_vars.keys())}")
                print(f"   Coordinates: {list(ds.coords.keys())}")
                
                # Show data info
                if hasattr(ds, 'NDSI') or hasattr(ds, 'NDSI_Snow_Cover'):
                    var_name = 'NDSI' if hasattr(ds, 'NDSI') else 'NDSI_Snow_Cover'
                    data_var = ds[var_name]
                    print(f"   {var_name} shape: {data_var.shape}")
                    print(f"   {var_name} dtype: {data_var.dtype}")
                    
                    # Check for NaN values
                    if hasattr(data_var, 'isnull'):
                        nan_count = data_var.isnull().sum().values
                        total_count = data_var.size
                        nan_percentage = (nan_count / total_count) * 100
                        print(f"   NaN values: {nan_count}/{total_count} ({nan_percentage:.2f}%)")
                
                ds.close()
                
            except Exception as e:
                print(f"   ❌ Could not analyze file: {e}")
        
    except Exception as e:
        print(f"❌ Error during results analysis: {e}")

def main():
    """
    Main execution function.
    """
    print("🌨️  SnowMapPy Real Cloud Processing Test")
    print("=" * 80)
    print("This test will download and process real MODIS NDSI data from Google Earth Engine.")
    print("Make sure you have authenticated with Google Earth Engine before running this test.")
    print("=" * 80)
    
    # Run the test
    success = test_cloud_processing()
    
    # Analyze results if successful
    if success:
        analyze_results()
    
    # Final summary
    print("\n" + "=" * 80)
    print("📋 Test Summary")
    print("=" * 80)
    print(f"   Cloud Processing: {'✅ PASSED' if success else '❌ FAILED'}")
    
    if success:
        print("\n🎉 Real cloud processing test completed successfully!")
        print(f"📁 Check the results in: {OUTPUT_DIR}")
        print("\n📝 Next steps:")
        print("   1. Verify the output files contain the expected data")
        print("   2. Check the data quality and coverage")
        print("   3. Use the processed data for your analysis")
    else:
        print("\n⚠️  Cloud processing test failed!")
        print("   Check the error messages above for troubleshooting.")
        print("\n🔧 Common solutions:")
        print("   1. Ensure Google Earth Engine authentication is set up")
        print("   2. Check your internet connection")
        print("   3. Verify the input parameters are correct")
        print("   4. Make sure all required packages are installed")
    
    print("=" * 80)
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 