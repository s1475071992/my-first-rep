FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive
ARG CONTROL_REPO_SHA=unknown
ARG FROZEN_EXECUTABLE_SHA256=unknown

LABEL org.opencontainers.image.title="GCClassic 14.7.1 Paper-1 external reference environment" \
      org.opencontainers.image.description="Validated GCClassic 14.7.1 TransportTracers runtime for frozen seasonal/ regional external holdout production" \
      org.opencontainers.image.revision="$CONTROL_REPO_SHA" \
      org.opencontainers.image.version="14.7.1-paper1-v1" \
      io.torchctm.gcclassic.executable.sha256="$FROZEN_EXECUTABLE_SHA256"

RUN apt-get update -y \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl wget git \
      libnetcdf-dev libnetcdff-dev netcdf-bin \
      python3 python3-pip \
 && rm -rf /var/lib/apt/lists/* \
 && python3 -m pip install --break-system-packages --no-cache-dir pyyaml netCDF4 awscli

COPY .gc14-image-root/ /tmp/gc14-reference/
COPY scripts/ /opt/control/scripts/
COPY config/ /opt/control/config/

RUN test -x /tmp/gc14-reference/rundirs/gc_4x5_merra2_TransportTracers/gcclassic \
 && actual="$(sha256sum /tmp/gc14-reference/rundirs/gc_4x5_merra2_TransportTracers/gcclassic | awk '{print $1}')" \
 && test "$actual" = "$FROZEN_EXECUTABLE_SHA256" \
 && printf '%s  %s\n' "$actual" "/tmp/gc14-reference/rundirs/gc_4x5_merra2_TransportTracers/gcclassic" > /opt/control/gcclassic.image.sha256

ENV GC_USER_REGISTERED=true \
    PYTHONUNBUFFERED=1 \
    GITHUB_WORKSPACE=/opt/control

WORKDIR /work
