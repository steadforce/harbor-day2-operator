# Stick to Python 3.11 until Nuitka supports Python 3.12
FROM python:3.11-alpine@sha256:d1975f2182c9962f5daa1ad935eb092e3e32dce11d8105cb3584a31afc7b451b as base
ENV PYTHONUNBUFFERED 1

FROM base as builder
# we want always the latest version of fetched apk packages
# hadolint ignore=DL3018
RUN apk add --no-cache build-base libressl-dev musl-dev libffi-dev && \
    mkdir /install
WORKDIR /install
COPY requirements.txt requirements.txt
# we want always the latest version of fetched pip packages
# hadolint ignore=DL3013
RUN pip3 install --no-cache-dir -U pip setuptools wheel && \
    pip3 install --no-cache-dir --prefix=/install --no-warn-script-location -r ./requirements.txt

FROM builder as native-builder
# we want always the latest version of fetched apk packages
# hadolint ignore=DL3018
RUN apk add --no-cache ccache patchelf
COPY src/ /src/
RUN python -m venv /venv && \
    /venv/bin/pip install --no-cache-dir -U pip nuitka setuptools wheel && \
    /venv/bin/pip install --no-cache-dir --no-warn-script-location -r ./requirements.txt && \
    /venv/bin/python -m nuitka --onefile /src/harbor.py && \
    pwd && \
    ls -lha

FROM base as test
COPY --from=builder /install /usr/local
COPY tests/ /tests/
WORKDIR /tests
RUN python3 -m unittest discover -v -s .

FROM alpine:3.19@sha256:95c16745f100f44cf9a0939fd3f357905f845f8b6fa7d0cde0e88c9764060185
COPY --from=native-builder /install/harbor.bin /usr/local/harbor
