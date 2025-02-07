# Always use the latest image
# hadolint ignore=DL3007
FROM cgr.dev/chainguard/wolfi-base:latest AS base
ENV PYTHONUNBUFFERED=1

FROM base AS builder
# we want always the latest version of fetched apk packages
# hadolint ignore=DL3018
RUN apk add --no-cache build-base openssl-dev glibc-dev posix-libc-utils libffi-dev \
    python-3.12 python3-dev py3.12-pip && \
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
RUN apk add --no-cache ccache
COPY src/ /src/
WORKDIR /src

RUN python -m venv /venv && \
    /venv/bin/pip install --no-cache-dir -U pip pyinstaller setuptools wheel && \
    /venv/bin/pip install --no-cache-dir --no-warn-script-location -r ./requirements.txt && \
    /venv/bin/pyinstaller --onefile harbor.py

FROM base AS test
USER nonroot
COPY --from=builder /install /usr/local
COPY tests/ /tests/
WORKDIR /tests
RUN python3 -m unittest discover -v -s .

# Always use the latest image
# hadolint ignore=DL3007
FROM cgr.dev/chainguard/wolfi-base:latest
USER nonroot
COPY --from=native-builder /src/dist/harbor /usr/local/harbor
