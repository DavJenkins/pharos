FROM python:3.13-slim-trixie
ARG SOURCE_REVISION=development
LABEL org.opencontainers.image.title="Pharos Data Ark" \
      org.opencontainers.image.source="https://github.com/DavJenkins/pharos" \
      org.opencontainers.image.revision=$SOURCE_REVISION
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 DATAARK_CONTAINER=1 \
    DATAARK_REVISION=$SOURCE_REVISION PATH="/opt/dataark/venv/bin:$PATH"
RUN apt-get update && apt-get install -y --no-install-recommends \
      kiwix-tools tini procps iproute2 libmagic1 poppler-utils \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 admin && useradd --uid 1000 --gid 1000 --create-home admin
WORKDIR /opt/dataark
COPY requirements.txt .
RUN python -m venv venv && venv/bin/pip install --no-cache-dir -r requirements.txt
COPY --chown=1000:1000 . .
RUN mkdir -p /usr/share/dataark /config /var/lib/dataark /etc/dataark /mnt/storage /var/www/html \
    && cp -a config/library /usr/share/dataark/library \
    && cp -a config/content /usr/share/dataark/content \
    && rm -rf config/library config/content \
    && ln -s /config/library config/library && ln -s /config/content config/content \
    && mkdir -p /var/lib/dataark/ark /var/lib/dataark/logs /var/lib/dataark/cache \
    && ln -s /var/lib/dataark/cache .cache \
    && ln -s /var/lib/dataark/ark /var/lib/ark \
    && ln -s /var/lib/dataark/logs /var/log/dataark \
    && chown 1000:1000 /opt/dataark \
    && chown -R 1000:1000 /config /var/lib/dataark /etc/dataark /var/www/html \
    && venv/bin/python -c 'from deploy.container.runtime import write_image_metadata; write_image_metadata()'
USER 1000:1000
EXPOSE 8088
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s \
 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8088/api/container/health',timeout=3)"
ENTRYPOINT ["/usr/bin/tini","--","python","-m","deploy.container.runtime"]
