# Dockerfile for Aegis Rust Proxy
FROM rust:1.75 as builder

WORKDIR /app
COPY Cargo.toml Cargo.toml
COPY src src

RUN cargo build --release

# Runtime image
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/target/release/aegis_proxy /usr/local/bin/aegis_proxy

ENV ORIGIN_URL=http://origin:9000
EXPOSE 8080

CMD ["aegis_proxy"]
