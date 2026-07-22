# syntax=docker/dockerfile:1.19.0@sha256:b6afd42430b15f2d2a4c5a02b919e98a525b785b1aaff16747d2f623364e39b6

ARG GO_IMAGE="golang:1.26.5-alpine3.24@sha256:0178a641fbb4858c5f1b48e34bdaabe0350a330a1b1149aabd498d0699ff5fb2"
ARG UPSTREAM_IMAGE="prom/prometheus:v3.13.1@sha256:3c42b892cf723fa54d2f262c37a0e1f80aa8c8ddb1da7b9b0df9455a35a7f893"

FROM ${GO_IMAGE} AS build

ARG SOURCE_DATE_EPOCH
ARG PROMETHEUS_ARCHIVE="prometheus-73ff57c.tar.gz"
ARG PROMETHEUS_SHA256="322276709c16cb3c22a4d01d244beb91f0380a257699358d2a20ac7086d7256c"
ARG UI_ARCHIVE="prometheus-web-ui-3.13.1.tar.gz"
ARG UI_SHA256="2194bfbb5d36457df2b8f480037ce89786ee32f03b5ee6ad5597989f14deafb0"
ARG GRPC_ARCHIVE="grpc-go-ebd8f06.tar.gz"
ARG GRPC_SHA256="50947ea17daeccbfcc031e7d7b93dd3293da79ed0573352d8ea3d324c8326582"

COPY ${PROMETHEUS_ARCHIVE} /tmp/prometheus.tar.gz
COPY ${UI_ARCHIVE} /tmp/prometheus-ui.tar.gz
COPY ${GRPC_ARCHIVE} /tmp/grpc-go.tar.gz
RUN echo "${PROMETHEUS_SHA256}  /tmp/prometheus.tar.gz" | sha256sum -c - \
    && echo "${UI_SHA256}  /tmp/prometheus-ui.tar.gz" | sha256sum -c - \
    && echo "${GRPC_SHA256}  /tmp/grpc-go.tar.gz" | sha256sum -c - \
    && mkdir -p /src/prometheus /src/prebuilt-ui /src/grpc-go \
    && tar -xzf /tmp/prometheus.tar.gz -C /src/prometheus --strip-components=1 \
    && tar -xzf /tmp/prometheus-ui.tar.gz -C /src/prebuilt-ui \
    && tar -xzf /tmp/grpc-go.tar.gz -C /src/grpc-go --strip-components=1

WORKDIR /src/prometheus
ENV GOWORK=off
RUN go mod edit -require=google.golang.org/grpc@v1.82.1 \
    && go mod edit -replace=google.golang.org/grpc=/src/grpc-go \
    && grep -F 'google.golang.org/grpc v1.82.1' go.mod \
    && grep -F 'replace google.golang.org/grpc => /src/grpc-go' go.mod \
    && go mod vendor \
    && go mod edit -dropreplace=google.golang.org/grpc \
    && sed -i 's|^# google.golang.org/grpc v1.82.1 => /src/grpc-go$|# google.golang.org/grpc v1.82.1|' vendor/modules.txt \
    && sed -i '/^# google\.golang\.org\/grpc => \/src\/grpc-go$/d' vendor/modules.txt \
    && go list -mod=vendor -m google.golang.org/grpc \
        | grep -Fx 'google.golang.org/grpc v1.82.1'
RUN mkdir -p web/ui/static \
    && find /src/prebuilt-ui/static -type f -print | sort | while IFS= read -r file; do \
        relative="${file#/src/prebuilt-ui/static/}"; \
        mkdir -p "web/ui/static/$(dirname "${relative}")"; \
        gzip -n -c "${file}" > "web/ui/static/${relative}.gz"; \
    done \
    && cp web/ui/embed.go.tmpl web/ui/embed.go \
    && { printf '//go:embed'; find web/ui/static -type f -name '*.gz' -print \
        | sed 's#^web/ui/##' | sort | while IFS= read -r file; do printf ' %s' "${file}"; done; \
        printf '\nvar EmbedFS embed.FS\n'; } >> web/ui/embed.go
RUN --network=none CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -mod=vendor -buildvcs=false -trimpath -tags netgo,builtinassets \
    -ldflags='-s -w -X github.com/prometheus/common/version.Version=3.13.1 -X github.com/prometheus/common/version.Revision=73ff57ce2b8161059ac7fe5188f03f1c3d22b29a -X github.com/prometheus/common/version.Branch=HEAD -X github.com/prometheus/common/version.BuildUser=dcim@development -X github.com/prometheus/common/version.BuildDate=20260710-08:03:47' \
    -o /out/prometheus ./cmd/prometheus \
    && go build -mod=vendor -buildvcs=false -trimpath -tags netgo,builtinassets \
    -ldflags='-s -w -X github.com/prometheus/common/version.Version=3.13.1 -X github.com/prometheus/common/version.Revision=73ff57ce2b8161059ac7fe5188f03f1c3d22b29a -X github.com/prometheus/common/version.Branch=HEAD -X github.com/prometheus/common/version.BuildUser=dcim@development -X github.com/prometheus/common/version.BuildDate=20260710-08:03:47' \
    -o /out/promtool ./cmd/promtool
RUN touch -d "@${SOURCE_DATE_EPOCH}" /out/prometheus /out/promtool

FROM ${UPSTREAM_IMAGE}

ARG SOURCE_DATE="2026-07-10T08:03:47Z"
LABEL org.opencontainers.image.created="${SOURCE_DATE}" \
      org.opencontainers.image.source="https://github.com/prometheus/prometheus" \
      org.opencontainers.image.revision="73ff57ce2b8161059ac7fe5188f03f1c3d22b29a" \
      org.opencontainers.image.version="3.13.1-dcim.2" \
      org.opencontainers.image.vendor="DCIM Development derivative" \
      io.dcim.derivative="true" \
      io.dcim.recipe.revision="2" \
      io.dcim.remediation.grpc-go="1.82.1"

COPY --from=build --chown=65534:65534 /out/prometheus /bin/prometheus
COPY --from=build --chown=65534:65534 /out/promtool /bin/promtool
