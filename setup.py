from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="SnowMapPy",
    version="1.0.5",
    author="Haytam Elyoussfi, Hatim BECHRI",
    author_email="haytam.elyoussfi@um6p.ma, hatim.bechri@usms.ac.ma",
    description="A comprehensive Python package for processing MODIS NDSI data from local files and Google Earth Engine",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/haytamelyo/SnowMapPy",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "numpy>=1.20.0",
        "scipy>=1.7.0", 
        "pandas>=1.3.0",
        "xarray>=0.19.0",
        "rasterio>=1.2.0",
        "rioxarray>=0.11.0",
        "geopandas>=0.10.0",
        "pyproj>=3.0.0",
        "shapely>=1.8.0",
        "earthengine-api>=0.1.0",
        "zarr>=2.10.0",
        "tqdm>=4.60.0",
        "joblib>=1.0.0"
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "flake8>=3.8",
            "black>=21.0",
            "matplotlib>=3.5.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: GIS",
        "Topic :: Scientific/Engineering :: Atmospheric Science",
    ],
    keywords="modis, snow, remote sensing, earth engine, gis, hydrology",
    project_urls={
        "Bug Reports": "https://github.com/haytamelyo/SnowMapPy/issues",
        "Source": "https://github.com/haytamelyo/SnowMapPy",
        "Documentation": "https://github.com/haytamelyo/SnowMapPy#readme",
    },
)