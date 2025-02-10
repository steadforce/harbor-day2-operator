# syntax=docker/dockerfile:1.11-labs 
FROM cgr.dev/chainguard/wolfi-base:latest@sha256:1ec3327af43d7af231ffe475aff88d49dbb5e09af9f28610e6afbd2cb096e751 AS base
ENV PYTHONUNBUFFERED=1
RUN apk update --no-cache && apk upgrade --no-cache
# renovate: datasource=python-version depName=python versioning=python
ARG version=3.13
RUN apk add python-${version} py${version}-pip
ENV PATH="${PATH}:/home/nonroot/.local/bin"

FROM base AS builder_package
RUN apk add --no-cache build-base openssl-dev glibc-dev posix-libc-utils libffi-dev
RUN pip3 install --no-cache-dir -U pip setuptools wheel pyinstaller

FROM builder_package AS builder
WORKDIR /build
COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir --upgrade -r ./requirements.txt
COPY src/ src/
RUN pyinstaller --onefile src/harbor.py

FROM base AS package
USER nonroot
WORKDIR /app/
COPY --from=builder /build/dist/harbor /app/harbor

FROM package
WORKDIR /
ENV JSON_LOGGING=True
ENTRYPOINT ["/app/harbor"]
