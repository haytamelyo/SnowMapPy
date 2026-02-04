#!/usr/bin/env python3
"""
SnowMapPy v2.0.0 - Interactive Command Line Interface

Process MODIS NDSI data from Google Earth Engine with an interactive,
user-friendly command-line interface.

Usage:
    snowmappy              # Interactive mode (recommended)
    snowmappy --help       # Show help

Authors: Haytam Elyoussfi, Hatim Bechri
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Suppress warnings early
import warnings
warnings.filterwarnings('ignore')

try:
    import questionary
    from questionary import Style
    QUESTIONARY_AVAILABLE = True
except ImportError:
    QUESTIONARY_AVAILABLE = False

from .core.console import (
    suppress_warnings, print_banner, print_section, print_config,
    print_success, print_error, print_info, print_complete, green, red, cyan
)

# Suppress unnecessary warnings
suppress_warnings()

# Custom style for questionary prompts
CUSTOM_STYLE = Style([
    ('qmark', 'fg:cyan bold'),
    ('question', 'bold'),
    ('answer', 'fg:green bold'),
    ('pointer', 'fg:cyan bold'),
    ('highlighted', 'fg:cyan bold'),
    ('selected', 'fg:green'),
    ('separator', 'fg:gray'),
    ('instruction', 'fg:gray'),
    ('text', ''),
    ('disabled', 'fg:gray italic'),
]) if QUESTIONARY_AVAILABLE else None

# Spatial correction method mappings (technical names)
SPATIAL_CORRECTION_METHODS = {
    'elevation_mean': {
        'display': 'Elevation Mean Method (recommended)',
        'description': 'Uses mean elevation of snow pixels to fill gaps above that elevation',
        'value': 'elevation_mean'
    },
    'neighbor_based': {
        'display': 'Neighbor-Based Method',
        'description': 'Checks surrounding pixels above 1000m for snow presence',
        'value': 'neighbor_based'
    },
    'none': {
        'display': 'No Spatial Correction',
        'description': 'Skip spatial snow correction entirely',
        'value': 'none'
    }
}

# Interpolation method descriptions
INTERPOLATION_METHODS = {
    'nearest': {
        'display': 'Nearest (fastest, recommended)',
        'description': 'Uses nearest valid observation in time (backward-first priority)'
    },
    'linear': {
        'display': 'Linear',
        'description': 'Linear interpolation between valid observations'
    },
    'cubic': {
        'display': 'Cubic (smoothest)',
        'description': 'Cubic spline interpolation for smooth transitions'
    }
}


def get_shapefile_name(shapefile_path: str) -> str:
    """Extract shapefile name without extension for default output name."""
    return Path(shapefile_path).stem


def validate_date(date_str: str) -> bool:
    """Validate date format YYYY-MM-DD."""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def validate_shapefile(path: str) -> bool:
    """Validate shapefile exists."""
    return os.path.exists(path) and path.lower().endswith('.shp')


def validate_output_dir(path: str) -> bool:
    """Validate output directory (create if needed)."""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception:
        return False


def run_interactive():
    """Run the interactive CLI."""
    if not QUESTIONARY_AVAILABLE:
        print_error("Interactive mode requires 'questionary' package.")
        print_info("Install it with: pip install questionary")
        print_info("Or use command-line arguments: snowmappy --help")
        return 1
    
    print_banner()
    print()
    print_info("Welcome to SnowMapPy Interactive Mode!")
    print_info("Press Ctrl+C at any time to cancel.")
    print()
    
    try:
        # =====================================================================
        # Google Earth Engine Project
        # =====================================================================
        print_section("Google Earth Engine Configuration")
        
        project_name = questionary.text(
            "Enter your GEE project name:",
            instruction="(e.g., ee-myproject)",
            style=CUSTOM_STYLE,
            validate=lambda x: len(x) > 0 or "Project name is required"
        ).ask()
        
        if project_name is None:
            return 1
        
        # =====================================================================
        # Study Area (Shapefile)
        # =====================================================================
        print()
        print_section("Study Area Configuration")
        
        shapefile_path = questionary.path(
            "Select your shapefile (.shp):",
            only_directories=False,
            file_filter=lambda x: x.endswith('.shp') or os.path.isdir(x),
            style=CUSTOM_STYLE,
            validate=lambda x: validate_shapefile(x) or "Please select a valid .shp file"
        ).ask()
        
        if shapefile_path is None:
            return 1
        
        # Default output name from shapefile
        default_name = f"{get_shapefile_name(shapefile_path)}_NDSI"
        
        # =====================================================================
        # Date Range
        # =====================================================================
        print()
        print_section("Date Range Configuration")
        
        start_date = questionary.text(
            "Enter start date:",
            instruction="(YYYY-MM-DD format)",
            default="2020-01-01",
            style=CUSTOM_STYLE,
            validate=lambda x: validate_date(x) or "Invalid date format. Use YYYY-MM-DD"
        ).ask()
        
        if start_date is None:
            return 1
        
        end_date = questionary.text(
            "Enter end date:",
            instruction="(YYYY-MM-DD format)",
            default="2020-12-31",
            style=CUSTOM_STYLE,
            validate=lambda x: validate_date(x) or "Invalid date format. Use YYYY-MM-DD"
        ).ask()
        
        if end_date is None:
            return 1
        
        # Validate date range
        if datetime.strptime(start_date, '%Y-%m-%d') >= datetime.strptime(end_date, '%Y-%m-%d'):
            print_error("Start date must be before end date!")
            return 1
        
        # =====================================================================
        # Output Configuration
        # =====================================================================
        print()
        print_section("Output Configuration")
        
        output_path = questionary.path(
            "Select output directory:",
            only_directories=True,
            style=CUSTOM_STYLE,
            default="./"
        ).ask()
        
        if output_path is None:
            return 1
        
        output_name = questionary.text(
            "Enter output filename:",
            instruction="(without extension)",
            default=default_name,
            style=CUSTOM_STYLE,
            validate=lambda x: len(x) > 0 or "Filename is required"
        ).ask()
        
        if output_name is None:
            return 1
        
        # =====================================================================
        # Processing Options
        # =====================================================================
        print()
        print_section("Processing Options")
        
        # Interpolation method
        interp_choices = [
            questionary.Choice(
                title=f"{v['display']} - {v['description']}",
                value=k
            )
            for k, v in INTERPOLATION_METHODS.items()
        ]
        
        interpolation = questionary.select(
            "Select interpolation method:",
            choices=interp_choices,
            default="nearest",
            style=CUSTOM_STYLE,
            instruction="(use arrow keys)"
        ).ask()
        
        if interpolation is None:
            return 1
        
        # Spatial correction method
        spatial_choices = [
            questionary.Choice(
                title=f"{v['display']} - {v['description']}",
                value=k
            )
            for k, v in SPATIAL_CORRECTION_METHODS.items()
        ]
        
        spatial_correction = questionary.select(
            "Select spatial correction method:",
            choices=spatial_choices,
            default="elevation_mean",
            style=CUSTOM_STYLE,
            instruction="(use arrow keys)"
        ).ask()
        
        if spatial_correction is None:
            return 1
        
        # =====================================================================
        # Advanced Options
        # =====================================================================
        print()
        show_advanced = questionary.confirm(
            "Show advanced options?",
            default=False,
            style=CUSTOM_STYLE
        ).ask()
        
        save_original = False
        save_counters = False
        crs = "EPSG:4326"
        
        if show_advanced:
            print()
            print_section("Advanced Options")
            
            save_original = questionary.confirm(
                "Save original Terra/Aqua data?",
                default=False,
                style=CUSTOM_STYLE
            ).ask()
            
            save_counters = questionary.confirm(
                "Save pixel counters to CSV?",
                default=False,
                style=CUSTOM_STYLE
            ).ask()
            
            change_crs = questionary.confirm(
                "Change coordinate reference system?",
                default=False,
                style=CUSTOM_STYLE
            ).ask()
            
            if change_crs:
                crs = questionary.text(
                    "Enter CRS:",
                    default="EPSG:4326",
                    style=CUSTOM_STYLE
                ).ask()
        
        # =====================================================================
        # Confirmation
        # =====================================================================
        print()
        print_section("Configuration Summary")
        print_config("GEE Project", project_name)
        print_config("Shapefile", shapefile_path)
        print_config("Date Range", f"{start_date} to {end_date}")
        print_config("Output", f"{output_path}/{output_name}.zarr")
        print_config("Interpolation", interpolation)
        print_config("Spatial Correction", spatial_correction)
        print_config("Save Original Data", "Yes" if save_original else "No")
        print_config("Save Pixel Counters", "Yes" if save_counters else "No")
        print()
        
        confirm = questionary.confirm(
            "Proceed with processing?",
            default=True,
            style=CUSTOM_STYLE
        ).ask()
        
        if not confirm:
            print_info("Processing cancelled.")
            return 0
        
        # =====================================================================
        # Run Processing
        # =====================================================================
        print()
        print_section("Starting Processing")
        start_time = time.time()
        
        # Import processor
        from .cloud.processor import process_modis_ndsi_cloud
        
        # Map technical names to internal names
        spatial_map = {
            'elevation_mean': 'old',
            'neighbor_based': 'new',
            'none': 'none'
        }
        
        # Run processing
        result, counters = process_modis_ndsi_cloud(
            project_name=project_name,
            shapefile_path=shapefile_path,
            start_date=start_date,
            end_date=end_date,
            output_path=output_path,
            file_name=output_name,
            crs=crs,
            save_original_data=save_original,
            interpolation_method=interpolation,
            spatial_correction_method=spatial_map[spatial_correction],
            verbose=True,
            save_pixel_counters=save_counters
        )
        
        elapsed = time.time() - start_time
        
        print()
        print_complete(f"Processing completed in {elapsed:.1f} seconds!")
        print_success(f"Output saved to: {output_path}/{output_name}.zarr")
        
        return 0
        
    except KeyboardInterrupt:
        print()
        print_info("Processing cancelled by user.")
        return 1
    except Exception as e:
        print()
        print_error(f"Error: {e}")
        return 1


def run_cli():
    """Main entry point for the CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="SnowMapPy v2.0.0 - High-Performance MODIS NDSI Processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Interactive Mode (recommended):
  snowmappy                    Launch interactive wizard

Command-Line Mode:
  snowmappy -p PROJECT -s SHAPEFILE --start DATE --end DATE -o OUTPUT

Examples:
  snowmappy -p ee-myproject -s ./roi.shp --start 2020-01-01 --end 2020-12-31 -o ./output
        """
    )
    
    # Optional: command-line arguments for non-interactive use
    parser.add_argument('-p', '--project', type=str, help='GEE project name')
    parser.add_argument('-s', '--shapefile', type=str, help='Path to shapefile')
    parser.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('-o', '--output', type=str, help='Output directory')
    parser.add_argument('-n', '--name', type=str, help='Output filename (default: shapefile_NDSI)')
    parser.add_argument('-i', '--interpolation', type=str, 
                        choices=['nearest', 'linear', 'cubic'], default='nearest',
                        help='Interpolation method (default: nearest)')
    parser.add_argument('--spatial-correction', type=str,
                        choices=['elevation_mean', 'neighbor_based', 'none'],
                        default='elevation_mean',
                        help='Spatial correction method (default: elevation_mean)')
    parser.add_argument('--crs', type=str, default='EPSG:4326', help='CRS (default: EPSG:4326)')
    parser.add_argument('--save-original', action='store_true', help='Save original data')
    parser.add_argument('--save-counters', action='store_true', help='Save pixel counters CSV')
    parser.add_argument('--version', action='version', version='SnowMapPy v2.0.0')
    
    args = parser.parse_args()
    
    # If no arguments provided, run interactive mode
    if len(sys.argv) == 1:
        return run_interactive()
    
    # Otherwise, validate required arguments for command-line mode
    required = ['project', 'shapefile', 'start', 'end', 'output']
    missing = [arg for arg in required if getattr(args, arg) is None]
    
    if missing:
        print_error(f"Missing required arguments: {', '.join(missing)}")
        print_info("Run 'snowmappy' without arguments for interactive mode")
        print_info("Or use 'snowmappy --help' for usage information")
        return 1
    
    # Validate inputs
    if not os.path.exists(args.shapefile):
        print_error(f"Shapefile not found: {args.shapefile}")
        return 1
    
    if not validate_date(args.start) or not validate_date(args.end):
        print_error("Invalid date format. Use YYYY-MM-DD")
        return 1
    
    # Default filename from shapefile
    output_name = args.name or f"{get_shapefile_name(args.shapefile)}_NDSI"
    
    # Map spatial correction names
    spatial_map = {
        'elevation_mean': 'old',
        'neighbor_based': 'new', 
        'none': 'none'
    }
    
    print_banner()
    
    try:
        from .cloud.processor import process_modis_ndsi_cloud
        
        result, counters = process_modis_ndsi_cloud(
            project_name=args.project,
            shapefile_path=args.shapefile,
            start_date=args.start,
            end_date=args.end,
            output_path=args.output,
            file_name=output_name,
            crs=args.crs,
            save_original_data=args.save_original,
            interpolation_method=args.interpolation,
            spatial_correction_method=spatial_map[args.spatial_correction],
            verbose=True,
            save_pixel_counters=args.save_counters
        )
        
        print_complete("Processing completed successfully!")
        return 0
        
    except Exception as e:
        print_error(f"Processing failed: {e}")
        return 1


def main():
    """Entry point for the snowmappy command."""
    sys.exit(run_cli())


if __name__ == "__main__":
    main()
