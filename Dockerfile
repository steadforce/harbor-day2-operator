# syntax=docker/dockerfile:1.17-labs 
FROM cgr.dev/chainguard/wolfi-base:latest@sha256:c1eae10707f1af4f3864f978e609c7c89d4b29edacb30c1eba3745691bc25b27 AS base
ENV PYTHONUNBUFFERED=1
RUN apk update --no-cache && apk upgrade --no-cache
# renovate: datasource=python-version depName=python versioning=python
ARG version=3.13
# hadolint ignore=DL3018
RUN apk add --no-cache python-${version} py${version}-pip
ENV PATH="${PATH}:/home/nonroot/.local/bin"

FROM base AS builder_package
# hadolint ignore=DL3018
RUN apk add --no-cache build-base openssl-dev glibc-dev posix-libc-utils libffi-dev
# hadolint ignore=DL3013,DL3059
RUN pip3 install --no-cache-dir -U pip setuptools wheel pyinstaller

FROM builder_package AS builder
WORKDIR /build
COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir --upgrade -r ./requirements.txt
COPY src/ src/
RUN pyinstaller --onefile --paths src src/harbor.py

FROM base AS package
USER nonroot
WORKDIR /usr/local/bin/
COPY --from=builder /build/dist/harbor ./harbor

FROM package
WORKDIR /
ENV JSON_LOGGING=True
ARG HARBOR_OPERATOR_VERSION=0.0.0-dev
ENV HARBOR_OPERATOR_VERSION=${HARBOR_OPERATOR_VERSION}
ENTRYPOINT ["/usr/local/bin/harbor"]
