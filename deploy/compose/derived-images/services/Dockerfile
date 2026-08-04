FROM python:3.12-alpine@sha256:6d43704baacd1bfbe7c295d7f13079d5d8104ed33568873133f8fc69980419df AS builder

ARG LIBRDKAFKA_ARCHIVE="librdkafka-2.15.0.tar.gz"
ARG LIBRDKAFKA_SHA256="259015220cdca708afe838b5aa79ebf1a5fb710fb4179cf918d390aed85d5dbc"
ARG SOURCE_DATE_EPOCH

COPY ${LIBRDKAFKA_ARCHIVE} /tmp/librdkafka.tar.gz

RUN apk add --no-cache bash build-base cyrus-sasl-dev openssl-dev zlib-dev \
 && echo "${LIBRDKAFKA_SHA256}  /tmp/librdkafka.tar.gz" | sha256sum -c - \
 && mkdir /src \
 && tar -xzf /tmp/librdkafka.tar.gz -C /src \
 && cd /src/librdkafka-2.15.0 \
 && CFLAGS="-ffile-prefix-map=/src=. -fdebug-prefix-map=/src=." SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH}" ./configure --prefix=/opt/librdkafka --enable-strip \
 && make -j1 \
 && make install \
 && mkdir /build \
 && python3 -m venv /opt/venv \
 && TMPDIR=/build CFLAGS="-ffile-prefix-map=/build=. -fdebug-prefix-map=/build=." \
    LDFLAGS="-Wl,--build-id=none" SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH}" \
    /opt/venv/bin/pip install --no-cache-dir --no-compile \
    pydantic==2.9.2 fastapi==0.116.0 uvicorn[standard]==0.30.6 asyncpg==0.30.0 \
    httpx==0.28.1 prometheus-client==0.26.0 \
 && TMPDIR=/build CFLAGS="-ffile-prefix-map=/build=. -fdebug-prefix-map=/build=." \
    CPPFLAGS="-I/opt/librdkafka/include" LDFLAGS="-L/opt/librdkafka/lib -Wl,--build-id=none" \
    PKG_CONFIG_PATH="/opt/librdkafka/lib/pkgconfig" SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH}" /opt/venv/bin/pip install \
    --no-cache-dir --no-compile --no-binary confluent-kafka confluent-kafka==2.15.0 \
 && strip --strip-unneeded /opt/librdkafka/lib/librdkafka.so.1 \
 && find /opt/venv -name '*.so' -exec strip --strip-unneeded {} + \
 && python3 -c "import pathlib,re; [path.write_bytes(re.sub(rb'pip-install-[^/]+/confluent-kafka_[^/]+/', lambda match: b'.' * len(match.group()), path.read_bytes())) for path in pathlib.Path('/opt/venv').rglob('cimpl*.so')]" \
 && python3 -c 'import base64,hashlib,pathlib; [record.write_text("".join(f"{line.split(\",\", 1)[0]},sha256={base64.urlsafe_b64encode(hashlib.sha256((record.parent.parent / line.split(\",\", 1)[0]).read_bytes()).digest()).decode().rstrip(\"=\")},{(record.parent.parent / line.split(\",\", 1)[0]).stat().st_size}\n" if line.startswith("confluent_kafka/cimpl") else line for line in record.read_text().splitlines(True))) for record in pathlib.Path("/opt/venv").rglob("confluent_kafka-*.dist-info/RECORD")]' \
 && find /opt/librdkafka /opt/venv -exec touch -d "@${SOURCE_DATE_EPOCH}" {} +

FROM python:3.12-alpine@sha256:6d43704baacd1bfbe7c295d7f13079d5d8104ed33568873133f8fc69980419df

LABEL io.dcim.derivative=true \
      org.opencontainers.image.revision="bb96c631cdae148eec0aca3fd0cbe15f485a61c2"

COPY --from=builder /opt/librdkafka/lib/librdkafka*.so* /usr/local/lib/
COPY --from=builder /opt/venv /opt/venv

RUN printf 'dcim:x:10001:\n' >> /etc/group \
 && printf 'dcim:x:10001:10001:DCIM:/nonexistent:/sbin/nologin\n' >> /etc/passwd

ENV PATH="/opt/venv/bin:${PATH}" LD_LIBRARY_PATH="/usr/local/lib"
WORKDIR /opt/dcim
USER 10001:10001

HEALTHCHECK --interval=10s --timeout=5s --retries=12 --start-period=20s CMD python3 -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status==200 else 1)"
