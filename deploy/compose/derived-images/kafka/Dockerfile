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
ARG JETTY_ALPN_CLIENT_ARCHIVE="jetty-alpn-client-12.0.36.jar"
ARG JETTY_ALPN_CLIENT_SHA256="6b0e03b545fa49fc82cf3149dafb3849e6e0827b3756c31b0e1f5324d86816d2"
ARG JETTY_CLIENT_ARCHIVE="jetty-client-12.0.36.jar"
ARG JETTY_CLIENT_SHA256="1e188b18e8ff6b60ca743e9c9cc39c35f8b6b1b6a7dc07cbdd06800672a1ee02"
ARG JETTY_HTTP_ARCHIVE="jetty-http-12.0.36.jar"
ARG JETTY_HTTP_SHA256="2b5c6ee1303aa979b99afb27e3c602096c344e06da9bdc0057938d1c47f8f1f2"
ARG JETTY_IO_ARCHIVE="jetty-io-12.0.36.jar"
ARG JETTY_IO_SHA256="b191d45e3c48711cc784d509a8dec50112816af392b2b7c76d9e42324b5064da"
ARG JETTY_SECURITY_ARCHIVE="jetty-security-12.0.36.jar"
ARG JETTY_SECURITY_SHA256="e6fb70974291312c58ac84d8bf28c909d1800d1b3104020e7cd4db77391f9fb2"
ARG JETTY_SERVER_ARCHIVE="jetty-server-12.0.36.jar"
ARG JETTY_SERVER_SHA256="f0eb8d1e71d67d0f937c45752546cf479ba55ad3135cf600d3bf723f52cd53fe"
ARG JETTY_SESSION_ARCHIVE="jetty-session-12.0.36.jar"
ARG JETTY_SESSION_SHA256="5b6dc693b9e3d87d309027a5f506b57225b6450444a3f276d9089f2c663cbcc4"
ARG JETTY_UTIL_ARCHIVE="jetty-util-12.0.36.jar"
ARG JETTY_UTIL_SHA256="e16c145dd761168133d1505b6f7cf05343f5e3e3ff03333757c8a6312896ab48"
ARG JETTY_EE10_SERVLET_ARCHIVE="jetty-ee10-servlet-12.0.36.jar"
ARG JETTY_EE10_SERVLET_SHA256="64d42fc2e1c3fd6b7e7a77c1165626bce3a52ef3ed89a7cf00163d11b42201c8"
ARG JETTY_EE10_SERVLETS_ARCHIVE="jetty-ee10-servlets-12.0.36.jar"
ARG JETTY_EE10_SERVLETS_SHA256="e4bc43fbe7ddb1f7658a935b9ad0329d9cf4eae446533bfed7822e6183fe933e"
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
COPY ${JETTY_ALPN_CLIENT_ARCHIVE} /tmp/jetty-alpn-client-12.0.36.jar
COPY ${JETTY_CLIENT_ARCHIVE} /tmp/jetty-client-12.0.36.jar
COPY ${JETTY_HTTP_ARCHIVE} /tmp/jetty-http-12.0.36.jar
COPY ${JETTY_IO_ARCHIVE} /tmp/jetty-io-12.0.36.jar
COPY ${JETTY_SECURITY_ARCHIVE} /tmp/jetty-security-12.0.36.jar
COPY ${JETTY_SERVER_ARCHIVE} /tmp/jetty-server-12.0.36.jar
COPY ${JETTY_SESSION_ARCHIVE} /tmp/jetty-session-12.0.36.jar
COPY ${JETTY_UTIL_ARCHIVE} /tmp/jetty-util-12.0.36.jar
COPY ${JETTY_EE10_SERVLET_ARCHIVE} /tmp/jetty-ee10-servlet-12.0.36.jar
COPY ${JETTY_EE10_SERVLETS_ARCHIVE} /tmp/jetty-ee10-servlets-12.0.36.jar

RUN echo "${JACKSON_SHA256}  /tmp/jackson-databind-2.21.4.jar" | sha256sum -c - \
    && echo "${JACKSON_CORE_SHA256}  /tmp/jackson-core-2.21.4.jar" | sha256sum -c - \
    && echo "${JLINE_SHA256}  /tmp/jline-4.2.1.jar" | sha256sum -c - \
    && echo "${JETTY_ALPN_CLIENT_SHA256}  /tmp/jetty-alpn-client-12.0.36.jar" | sha256sum -c - \
    && echo "${JETTY_CLIENT_SHA256}  /tmp/jetty-client-12.0.36.jar" | sha256sum -c - \
    && echo "${JETTY_HTTP_SHA256}  /tmp/jetty-http-12.0.36.jar" | sha256sum -c - \
    && echo "${JETTY_IO_SHA256}  /tmp/jetty-io-12.0.36.jar" | sha256sum -c - \
    && echo "${JETTY_SECURITY_SHA256}  /tmp/jetty-security-12.0.36.jar" | sha256sum -c - \
    && echo "${JETTY_SERVER_SHA256}  /tmp/jetty-server-12.0.36.jar" | sha256sum -c - \
    && echo "${JETTY_SESSION_SHA256}  /tmp/jetty-session-12.0.36.jar" | sha256sum -c - \
    && echo "${JETTY_UTIL_SHA256}  /tmp/jetty-util-12.0.36.jar" | sha256sum -c - \
    && echo "${JETTY_EE10_SERVLET_SHA256}  /tmp/jetty-ee10-servlet-12.0.36.jar" | sha256sum -c - \
    && echo "${JETTY_EE10_SERVLETS_SHA256}  /tmp/jetty-ee10-servlets-12.0.36.jar" | sha256sum -c - \
    && rm /opt/kafka/libs/jackson-databind-2.21.2.jar \
    && rm /opt/kafka/libs/jackson-core-2.21.2.jar \
    && rm /opt/kafka/libs/jline-3.30.4.jar \
    && rm /opt/kafka/libs/jetty-alpn-client-12.0.34.jar \
    && rm /opt/kafka/libs/jetty-client-12.0.34.jar \
    && rm /opt/kafka/libs/jetty-http-12.0.34.jar \
    && rm /opt/kafka/libs/jetty-io-12.0.34.jar \
    && rm /opt/kafka/libs/jetty-security-12.0.34.jar \
    && rm /opt/kafka/libs/jetty-server-12.0.34.jar \
    && rm /opt/kafka/libs/jetty-session-12.0.34.jar \
    && rm /opt/kafka/libs/jetty-util-12.0.34.jar \
    && rm /opt/kafka/libs/jetty-ee10-servlet-12.0.34.jar \
    && rm /opt/kafka/libs/jetty-ee10-servlets-12.0.34.jar \
    && install -o root -g root -m 0444 /tmp/jackson-databind-2.21.4.jar /opt/kafka/libs/jackson-databind-2.21.4.jar \
    && install -o root -g root -m 0444 /tmp/jackson-core-2.21.4.jar /opt/kafka/libs/jackson-core-2.21.4.jar \
    && install -o root -g root -m 0444 /tmp/jline-4.2.1.jar /opt/kafka/libs/jline-4.2.1.jar \
    && install -o root -g root -m 0444 /tmp/jetty-alpn-client-12.0.36.jar /opt/kafka/libs/jetty-alpn-client-12.0.36.jar \
    && install -o root -g root -m 0444 /tmp/jetty-client-12.0.36.jar /opt/kafka/libs/jetty-client-12.0.36.jar \
    && install -o root -g root -m 0444 /tmp/jetty-http-12.0.36.jar /opt/kafka/libs/jetty-http-12.0.36.jar \
    && install -o root -g root -m 0444 /tmp/jetty-io-12.0.36.jar /opt/kafka/libs/jetty-io-12.0.36.jar \
    && install -o root -g root -m 0444 /tmp/jetty-security-12.0.36.jar /opt/kafka/libs/jetty-security-12.0.36.jar \
    && install -o root -g root -m 0444 /tmp/jetty-server-12.0.36.jar /opt/kafka/libs/jetty-server-12.0.36.jar \
    && install -o root -g root -m 0444 /tmp/jetty-session-12.0.36.jar /opt/kafka/libs/jetty-session-12.0.36.jar \
    && install -o root -g root -m 0444 /tmp/jetty-util-12.0.36.jar /opt/kafka/libs/jetty-util-12.0.36.jar \
    && install -o root -g root -m 0444 /tmp/jetty-ee10-servlet-12.0.36.jar /opt/kafka/libs/jetty-ee10-servlet-12.0.36.jar \
    && install -o root -g root -m 0444 /tmp/jetty-ee10-servlets-12.0.36.jar /opt/kafka/libs/jetty-ee10-servlets-12.0.36.jar \
    && rm /tmp/jackson-databind-2.21.4.jar /tmp/jackson-core-2.21.4.jar /tmp/jline-4.2.1.jar \
       /tmp/jetty-alpn-client-12.0.36.jar /tmp/jetty-client-12.0.36.jar /tmp/jetty-http-12.0.36.jar \
       /tmp/jetty-io-12.0.36.jar /tmp/jetty-security-12.0.36.jar /tmp/jetty-server-12.0.36.jar \
       /tmp/jetty-session-12.0.36.jar /tmp/jetty-util-12.0.36.jar \
       /tmp/jetty-ee10-servlet-12.0.36.jar /tmp/jetty-ee10-servlets-12.0.36.jar \
    && mkdir -p /etc/kafka/secrets /mnt/shared/config /usr/logs /var/lib/kafka/data \
    && chown 1000:1000 /home/appuser /mnt/shared/config /usr/logs \
    && chown 1000:0 /etc/kafka /var/lib/kafka/data \
    && chmod 0775 /etc/kafka /var/lib/kafka/data \
    && touch -d "@${SOURCE_DATE_EPOCH}" /etc/passwd /etc/group /etc/shadow /etc/gshadow \
       /home/appuser /mnt/shared/config /usr/logs /var/lib/kafka/data \
       /opt/kafka/libs/jackson-databind-2.21.4.jar /opt/kafka/libs/jackson-core-2.21.4.jar \
       /opt/kafka/libs/jline-4.2.1.jar \
       /opt/kafka/libs/jetty-alpn-client-12.0.36.jar /opt/kafka/libs/jetty-client-12.0.36.jar \
       /opt/kafka/libs/jetty-http-12.0.36.jar /opt/kafka/libs/jetty-io-12.0.36.jar \
       /opt/kafka/libs/jetty-security-12.0.36.jar /opt/kafka/libs/jetty-server-12.0.36.jar \
       /opt/kafka/libs/jetty-session-12.0.36.jar /opt/kafka/libs/jetty-util-12.0.36.jar \
       /opt/kafka/libs/jetty-ee10-servlet-12.0.36.jar /opt/kafka/libs/jetty-ee10-servlets-12.0.36.jar

LABEL org.opencontainers.image.created="${SOURCE_DATE}" \
      org.opencontainers.image.source="https://github.com/apache/kafka" \
      org.opencontainers.image.revision="26b251a451ce941d3d7a55e6487bcb7f16b5ad48" \
      org.opencontainers.image.version="4.3.1-dcim.2" \
      org.opencontainers.image.vendor="DCIM Development derivative" \
      io.dcim.derivative="true" \
      io.dcim.recipe.revision="3" \
      io.dcim.remediation.jackson-databind="2.21.4" \
      io.dcim.remediation.jackson-core="2.21.4" \
      io.dcim.remediation.jline="4.2.1" \
      io.dcim.remediation.jetty="12.0.36"

EXPOSE 9092
VOLUME ["/etc/kafka/secrets", "/mnt/shared/config", "/var/lib/kafka/data"]
USER appuser
CMD ["/etc/kafka/docker/run"]
