FROM continuumio/miniconda3:latest

# Add metadata labels
LABEL maintainer="Haytam Elyoussfi <haytam.elyoussfi@um6p.ma>, Hatim BECHRI <hatim.bechri@usms.ac.ma>"
LABEL description="SnowMapPy - A comprehensive Python package for processing MODIS NDSI data"
LABEL version="1.0.5"
LABEL org.opencontainers.image.source="https://github.com/haytamelyo/SnowMapPy"
LABEL org.opencontainers.image.authors="Haytam Elyoussfi, Hatim BECHRI"

WORKDIR /app

# Install geospatial dependencies via conda in a single layer to reduce size
RUN conda install -c conda-forge \
    python=3.11 \
    gdal \
    rasterio \
    geopandas \
    rioxarray \
    pyproj \
    shapely \
    xarray \
    zarr \
    numpy \
    scipy \
    pandas \
    tqdm \
    joblib \
    netcdf4 \
    h5py \
    geemap \
    && conda clean -afy \
    && pip install --no-cache-dir \
        earthengine-api \
        SnowMapPy==1.0.5 \
    && conda clean --all --yes \
    && pip cache purge

CMD ["/bin/bash"]