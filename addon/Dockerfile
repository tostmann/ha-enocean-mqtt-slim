ARG BUILD_FROM
FROM $BUILD_FROM

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install build tools (needed for pip compilation)
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-setuptools \
    py3-wheel \
    gcc \
    musl-dev \
    python3-dev

# Copy application files
COPY rootfs /

# --- FIX: Install aiohttp via PIP explicitly ---
# Das stellt sicher, dass es in genau der Python-Umgebung landet, die auch ausgeführt wird.
RUN pip3 install --no-cache-dir aiohttp

# Install other dependencies from requirements.txt
# (Falls requirements.txt leer ist oder fehlt, stürzt dieser Befehl ggf. ab.
#  Wenn die Datei existiert, ist es okay.)
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# Set working directory
WORKDIR /app

# Make run script executable
RUN chmod a+x /run.sh

# Run
CMD ["/run.sh"]
