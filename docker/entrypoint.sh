#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${CLUSTER_NAME:-sus-kind}"
K8S_NODES="${K8S_NODES:-1}"

APP_NAME="${APP_NAME:-demo-app}"
APP_IMAGE="${APP_IMAGE:-nginx:1.27-alpine}"
APP_PORT="${APP_PORT:-80}"
APP_REPLICAS="${APP_REPLICAS:-2}"

if ! [[ "${K8S_NODES}" =~ ^[0-9]+$ ]]; then
  echo "K8S_NODES must be an integer >= 1"
  exit 1
fi

if (( K8S_NODES < 1 )); then
  echo "K8S_NODES must be >= 1"
  exit 1
fi

WORKER_NODES=$((K8S_NODES - 1))
KIND_CONFIG="/tmp/kind-config.yaml"
RENDERED_TEMPLATE="/tmp/template.yaml"

{
  echo "kind: Cluster"
  echo "apiVersion: kind.x-k8s.io/v1alpha4"
  echo "nodes:"
  echo "  - role: control-plane"

  i=0
  while (( i < WORKER_NODES )); do
    echo "  - role: worker"
    i=$((i + 1))
  done
} > "${KIND_CONFIG}"

echo "Creating kind cluster '${CLUSTER_NAME}' with ${K8S_NODES} node(s)..."
kind create cluster --name "${CLUSTER_NAME}" --config "${KIND_CONFIG}"

# Optionally build the Python app image from the workspace and load it into the kind cluster
BUILD_APP_IMAGE="${BUILD_APP_IMAGE:-1}"
if [[ "${BUILD_APP_IMAGE}" != "0" ]]; then
  if [[ -d "/workspace/app" ]]; then
    echo "Building app image sus-app:latest from /workspace/app..."
    docker build -t sus-app:latest /workspace/app
    echo "Loading sus-app:latest into kind cluster ${CLUSTER_NAME}..."
    kind load docker-image sus-app:latest --name "${CLUSTER_NAME}"
  else
    echo "/workspace/app not present, skipping app image build"
  fi
fi

export APP_NAME APP_IMAGE APP_PORT APP_REPLICAS
envsubst '${APP_NAME} ${APP_IMAGE} ${APP_PORT} ${APP_REPLICAS}' \
  < /opt/k8s/template.yaml.tpl > "${RENDERED_TEMPLATE}"

echo "Applying Kubernetes template..."
kubectl --context "kind-${CLUSTER_NAME}" apply -f "${RENDERED_TEMPLATE}"

echo "Cluster is ready. Nodes:"
kubectl --context "kind-${CLUSTER_NAME}" get nodes

echo "Resources created from template:"
kubectl --context "kind-${CLUSTER_NAME}" get all

# Deploy patient pods (default 100)
PATIENT_COUNT="${PATIENT_COUNT:-100}"
PATIENT_IMAGE="${PATIENT_IMAGE:-sus-app:latest}"

if ! [[ "${PATIENT_COUNT}" =~ ^[0-9]+$ ]]; then
  echo "PATIENT_COUNT must be an integer >= 0"
  exit 1
fi

if (( PATIENT_COUNT > 0 )); then
  echo "Creating ${PATIENT_COUNT} patient pod(s)..."
  i=1
  while (( i <= PATIENT_COUNT )); do
    PATIENT_NAME="patient-${i}"
    export PATIENT_ID="${i}" PATIENT_NAME PATIENT_IMAGE
    envsubst '${PATIENT_NAME} ${PATIENT_ID} ${PATIENT_IMAGE}' \
      < /opt/k8s/patient-pod.tpl > "/tmp/patient-${i}.yaml"
    kubectl --context "kind-${CLUSTER_NAME}" apply -f "/tmp/patient-${i}.yaml"
    i=$((i + 1))
  done
  echo "Patient pods created."
fi

# Deploy health posts
HEALTH_POST_COUNT="${HEALTH_POST_COUNT:-10}"
HEALTH_POST_IMAGE="${HEALTH_POST_IMAGE:-sus-app:latest}"

if ! [[ "${HEALTH_POST_COUNT}" =~ ^[0-9]+$ ]]; then
  echo "HEALTH_POST_COUNT must be an integer >= 0"
  exit 1
fi

if (( HEALTH_POST_COUNT > 0 )); then
  echo "Creating ${HEALTH_POST_COUNT} health post pod(s)..."
  i=1
  while (( i <= HEALTH_POST_COUNT )); do
    HEALTH_POST_NAME="health-post-${i}"
    export HEALTH_POST_ID="${i}" HEALTH_POST_NAME HEALTH_POST_IMAGE
    envsubst '${HEALTH_POST_NAME} ${HEALTH_POST_ID} ${HEALTH_POST_IMAGE}' \
      < /opt/k8s/health-post-pod.tpl > "/tmp/health-post-${i}.yaml"
    kubectl --context "kind-${CLUSTER_NAME}" apply -f "/tmp/health-post-${i}.yaml"
    i=$((i + 1))
  done
  echo "Health post pods created."
fi

# Deploy SUS database(s)
SUS_DB_COUNT="${SUS_DB_COUNT:-1}"
SUS_DB_IMAGE="${SUS_DB_IMAGE:-sus-app:latest}"

if ! [[ "${SUS_DB_COUNT}" =~ ^[0-9]+$ ]]; then
  echo "SUS_DB_COUNT must be an integer >= 0"
  exit 1
fi

if (( SUS_DB_COUNT > 0 )); then
  echo "Creating ${SUS_DB_COUNT} SUS database pod(s)..."
  i=1
  while (( i <= SUS_DB_COUNT )); do
    SUS_DB_NAME="sus-db-${i}"
    export SUS_DB_NAME SUS_DB_IMAGE
    envsubst '${SUS_DB_NAME} ${SUS_DB_IMAGE}' \
      < /opt/k8s/sus-database-pod.tpl > "/tmp/sus-db-${i}.yaml"
    kubectl --context "kind-${CLUSTER_NAME}" apply -f "/tmp/sus-db-${i}.yaml"
    i=$((i + 1))
  done
  echo "SUS database pods created."
fi

# Deploy National database(s)
NATIONAL_DB_COUNT="${NATIONAL_DB_COUNT:-0}"
NATIONAL_DB_IMAGE="${NATIONAL_DB_IMAGE:-sus-app:latest}"

if ! [[ "${NATIONAL_DB_COUNT}" =~ ^[0-9]+$ ]]; then
  echo "NATIONAL_DB_COUNT must be an integer >= 0"
  exit 1
fi

if (( NATIONAL_DB_COUNT > 0 )); then
  echo "Creating ${NATIONAL_DB_COUNT} national database pod(s)..."
  i=1
  while (( i <= NATIONAL_DB_COUNT )); do
    NATIONAL_DB_NAME="national-db-${i}"
    export NATIONAL_DB_NAME NATIONAL_DB_IMAGE
    envsubst '${NATIONAL_DB_NAME} ${NATIONAL_DB_IMAGE}' \
      < /opt/k8s/national-database-pod.tpl > "/tmp/national-db-${i}.yaml"
    kubectl --context "kind-${CLUSTER_NAME}" apply -f "/tmp/national-db-${i}.yaml"
    i=$((i + 1))
  done
  echo "National database pods created."
fi

if [[ $# -gt 0 ]]; then
  exec "$@"
fi

# Keep the container alive for inspection and kubectl access.
tail -f /dev/null
