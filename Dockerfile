# Always use the latest image
# hadolint ignore=DL3007
FROM cgr.dev/chainguard/wolfi-base:latest AS base
ENV PYTHONUNBUFFERED=1

FROM base AS builder
# we want always the latest version of fetched apk packages
# hadolint ignore=DL3018
RUN apk add --no-cache build-base posix-libc-utils && \
    apk add --no-cache python-3.12 python3-dev py3.12-pip && \
    mkdir /install
WORKDIR /install

FROM builder AS native-builder
# we want always the latest version of fetched apk packages
# hadolint ignore=DL3018
COPY src/ /src/
COPY requirements.txt requirements.txt

# use latest version of pyinstaller
# hadolint ignore=DL3013
RUN pip install --no-cache-dir -U pyinstaller && \
    pip install --no-cache-dir --no-warn-script-location -r ./requirements.txt && \
    pyinstaller --onefile /src/harbor.py && \
    pwd && \
    ls -lha

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
COPY --from=native-builder /install/dist/harbor /usr/local/harbor
