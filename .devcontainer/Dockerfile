FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

# Install system dependencies for TimeLocker development (restic, diagrams, build tooling)
RUN apt-get update \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libsqlite3-dev \
        restic \
        graphviz \
        plantuml \
        openjdk-17-jre-headless \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER vscode

# Align container working directory with project expectations
WORKDIR /workspace

# Keep pip tooling current for editable installs
RUN pip install --upgrade pip setuptools wheel
