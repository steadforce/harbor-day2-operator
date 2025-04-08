# syntax=docker/dockerfile:1.11-labs 
FROM cgr.dev/chainguard/wolfi-base:latest@sha256:de8e5bd83625801da1ff756f648abd4c65fd9da43fcdb30f67ac78ba86170ca8 AS base
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
