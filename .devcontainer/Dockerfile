FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

# Install system dependencies for TimeLocker development (restic, diagrams, build tooling)
ARG RESTIC_VERSION=0.18.1

RUN apt-get update \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libsqlite3-dev \
        graphviz \
        plantuml \
        openjdk-17-jre-headless \
        iputils-ping \
        curl \
        bzip2 \
    && curl -L "https://github.com/restic/restic/releases/download/v${RESTIC_VERSION}/restic_${RESTIC_VERSION}_linux_amd64.bz2" -o /usr/local/bin/restic.bz2 \
    && bunzip2 /usr/local/bin/restic.bz2 \
    && chmod +x /usr/local/bin/restic \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER vscode

# Align container working directory with project expectations
WORKDIR /workspace

# Keep pip tooling current for editable installs
RUN pip install --upgrade pip setuptools wheel
