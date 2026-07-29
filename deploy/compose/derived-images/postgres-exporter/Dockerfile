# syntax=docker/dockerfile:1.19.0@sha256:b6afd42430b15f2d2a4c5a02b919e98a525b785b1aaff16747d2f623364e39b6

ARG GO_IMAGE="golang:1.26.5-alpine3.24@sha256:0178a641fbb4858c5f1b48e34bdaabe0350a330a1b1149aabd498d0699ff5fb2"
ARG UPSTREAM_IMAGE="prometheuscommunity/postgres-exporter:v0.20.1@sha256:ac5ec343104fae0e2d84a27bb8d69b38430a11910c5382cad85d478d2bab713e"

FROM ${GO_IMAGE} AS build

ARG SOURCE_DATE_EPOCH
ARG SOURCE_ARCHIVE="postgres-exporter-867fbca.tar.gz"
ARG SOURCE_SHA256="68a1bbc1a83ec17996d7d49bbad1457bb4b248e8071ccd497db48e8346564501"
ARG SOURCE_DIRECTORY="postgres_exporter-867fbcac31cd18c143e244190ea9168cca069827"
ARG X_TEXT_ARCHIVE="x-text-0.39.0.tar.gz"
ARG X_TEXT_SHA256="c2e68286e1061496dcbb794cec0e40c20c744885b495ff6c7d40f3459699c6c0"

COPY ${SOURCE_ARCHIVE} /tmp/source.tar.gz
COPY ${X_TEXT_ARCHIVE} /tmp/x-text.tar.gz
RUN echo "${SOURCE_SHA256}  /tmp/source.tar.gz" | sha256sum -c - \
    && echo "${X_TEXT_SHA256}  /tmp/x-text.tar.gz" | sha256sum -c - \
    && mkdir /src && tar -xzf /tmp/source.tar.gz -C /src \
    && mkdir -p /src/x-text && tar -xzf /tmp/x-text.tar.gz -C /src/x-text --strip-components=1
WORKDIR /src/${SOURCE_DIRECTORY}

# go.sum locks fetched module content. Compilation itself has no network access.
RUN go mod edit -require=golang.org/x/text@v0.39.0 \
    && go mod edit -replace=golang.org/x/text=/src/x-text \
    && grep -F 'golang.org/x/text v0.39.0' go.mod \
    && grep -F 'replace golang.org/x/text => /src/x-text' go.mod \
    && go mod download
RUN --network=none CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -trimpath \
    -ldflags="-s -w -X github.com/prometheus/common/version.Version=0.20.1 -X github.com/prometheus/common/version.Revision=867fbcac31cd18c143e244190ea9168cca069827" \
    -o /out/postgres_exporter ./cmd/postgres_exporter
RUN touch -d "@${SOURCE_DATE_EPOCH}" /out/postgres_exporter

FROM ${UPSTREAM_IMAGE}

ARG SOURCE_DATE="2026-07-08T01:45:25Z"
LABEL org.opencontainers.image.created="${SOURCE_DATE}" \
      org.opencontainers.image.source="https://github.com/prometheus-community/postgres_exporter" \
      org.opencontainers.image.revision="867fbcac31cd18c143e244190ea9168cca069827" \
      org.opencontainers.image.version="0.20.1-dcim.1" \
      org.opencontainers.image.vendor="DCIM Development derivative" \
      io.dcim.derivative="true" \
      io.dcim.recipe.revision="2" \
      io.dcim.remediation.go="1.26.5" \
      io.dcim.remediation.x-text="0.39.0"

COPY --from=build /out/postgres_exporter /bin/postgres_exporter
