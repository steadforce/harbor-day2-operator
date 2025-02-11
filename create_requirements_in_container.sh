#!/usr/bin/env bash

set -e

docker build --no-cache --target builder_package -t local-python-builder .
docker run \
    -v ./dev_requirements.txt:/dev_requirements.txt \
    -v ./requirements.txt:/requirements.txt \
    --rm local-python-builder sh -c '\
        pip3 install pip-chill && \
        # Collect requirements (with versions) installed by system or Dockerfile
        pip-chill --no-chill > system_requirements.txt && \
        pip3 install -r dev_requirements.txt && \
        # Ignore requirements (only the exact version) installed by system or Dockerfile
        pip-chill --no-chill | grep -vf system_requirements.txt > requirements.txt'
docker image rm local-python-builder
grep 'extra-index-url\|trusted-host' dev_requirements.txt | \
    cat - requirements.txt > out.txt && mv out.txt requirements.txt
