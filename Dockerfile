# syntax=docker/dockerfile:1.21-labs 

# uv for the build host. A plain `COPY --from=<image>` would take the target platform's
# binary, which the build host cannot run without emulation.
FROM --platform=$BUILDPLATFORM ghcr.io/astral-sh/uv:0.13.4@sha256:9f130421e930bfbdc563c00740466603f8723158e90297d07957c2294640262b AS uv

# Runs on the build host for every target platform: uv downloads the target's wheels
# directly, so multi-arch builds need no emulation. Keep the Python minor version in
# sync with the runtime image and with .python-version.
FROM --platform=$BUILDPLATFORM python:3.13-slim-trixie@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90 AS build
COPY --from=uv /uv /usr/local/bin/uv

ARG TARGETARCH
WORKDIR /src
COPY pyproject.toml uv.lock ./
# Every dependency, also the transitive ones, comes from uv.lock as a hash-pinned wheel: --require-hashes
# refuses anything else and --only-binary refuses a source build (no compiler in this stage or in the image).
RUN case "$TARGETARCH" in \
      amd64) platform=x86_64-manylinux_2_28 ;; \
      arm64) platform=aarch64-manylinux_2_28 ;; \
      *) echo "unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac \
 && uv export --frozen --no-dev --no-emit-project --output-file requirements.txt \
 && uv pip install --target /app --no-deps --require-hashes --only-binary :all: \
      --python-version 3.13 --python-platform "$platform" -r requirements.txt

COPY src/harbor_day2_operator /app/harbor_day2_operator
RUN python -m compileall -q --invalidation-mode unchecked-hash /app

# No shell, no package manager: only the Python interpreter, its libraries and the program.
FROM gcr.io/distroless/python3-debian13:nonroot@sha256:c3ed2b61f3c4e410685565ceb3c818197b552832521b39d53eca5d2d9d0dc1e1
COPY --from=build /app /app
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1 JSON_LOGGING=True
ARG HARBOR_OPERATOR_VERSION=0.0.0-dev
ENV HARBOR_OPERATOR_VERSION=${HARBOR_OPERATOR_VERSION}
ENTRYPOINT ["python3", "-m", "harbor_day2_operator.harbor"]
