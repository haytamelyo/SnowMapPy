from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="SnowMapPy",
    version="1.0.3",  # Updated version
    author="Haytam Elyoussfi",
    author_email="haytam.elyoussfi@um6p.ma",
    description="A comprehensive Python package for processing MODIS NDSI data from local files and Google Earth Engine",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/haytamelyo/SnowMapPy",
    packages=find_packages(),
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
        "Bug Reports": "https://github.com/haytamelyo/SnowMapPy/issues",
        "Source": "https://github.com/haytamelyo/SnowMapPy",
        "Documentation": "https://github.com/haytamelyo/SnowMapPy#readme",
    },
)
