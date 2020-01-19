FROM python:3.10-slim

# Prevent writing .pyc files on the import of source modules
# and set unbuffered mode to ensure logging outputs
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Copy repo contents
COPY setup.py setup.cfg LICENSE MANIFEST.in README.md .docker/run.sh ./
COPY optimade ./optimade
COPY providers/src/links/v1/providers.json ./optimade/server/data/
<<<<<<< HEAD
RUN apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -U pip setuptools wheel flit \
    && pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org .[server]
=======
RUN pip install -e .[server]

# Use MaterialsCloud data
COPY mcloud ./mcloud
ENV OPTIMADE_INDEX_LINKS_PATH /app/mcloud/index_links.json

ARG PORT=5000
EXPOSE ${PORT}

COPY .docker/run.sh ./
>>>>>>> Configure for use with Materials Cloud

# Setup server configuration
ARG CONFIG_FILE=optimade_config.json
<<<<<<< HEAD
COPY ${CONFIG_FILE} ./optimade_config.json
ENV OPTIMADE_CONFIG_FILE=/app/optimade_config.json
=======
ENV OPTIMADE_CONFIG_FILE /app/${CONFIG_FILE}
>>>>>>> Configure for use with Materials Cloud

# Run app
EXPOSE 5000
ENTRYPOINT [ "/app/run.sh" ]
