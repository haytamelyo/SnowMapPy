import ee
import geemap


def initialize_earth_engine(project_name):
    """Initialize Google Earth Engine with project authentication."""
    try:
        ee.Authenticate()
        ee.Initialize(project=project_name, opt_url='https://earthengine-highvolume.googleapis.com')
        return True
    except Exception as e:
        print(f"Failed to initialize Earth Engine: {e}")
        return False