"""
Console Utilities
=================

Terminal output formatting with colors and warning suppression.

Authors: Haytam Elyoussfi, Hatim Bechri
Version: 2.0.0
"""

import sys
import os
import warnings


# =============================================================================
# PROJ FIX - Must be done BEFORE any GDAL/rasterio imports
# =============================================================================

def fix_proj_path():
    """
    Fix PROJ database path conflicts.
    
    This is needed when PostgreSQL/PostGIS or other software installs
    a conflicting PROJ version. We force PROJ to use the Python 
    environment's proj.db instead.
    """
    # Find the correct proj.db from the Python environment
    try:
        import pyproj
        proj_dir = pyproj.datadir.get_data_dir()
        if proj_dir and os.path.exists(os.path.join(proj_dir, 'proj.db')):
            os.environ['PROJ_LIB'] = proj_dir
            os.environ['PROJ_DATA'] = proj_dir
            return True
    except ImportError:
        pass
    
    # Fallback: try to find proj in the virtual environment
    if hasattr(sys, 'prefix'):
        possible_paths = [
            os.path.join(sys.prefix, 'Library', 'share', 'proj'),  # Windows conda/venv
            os.path.join(sys.prefix, 'share', 'proj'),  # Linux/Mac
            os.path.join(sys.prefix, 'Lib', 'site-packages', 'pyproj', 'proj_dir', 'share', 'proj'),
        ]
        for path in possible_paths:
            if os.path.exists(os.path.join(path, 'proj.db')):
                os.environ['PROJ_LIB'] = path
                os.environ['PROJ_DATA'] = path
                return True
    
    return False


# Apply PROJ fix immediately
fix_proj_path()


# =============================================================================
# WARNING SUPPRESSION
# =============================================================================

def suppress_warnings():
    """
    Suppress non-critical warnings to keep terminal output clean.
    
    Filters out:
        - Zarr numcodecs warnings about v3 specification
        - PROJ database warnings
        - xarray deprecation warnings
        - Earth Engine system warnings
    """
    # Suppress all warnings by default
    warnings.filterwarnings('ignore')
    
    # Specifically suppress zarr/numcodecs warnings
    warnings.filterwarnings('ignore', category=UserWarning, module='zarr')
    warnings.filterwarnings('ignore', category=UserWarning, module='numcodecs')
    warnings.filterwarnings('ignore', message='.*Numcodecs codecs are not in the Zarr.*')
    warnings.filterwarnings('ignore', message='.*Consolidated metadata.*')
    
    # Suppress xee warnings
    warnings.filterwarnings('ignore', module='xee')
    warnings.filterwarnings('ignore', message=".*system:time_start.*")
    
    # Suppress deprecation warnings
    warnings.filterwarnings('ignore', category=DeprecationWarning)
    warnings.filterwarnings('ignore', category=FutureWarning)
    
    # Suppress GDAL/PROJ errors by redirecting stderr temporarily for GDAL
    os.environ['CPL_LOG'] = 'NUL' if os.name == 'nt' else '/dev/null'


# Auto-suppress warnings when module is imported
suppress_warnings()


# =============================================================================
# TERMINAL COLORS
# =============================================================================

class Colors:
    """ANSI color codes for terminal output."""
    
    # Check if colors are supported
    _enabled = sys.stdout.isatty() and os.name != 'nt' or \
               os.environ.get('TERM_PROGRAM') == 'vscode' or \
               os.environ.get('WT_SESSION') or \
               'ANSICON' in os.environ
    
    # Try to enable colors on Windows
    if os.name == 'nt':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            _enabled = True
        except Exception:
            pass
    
    # Color codes
    RESET = '\033[0m' if _enabled else ''
    BOLD = '\033[1m' if _enabled else ''
    
    # Standard colors
    WHITE = '\033[97m' if _enabled else ''
    RED = '\033[91m' if _enabled else ''
    GREEN = '\033[92m' if _enabled else ''
    BLUE = '\033[94m' if _enabled else ''
    CYAN = '\033[96m' if _enabled else ''
    YELLOW = '\033[93m' if _enabled else ''
    
    # Dim/subtle
    DIM = '\033[2m' if _enabled else ''


def _c(text, color):
    """Apply color to text."""
    return f"{color}{text}{Colors.RESET}"


def white(text):
    """White text."""
    return _c(text, Colors.WHITE)


def blue(text):
    """Blue text for titles."""
    return _c(text, Colors.BLUE)


def green(text):
    """Green text for success."""
    return _c(text, Colors.GREEN)


def red(text):
    """Red text for errors."""
    return _c(text, Colors.RED)


def cyan(text):
    """Cyan text for info."""
    return _c(text, Colors.CYAN)


def yellow(text):
    """Yellow text for warnings."""
    return _c(text, Colors.YELLOW)


def bold(text):
    """Bold text."""
    return _c(text, Colors.BOLD)


def dim(text):
    """Dimmed text."""
    return _c(text, Colors.DIM)


# =============================================================================
# FORMATTED OUTPUT
# =============================================================================

def print_header(title, char='=', width=60):
    """Print a formatted header."""
    line = char * width
    print(f"\n{blue(line)}")
    print(f"  {bold(white(title))}")
    print(f"{blue(line)}\n")


def print_section(title, char='-', width=40):
    """Print a section header."""
    line = char * width
    print(f"\n{blue(title)}")
    print(f"{dim(line)}")


def print_success(message):
    """Print a success message."""
    print(f"{green('✓')} {message}")


def print_error(message):
    """Print an error message."""
    print(f"{red('✗')} {red(message)}")


def print_warning(message):
    """Print a warning message."""
    print(f"{yellow('⚠')} {yellow(message)}")


def print_info(message):
    """Print an info message."""
    print(f"{cyan('→')} {message}")


def print_config(label, value):
    """Print a configuration key-value pair."""
    print(f"  {white(label + ':')} {dim(str(value))}")


def print_banner(title=None):
    """Print the SnowMapPy ASCII art banner."""
    try:
        import pyfiglet
        ascii_art = pyfiglet.figlet_format('SnowMapPy', font='standard')
        print()
        # Print ASCII art in cyan color
        for line in ascii_art.split('\n'):
            if line.strip():  # Only print non-empty lines
                print(cyan(line))
        print()
        print(f"           {dim('SnowMapPy v2.0.0')}  {dim('|')}  {dim('MODIS NDSI Processor')}")
        print()
    except ImportError:
        # Fallback if pyfiglet is not available
        print()
        print(cyan(bold("  SnowMapPy v2.0.0")))
        print(dim("  MODIS NDSI Processor"))
        print()


def print_complete(message=None, elapsed_seconds=None):
    """Print completion message."""
    print()
    print(green("=" * 60))
    if message:
        print(f"  {bold(green(message))}")
    else:
        print(f"  {bold(green('Processing Complete!'))}")
    print(green("=" * 60))
    if elapsed_seconds is not None:
        minutes = elapsed_seconds / 60
        print()
        print(f"  {white('Total time:')} {green(f'{elapsed_seconds:.1f}s')} ({minutes:.1f} minutes)")
    print()
