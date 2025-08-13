from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="SnowMapPy",
    version="1.0.1",  # Updated version
    author="Haytam Elyoussfi",
    author_email="haytam.elyoussfi@um6p.ma",
    description="A comprehensive Python package for processing MODIS NDSI data from local files and Google Earth Engine",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Hbechri/SnowMapPy",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: GIS",
        "Topic :: Scientific/Engineering :: Atmospheric Science",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0",
            "flake8>=3.8",
            "black>=21.0",
        ],
    },
    keywords="modis, snow, remote sensing, earth engine, gis, hydrology",
    project_urls={
        "Bug Reports": "https://github.com/Hbechri/SnowMapPy/issues",
        "Source": "https://github.com/Hbechri/SnowMapPy",
        "Documentation": "https://github.com/Hbechri/SnowMapPy#readme",
    },
)
