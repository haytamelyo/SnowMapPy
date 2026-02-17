# Google Earth Engine Setup

Detailed guide for configuring Google Earth Engine with SnowMapPy.

---

## Overview

SnowMapPy uses Google Earth Engine (GEE) to access MODIS snow cover data and SRTM elevation data. This eliminates the need to download large datasets locally - data is processed on Google's cloud infrastructure before being streamed to your machine.

---

## Creating a GEE Account

### Step 1: Register for Earth Engine

1. Visit [earthengine.google.com](https://earthengine.google.com/)
2. Click **Get Started**
3. Select your intended use:
    - **Research** - For academic and scientific work
    - **Nonprofit** - For NGOs and nonprofit organizations
    - **Commercial** - For business applications (requires paid license)

!!! success "Free for Research"
    
    Earth Engine is free for research, education, and nonprofit use. Commercial use requires a Google Cloud billing account.

### Step 2: Accept Terms of Service

After registration approval (usually instant), accept the Earth Engine Terms of Service.

---

## Creating a Cloud Project

SnowMapPy requires a Google Cloud project ID, not just a GEE account.

### Step 1: Access Google Cloud Console

1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
2. Sign in with your Google account

### Step 2: Create a Project

1. Click the project dropdown at the top of the page
2. Click **New Project**
3. Enter a project name (e.g., `my-snow-analysis`)
4. Note the **Project ID** - this is what you'll use in SnowMapPy

!!! warning "Project ID vs Project Name"
    
    The **Project ID** is a unique identifier (e.g., `my-snow-analysis-12345`) and cannot be changed. The **Project Name** is just a display label.

### Step 3: Enable Earth Engine API

1. In the Cloud Console, go to **APIs & Services** > **Library**
2. Search for "Earth Engine API"
3. Click **Enable**

---

## Authentication Methods

### Interactive Authentication (Recommended)

For personal machines and development, use interactive browser authentication:

```bash
earthengine authenticate
```

This will:

1. Open a browser window
2. Ask you to sign in to Google
3. Request permission to access Earth Engine
4. Save credentials locally

!!! info "Credentials Location"
    
    Credentials are stored at:
    
    - **Windows**: `%USERPROFILE%\.config\earthengine\credentials`
    - **Linux/macOS**: `~/.config/earthengine/credentials`

### Service Account Authentication

For automated workflows, servers, and production deployments, use a service account:

#### Create a Service Account

1. In Google Cloud Console, go to **IAM & Admin** > **Service Accounts**
2. Click **Create Service Account**
3. Enter a name (e.g., `snowmappy-processor`)
4. Click **Create and Continue**
5. Grant the role: **Service Account User**
6. Click **Done**

#### Generate a Key

1. Click on your new service account
2. Go to the **Keys** tab
3. Click **Add Key** > **Create New Key**
4. Choose **JSON** format
5. Save the downloaded file securely

#### Use in SnowMapPy

```python
import ee
from SnowMapPy.cloud import initialize_gee

# Initialize with service account
credentials = ee.ServiceAccountCredentials(
    email='snowmappy-processor@your-project.iam.gserviceaccount.com',
    key_file='path/to/service-account-key.json'
)
ee.Initialize(credentials, project='your-project-id')

# Now use SnowMapPy normally
from SnowMapPy import process_modis_ndsi_cloud
# ...
```

!!! danger "Protect Your Keys"
    
    Never commit service account keys to version control. Use environment variables or secret management systems in production.

---

## Using with SnowMapPy

### Basic Initialization

SnowMapPy handles initialization automatically when you provide a project name:

```python
from SnowMapPy import process_modis_ndsi_cloud

result, counters = process_modis_ndsi_cloud(
    project_name="your-project-id",  # Your GEE project
    shapefile_path="study_area.shp",
    start_date="2020-01-01",
    end_date="2020-12-31",
    output_path="./output"
)
```

### Manual Initialization

For more control, initialize manually:

```python
from SnowMapPy.cloud import initialize_gee

# Initialize GEE
initialize_gee(project="your-project-id")

# Then use processing functions
from SnowMapPy import process_modis_ndsi_cloud
```

---

## Troubleshooting

### Common Errors

??? failure "EEException: Not signed in"
    
    **Cause**: Authentication credentials are missing or expired.
    
    **Solution**:
    ```bash
    earthengine authenticate
    ```

??? failure "EEException: Earth Engine API has not been enabled"
    
    **Cause**: The Earth Engine API is not enabled for your project.
    
    **Solution**:
    1. Go to [Google Cloud Console](https://console.cloud.google.com/)
    2. Select your project
    3. Go to **APIs & Services** > **Library**
    4. Search for "Earth Engine API"
    5. Click **Enable**

??? failure "EEException: Project not found"
    
    **Cause**: Invalid project ID or insufficient permissions.
    
    **Solution**:
    1. Verify the project ID in Google Cloud Console
    2. Ensure you have access to the project
    3. Check if the project is active (not deleted)

??? failure "Quota exceeded"
    
    **Cause**: You've hit Earth Engine usage limits.
    
    **Solution**:
    - Free accounts have limited compute quotas
    - Process smaller time periods
    - Use smaller study areas
    - Wait for quota reset (typically daily)
    - Consider commercial GEE license for heavy usage

### Verify Your Setup

Run this test to verify everything is configured correctly:

```python
import ee
from SnowMapPy.cloud import initialize_gee

# Initialize
initialize_gee(project="your-project-id")

# Test by requesting a single image
image = ee.Image("MODIS/006/MOD10A1/2020_01_01")
print("MODIS bands:", image.bandNames().getInfo())

# Verify NDSI band exists
print("✓ Google Earth Engine connected successfully!")
```

Expected output:
```
MODIS bands: ['NDSI_Snow_Cover', 'NDSI_Snow_Cover_Basic_QA', ...]
✓ Google Earth Engine connected successfully!
```

---

## Next Steps

Once GEE is configured:

- [Quick Start](quickstart.md) - Run your first analysis
- [User Guide](user-guide/index.md) - Learn advanced features
