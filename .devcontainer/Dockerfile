FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

# Install system dependencies for restic operations and diagram generation
RUN apt-get update \
    && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y --no-install-recommends \
        restic \
        graphviz \
        plantuml \
        openjdk-17-jre-headless \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
