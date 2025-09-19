FROM python:3.12-slim

# Metadata
LABEL maintainer="Haytam Elyoussfi <haytam.elyoussfi@um6p.ma>" \
      org.opencontainers.image.title="SnowMapPy" \
      org.opencontainers.image.description="A comprehensive Python package for processing MODIS NDSI data from local files and Google Earth Engine" \
      org.opencontainers.image.url="https://github.com/haytamelyo/SnowMapPy" \
      org.opencontainers.image.source="https://github.com/haytamelyo/SnowMapPy" \
      org.opencontainers.image.version="1.0.3"

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgomp1 \
        build-essential \
        gcc && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Upgrade pip and install SnowMapPy
RUN pip install --upgrade pip && \
    pip install SnowMapPy==1.0.3

# Create non-root user
RUN useradd -m -u 1000 snowmappy

# Set working directory
WORKDIR /workspace

# Change ownership of the workspace to the non-root user
RUN chown -R snowmappy:snowmappy /workspace

# Switch to non-root user
USER snowmappy

# Create volume for data
VOLUME ["/workspace"]

# Default command to verify installation
CMD ["python", "-c", "import SnowMapPy; print(f'✅ SnowMapPy {SnowMapPy.__version__} is ready!'); print('📖 Documentation: https://github.com/haytamelyo/SnowMapPy'); print('🚀 Try: python -c \"import SnowMapPy; help(SnowMapPy)\"')"]