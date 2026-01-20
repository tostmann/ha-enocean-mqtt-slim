ARG BUILD_FROM
FROM $BUILD_FROM

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install requirements
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-setuptools \
    py3-wheel \
    gcc \
    musl-dev \
    aiohttp \
    python3-dev

# Copy application files
COPY rootfs /

# Install Python dependencies
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# Set working directory
WORKDIR /app

# Make run script executable
RUN chmod a+x /run.sh

# Run
CMD ["/run.sh"]
