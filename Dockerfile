FROM python:3.12-alpine@sha256:e0e4d3db19333a970e7acfdcb8863efe065be6c3038ef5018694f98162bffec0 AS base
ENV PYTHONUNBUFFERED=1

FROM base AS builder
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

FROM builder AS native-builder
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

FROM base AS test
COPY --from=builder /install /usr/local
COPY tests/ /tests/
WORKDIR /tests
RUN python3 -m unittest discover -v -s .

FROM alpine:3.20@sha256:0a4eaa0eecf5f8c050e5bba433f58c052be7587ee8af3e8b3910ef9ab5fbe9f5
COPY --from=native-builder /install/harbor.bin /usr/local/harbor
