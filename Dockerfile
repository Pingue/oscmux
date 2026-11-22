# syntax=docker/dockerfile:1
FROM ubuntu:24.04 AS build

# Ubuntu ships the Eina headers only in the EFL meta dev package.
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      build-essential cmake pkg-config liblo-dev libefl-all-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY CMakeLists.txt oscmux.c ./
COPY cmake ./cmake
RUN cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
 && cmake --build build


FROM ubuntu:24.04

# tini: oscmux has no signal handlers, and as PID 1 it would otherwise ignore
# SIGTERM (docker stop would wait 10s, then SIGKILL).
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      liblo7 libeina1t64 tini \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --system --no-create-home oscmux \
 && mkdir -m 1777 /run/oscmux

# Eina aborts at startup unless it can create a run dir ($XDG_RUNTIME_DIR or
# $HOME/.run). A sticky world-writable dir works for any user id.
ENV XDG_RUNTIME_DIR=/run/oscmux

COPY --from=build /src/build/oscmux /usr/local/bin/oscmux

USER oscmux
ENTRYPOINT ["/usr/bin/tini", "--", "oscmux"]
