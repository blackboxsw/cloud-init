FROM ubuntu:25.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libssl-dev \
        locales \
        make \
        python3-dev \
        shellcheck \
        shfmt && \
    locale-gen en_US.UTF-8 && \
    ln -sf /usr/bin/python3 /usr/local/bin/python && \
    rm -rf /var/lib/apt/lists/*

USER ubuntu

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
