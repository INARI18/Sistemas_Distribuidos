FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        docker.io \
        gettext-base \
    && rm -rf /var/lib/apt/lists/*

ARG KIND_VERSION=v0.23.0
ARG KUBECTL_VERSION=v1.30.2

RUN curl -fsSL -o /usr/local/bin/kind https://kind.sigs.k8s.io/dl/${KIND_VERSION}/kind-linux-amd64 \
    && chmod +x /usr/local/bin/kind \
    && curl -fsSL -o /usr/local/bin/kubectl https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl \
    && chmod +x /usr/local/bin/kubectl

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY k8s/patient-pod.tpl /opt/k8s/patient-pod.tpl
COPY k8s/health-post-pod.tpl /opt/k8s/health-post-pod.tpl
COPY k8s/sus-database-pod.tpl /opt/k8s/sus-database-pod.tpl
COPY k8s/national-database-pod.tpl /opt/k8s/national-database-pod.tpl

RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
