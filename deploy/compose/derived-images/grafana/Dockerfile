# syntax=docker/dockerfile:1.19.0@sha256:b6afd42430b15f2d2a4c5a02b919e98a525b785b1aaff16747d2f623364e39b6

ARG GO_IMAGE="golang:1.26.5-alpine3.24@sha256:0178a641fbb4858c5f1b48e34bdaabe0350a330a1b1149aabd498d0699ff5fb2"
ARG UPSTREAM_IMAGE="grafana/grafana:13.1.0-ubuntu-slim@sha256:936197495b76734df72002e6f3ff122cffd2d7027679a1c7c4a611cf90baee05"

FROM ${GO_IMAGE} AS grafana-build

ARG SOURCE_DATE_EPOCH
ARG GRAFANA_ARCHIVE="grafana-b309c9b.tar.gz"
ARG GRAFANA_SHA256="1de79b2f09e33e3a03fe83dc86bce3601be163bbf55098c37beb1dc11c01de86"
ARG GRAFANA_DIRECTORY="grafana-b309c9bb3b81a748c3a75289236a27309ed2566a"
ARG TEMPO_ARCHIVE="tempo-4aeafc2.tar.gz"
ARG TEMPO_SHA256="6159f130af77216215137a1033e3f573cc83e7aba69a19d618b521b7ab41d81f"
ARG TEMPO_DIRECTORY="tempo-4aeafc237b8d9a8d62e45735131e8a89eb741a00"
ARG GRPC_ARCHIVE="grpc-go-ebd8f06.tar.gz"
ARG GRPC_SHA256="50947ea17daeccbfcc031e7d7b93dd3293da79ed0573352d8ea3d324c8326582"
ARG KIN_OPENAPI_ARCHIVE="kin-openapi-f0407d5.tar.gz"
ARG KIN_OPENAPI_SHA256="80395f1aefd21eea1d8a6664e70c03f08bd798b6014d84b2e8faa71adf4dfe2c"
ARG X_TEXT_ARCHIVE="x-text-0.39.0.tar.gz"
ARG X_TEXT_SHA256="c2e68286e1061496dcbb794cec0e40c20c744885b495ff6c7d40f3459699c6c0"

COPY ${GRAFANA_ARCHIVE} /tmp/grafana.tar.gz
COPY ${TEMPO_ARCHIVE} /tmp/tempo.tar.gz
COPY ${GRPC_ARCHIVE} /tmp/grpc-go.tar.gz
COPY ${KIN_OPENAPI_ARCHIVE} /tmp/kin-openapi.tar.gz
COPY ${X_TEXT_ARCHIVE} /tmp/x-text.tar.gz
RUN echo "${GRAFANA_SHA256}  /tmp/grafana.tar.gz" | sha256sum -c - \
    && echo "${TEMPO_SHA256}  /tmp/tempo.tar.gz" | sha256sum -c - \
    && echo "${GRPC_SHA256}  /tmp/grpc-go.tar.gz" | sha256sum -c - \
    && echo "${KIN_OPENAPI_SHA256}  /tmp/kin-openapi.tar.gz" | sha256sum -c - \
    && echo "${X_TEXT_SHA256}  /tmp/x-text.tar.gz" | sha256sum -c - \
    && mkdir -p /src/grafana /src/tempo /src/grpc-go /src/kin-openapi /src/x-text \
    && tar -xzf /tmp/grafana.tar.gz -C /src/grafana --strip-components=1 \
    && tar -xzf /tmp/tempo.tar.gz -C /src/tempo --strip-components=1 \
    && tar -xzf /tmp/grpc-go.tar.gz -C /src/grpc-go --strip-components=1 \
    && tar -xzf /tmp/kin-openapi.tar.gz -C /src/kin-openapi --strip-components=1 \
    && tar -xzf /tmp/x-text.tar.gz -C /src/x-text --strip-components=1

WORKDIR /src/grafana
ENV GOWORK=off
RUN sed -i 's/^go 1\.26\.4$/go 1.26.5/' go.mod go.work \
    && sed -i 's#github.com/grafana/tempo v1.5.1-0.20260427112133-525d1bab07e0#github.com/grafana/tempo v2.10.3+incompatible#' go.mod \
    && printf '\nreplace github.com/grafana/tempo => /src/tempo\n' >> go.mod \
    && go mod edit -require=google.golang.org/grpc@v1.82.1 \
    && go mod edit -replace=google.golang.org/grpc=/src/grpc-go \
    && go mod edit -require=github.com/getkin/kin-openapi@v0.144.0 \
    && go mod edit -replace=github.com/getkin/kin-openapi=/src/kin-openapi \
    && go mod edit -require=golang.org/x/text@v0.39.0 \
    && go mod edit -replace=golang.org/x/text=/src/x-text \
    && grep -F 'github.com/grafana/tempo v2.10.3+incompatible' go.mod \
    && grep -F 'replace github.com/grafana/tempo => /src/tempo' go.mod \
    && grep -F 'google.golang.org/grpc v1.82.1' go.mod \
    && grep -F 'replace google.golang.org/grpc => /src/grpc-go' go.mod \
    && grep -F 'github.com/getkin/kin-openapi v0.144.0' go.mod \
    && grep -F 'replace github.com/getkin/kin-openapi => /src/kin-openapi' go.mod \
    && grep -F 'golang.org/x/text v0.39.0' go.mod \
    && grep -F 'replace golang.org/x/text => /src/x-text' go.mod \
    && go mod vendor -e \
    && go mod edit -dropreplace=github.com/grafana/tempo \
    && go mod edit -dropreplace=google.golang.org/grpc \
    && go mod edit -dropreplace=github.com/getkin/kin-openapi \
    && go mod edit -dropreplace=golang.org/x/text \
    && sed -i 's|^# github.com/grafana/tempo v2.10.3+incompatible => /src/tempo$|# github.com/grafana/tempo v2.10.3+incompatible|' vendor/modules.txt \
    && sed -i '/^# github\.com\/grafana\/tempo => \/src\/tempo$/d' vendor/modules.txt \
    && sed -i 's|^# google.golang.org/grpc v1.82.1 => /src/grpc-go$|# google.golang.org/grpc v1.82.1|' vendor/modules.txt \
    && sed -i '/^# google\.golang\.org\/grpc => \/src\/grpc-go$/d' vendor/modules.txt \
    && sed -i 's|^# github.com/getkin/kin-openapi v0.144.0 => /src/kin-openapi$|# github.com/getkin/kin-openapi v0.144.0|' vendor/modules.txt \
    && sed -i '/^# github\.com\/getkin\/kin-openapi => \/src\/kin-openapi$/d' vendor/modules.txt \
    && sed -i 's|^# golang.org/x/text v0.39.0 => /src/x-text$|# golang.org/x/text v0.39.0|' vendor/modules.txt \
    && sed -i '/^# golang\.org\/x\/text => \/src\/x-text$/d' vendor/modules.txt \
    && go list -mod=vendor -m github.com/grafana/tempo google.golang.org/grpc github.com/getkin/kin-openapi golang.org/x/text \
    && grep -Fx '# github.com/grafana/tempo v2.10.3+incompatible' vendor/modules.txt \
    && grep -Fx '# google.golang.org/grpc v1.82.1' vendor/modules.txt \
    && grep -Fx '# github.com/getkin/kin-openapi v0.144.0' vendor/modules.txt \
    && grep -Fx '# golang.org/x/text v0.39.0' vendor/modules.txt
RUN --network=none CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -mod=vendor -buildvcs=false -trimpath -tags oss \
    -ldflags='-s -w -X main.version=13.1.0 -X main.commit=b309c9bb3b81a748c3a75289236a27309ed2566a -X main.buildBranch=main -X main.buildstamp=1782214211' \
    -o /out/grafana ./pkg/cmd/grafana
RUN touch -d "@${SOURCE_DATE_EPOCH}" /out/grafana

FROM ${UPSTREAM_IMAGE}

ARG SOURCE_DATE="2026-06-23T11:30:11Z"
LABEL org.opencontainers.image.created="${SOURCE_DATE}" \
      org.opencontainers.image.source="https://github.com/grafana/grafana" \
      org.opencontainers.image.revision="b309c9bb3b81a748c3a75289236a27309ed2566a" \
      org.opencontainers.image.version="13.1.0-dcim.4" \
      org.opencontainers.image.vendor="DCIM Development derivative" \
      io.dcim.derivative="true" \
      io.dcim.recipe.revision="5" \
      io.dcim.remediation.go="1.26.5" \
      io.dcim.remediation.tempo="2.10.3" \
      io.dcim.remediation.grpc-go="1.82.1" \
      io.dcim.remediation.kin-openapi="0.144.0" \
      io.dcim.remediation.x-text="0.39.0"

COPY --from=grafana-build --chown=472:0 /out/grafana /usr/share/grafana/bin/grafana
