# syntax=docker/dockerfile:1.19.0@sha256:b6afd42430b15f2d2a4c5a02b919e98a525b785b1aaff16747d2f623364e39b6

ARG GO_IMAGE="golang:1.26.5-alpine3.24@sha256:0178a641fbb4858c5f1b48e34bdaabe0350a330a1b1149aabd498d0699ff5fb2"
ARG UPSTREAM_IMAGE="postgres:17.10-alpine3.24@sha256:742f40ea20b9ff2ff31db5458d127452988a2164df9e17441e191f3b72252193"

FROM ${GO_IMAGE} AS gosu-build

ARG SOURCE_DATE_EPOCH
ARG SOURCE_ARCHIVE="gosu-6456aaa.tar.gz"
ARG SOURCE_SHA256="33d7537d588ea49458b9509bcf4554bdf5ceacc66da71e5caa1058ea3b689c3b"
ARG SOURCE_DIRECTORY="gosu-6456aaa0f3c854d199d0f037f068eb97515b7513"

COPY ${SOURCE_ARCHIVE} /tmp/source.tar.gz
RUN echo "${SOURCE_SHA256}  /tmp/source.tar.gz" | sha256sum -c -
RUN mkdir /src && tar -xzf /tmp/source.tar.gz -C /src
WORKDIR /src/${SOURCE_DIRECTORY}
RUN go mod download
RUN --network=none CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -trimpath -ldflags="-s -w" -o /out/gosu .
RUN touch -d "@${SOURCE_DATE_EPOCH}" /out/gosu

FROM ${UPSTREAM_IMAGE}

ARG SOURCE_DATE="2026-07-08T16:08:37Z"
ARG SOURCE_DATE_EPOCH
USER root
RUN sed -i 's/^postgres:x:70:70:/postgres:x:999:999:/' /etc/passwd \
    && sed -i 's/^postgres:x:70:/postgres:x:999:/' /etc/group \
    && chown 999:999 /var/lib/postgresql /var/lib/postgresql/data /var/run/postgresql \
    && touch -d "@${SOURCE_DATE_EPOCH}" /etc/passwd /etc/group /var/lib/postgresql /var/lib/postgresql/data /var/run/postgresql
LABEL org.opencontainers.image.created="${SOURCE_DATE}" \
      org.opencontainers.image.source="https://github.com/docker-library/postgres" \
      org.opencontainers.image.revision="4f9ced003ba58a854656ba150d146243d27ae3ac" \
      org.opencontainers.image.version="17.10-dcim.1" \
      org.opencontainers.image.vendor="DCIM Development derivative" \
      io.dcim.derivative="true" \
      io.dcim.recipe.revision="1" \
      io.dcim.remediation.gosu.revision="6456aaa0f3c854d199d0f037f068eb97515b7513"

COPY --from=gosu-build /out/gosu /usr/local/bin/gosu
