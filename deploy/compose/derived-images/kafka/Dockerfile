# syntax=docker/dockerfile:1.19.0@sha256:b6afd42430b15f2d2a4c5a02b919e98a525b785b1aaff16747d2f623364e39b6

ARG UPSTREAM_IMAGE="apache/kafka:4.3.1@sha256:77e3df9054047a88b520d0cc46e16696d3b22022e1d580aeccd2632df6532837"
ARG RUNTIME_IMAGE="eclipse-temurin:21.0.11_10-jre-noble@sha256:373787d1d45a87f084fda43e7de0e9acf5eedee049446efac738f13587ec4c64"

FROM ${UPSTREAM_IMAGE} AS kafka-upstream

FROM ${RUNTIME_IMAGE}

ARG JACKSON_ARCHIVE="jackson-databind-2.21.4.jar"
ARG JACKSON_SHA256="3888e9e69ab66fbacaacc9aea0e9ffbf15368288e4aca468b024dba11c09fbf9"
ARG JACKSON_CORE_ARCHIVE="jackson-core-2.21.4.jar"
ARG JACKSON_CORE_SHA256="4b40a06396f239f8de2da57419adde6e94e5edc18a2171d471ea05eeed4e5c2d"
ARG JLINE_ARCHIVE="jline-4.2.1.jar"
ARG JLINE_SHA256="bdbe3b7b276ee609c28f11f704be11fdebe7375eb1a7d10a489086225cdbc535"
ARG SOURCE_DATE="2026-06-17T19:23:00Z"
ARG SOURCE_DATE_EPOCH

USER root

RUN groupmod --new-name appuser ubuntu \
    && usermod --login appuser --home /home/appuser --move-home ubuntu

COPY --from=kafka-upstream --chown=1000:1000 /opt/kafka /opt/kafka
COPY --from=kafka-upstream --chown=1000:0 /etc/kafka /etc/kafka
COPY ${JACKSON_ARCHIVE} /tmp/jackson-databind-2.21.4.jar
COPY ${JACKSON_CORE_ARCHIVE} /tmp/jackson-core-2.21.4.jar
COPY ${JLINE_ARCHIVE} /tmp/jline-4.2.1.jar

RUN echo "${JACKSON_SHA256}  /tmp/jackson-databind-2.21.4.jar" | sha256sum -c - \
    && echo "${JACKSON_CORE_SHA256}  /tmp/jackson-core-2.21.4.jar" | sha256sum -c - \
    && echo "${JLINE_SHA256}  /tmp/jline-4.2.1.jar" | sha256sum -c - \
    && rm /opt/kafka/libs/jackson-databind-2.21.2.jar \
    && rm /opt/kafka/libs/jackson-core-2.21.2.jar \
    && rm /opt/kafka/libs/jline-3.30.4.jar \
    && install -o root -g root -m 0444 /tmp/jackson-databind-2.21.4.jar /opt/kafka/libs/jackson-databind-2.21.4.jar \
    && install -o root -g root -m 0444 /tmp/jackson-core-2.21.4.jar /opt/kafka/libs/jackson-core-2.21.4.jar \
    && install -o root -g root -m 0444 /tmp/jline-4.2.1.jar /opt/kafka/libs/jline-4.2.1.jar \
    && rm /tmp/jackson-databind-2.21.4.jar /tmp/jackson-core-2.21.4.jar /tmp/jline-4.2.1.jar \
    && mkdir -p /etc/kafka/secrets /mnt/shared/config /usr/logs /var/lib/kafka/data \
    && chown 1000:1000 /home/appuser /mnt/shared/config /usr/logs \
    && chown 1000:0 /etc/kafka /var/lib/kafka/data \
    && chmod 0775 /etc/kafka /var/lib/kafka/data \
    && touch -d "@${SOURCE_DATE_EPOCH}" /etc/passwd /etc/group /etc/shadow /etc/gshadow \
       /home/appuser /mnt/shared/config /usr/logs /var/lib/kafka/data \
       /opt/kafka/libs/jackson-databind-2.21.4.jar /opt/kafka/libs/jackson-core-2.21.4.jar \
       /opt/kafka/libs/jline-4.2.1.jar

LABEL org.opencontainers.image.created="${SOURCE_DATE}" \
      org.opencontainers.image.source="https://github.com/apache/kafka" \
      org.opencontainers.image.revision="26b251a451ce941d3d7a55e6487bcb7f16b5ad48" \
      org.opencontainers.image.version="4.3.1-dcim.1" \
      org.opencontainers.image.vendor="DCIM Development derivative" \
      io.dcim.derivative="true" \
      io.dcim.recipe.revision="2" \
      io.dcim.remediation.jackson-databind="2.21.4" \
      io.dcim.remediation.jackson-core="2.21.4" \
      io.dcim.remediation.jline="4.2.1"

EXPOSE 9092
VOLUME ["/etc/kafka/secrets", "/mnt/shared/config", "/var/lib/kafka/data"]
USER appuser
CMD ["/etc/kafka/docker/run"]
