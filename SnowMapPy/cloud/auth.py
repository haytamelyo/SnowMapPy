"""
Google Earth Engine Authentication
===================================

Handle GEE authentication and session initialization with proper
error handling and re-authentication support.

Authors: Haytam Elyoussfi, Hatim Bechri
Version: 2.0.0
"""

import ee


def initialize_earth_engine(project_name, force_auth=False):
    """
    Initialize Google Earth Engine with project authentication.
    
    Handles three scenarios:
        1. Already authenticated with correct project - use existing session
        2. Authenticated but different project - re-initialize
        3. Not authenticated - trigger browser authentication flow
    
    Args:
        project_name: GEE project ID (e.g., 'ee-myproject')
        force_auth: Force re-authentication even if already initialized
    
    Returns:
        True if initialization successful, False otherwise
    """
    from ..core.console import print_success, print_info, print_error
    
    # Check if already initialized
    try:
        if not force_auth:
            # Try to use existing credentials
            ee.Initialize(
                project=project_name,
                opt_url='https://earthengine-highvolume.googleapis.com'
            )
            print_success(f"Earth Engine initialized with project: {project_name}")
            return True
    except ee.EEException:
        # Not initialized or wrong project, continue to authentication
        pass
    except Exception:
        pass
    
    # Need to authenticate
    print_info("Authenticating with Google Earth Engine...")
    print_info("A browser window will open for authentication.")
    print()
    
    try:
        # Use auth_mode='browser' to open browser and wait for code input
        ee.Authenticate(auth_mode='browser')
        
        # Initialize after authentication
        ee.Initialize(
            project=project_name,
            opt_url='https://earthengine-highvolume.googleapis.com'
        )
        
        print_success(f"Earth Engine authenticated and initialized with project: {project_name}")
        return True
        
    except ee.EEException as e:
        error_msg = str(e)
        
        if "not registered" in error_msg.lower() or "not found" in error_msg.lower():
            print_error(f"Project '{project_name}' not found or not registered for Earth Engine.")
            print_error("Please verify your project ID at: https://console.cloud.google.com/")
            print_error("Make sure Earth Engine API is enabled for your project.")
        elif "quota" in error_msg.lower():
            print_error("Earth Engine quota exceeded. Please try again later.")
        elif "permission" in error_msg.lower():
            print_error(f"No permission to access project '{project_name}'.")
            print_error("Make sure you have the correct permissions.")
        else:
            print_error(f"Earth Engine error: {error_msg}")
        
        return False
        
    except Exception as e:
        print_error(f"Failed to initialize Earth Engine: {e}")
        return False


def check_earth_engine_auth():
    """
    Check if Earth Engine credentials exist.
    
    Returns:
        True if credentials file exists, False otherwise
    """
    import os
    
    # Default credentials location
    cred_paths = [
        os.path.expanduser('~/.config/earthengine/credentials'),
        os.path.expanduser('~/.config/earthengine/credentials.json'),
    ]
    
    # Windows paths
    if os.name == 'nt':
        appdata = os.environ.get('APPDATA', '')
        cred_paths.extend([
            os.path.join(appdata, 'earthengine', 'credentials'),
            os.path.join(appdata, 'earthengine', 'credentials.json'),
        ])
    
    return any(os.path.exists(p) for p in cred_paths)
