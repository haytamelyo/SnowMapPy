from setuptools import setup, find_packages

setup(
    name="SnowMapPy",
    version="0.1",
    author='Haytam Elyoussfi',
    author_email='haytam.elyoussfi@um6p.ma',
    description='Description du package',
    packages=find_packages(),
    install_requires=[
        "os",
        "sys",
        "tqdm",
        "zarr",
        "json",
        "numpy",
        "scipy",
        "xarray",
        "joblib",
        "pandas",
        "affine",
        "datetime",
        "rasterio",
        "geopandas",
        "numcodecs",
    ],
)
