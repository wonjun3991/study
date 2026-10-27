#!/usr/bin/env bash
# Observability 실습 환경 구축 (멱등: 여러 번 실행해도 됨)
#   kind 클러스터 → kube-prometheus-stack → Loki → Tempo → OTel Collector(gateway, agent) → 데모 앱
set -euo pipefail
cd "$(dirname "$0")"

CLUSTER=observability
CTX=kind-${CLUSTER}          # 모든 명령에 context를 명시한다 (기본 context가 다른 클러스터일 수 있음)
NS=observability
K="kubectl --context ${CTX}"
H="helm --kube-context ${CTX}"

# 검증된 chart 버전 (2026-10-11)
KPS_VERSION=92.3.0           # kube-prometheus-stack (Prometheus Operator v0.94.1)
LOKI_VERSION=7.3.0           # Loki 3.6.12
TEMPO_VERSION=1.24.4         # Tempo 2.9.0
OTEL_VERSION=0.175.1         # OpenTelemetry Collector 0.161.0

step() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

step "kind 클러스터"
if ! kind get clusters | grep -qx "${CLUSTER}"; then
  kind create cluster --config kind-config.yaml
fi

step "Helm repo"
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null 2>&1 || true
helm repo add grafana https://grafana.github.io/helm-charts >/dev/null 2>&1 || true
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts >/dev/null 2>&1 || true
helm repo update >/dev/null

step "kube-prometheus-stack (Prometheus · Alertmanager · Grafana · exporters)"
${H} upgrade --install kps prometheus-community/kube-prometheus-stack --version ${KPS_VERSION} \
  -n ${NS} --create-namespace -f helm/kube-prometheus-stack.yaml --wait --timeout 10m

step "Loki"
${H} upgrade --install loki grafana/loki --version ${LOKI_VERSION} \
  -n ${NS} -f helm/loki.yaml --wait --timeout 10m

step "Tempo"
${H} upgrade --install tempo grafana/tempo --version ${TEMPO_VERSION} \
  -n ${NS} -f helm/tempo.yaml --wait --timeout 10m

step "OTel Collector gateway"
${H} upgrade --install otel-gateway open-telemetry/opentelemetry-collector --version ${OTEL_VERSION} \
  -n ${NS} -f helm/otel-gateway.yaml --wait --timeout 5m

step "OTel Collector agent (DaemonSet)"
${H} upgrade --install otel-agent open-telemetry/opentelemetry-collector --version ${OTEL_VERSION} \
  -n ${NS} -f helm/otel-agent.yaml --wait --timeout 5m

step "데모 앱 이미지 빌드 → kind 노드에 로드"
docker build -t demo-app:0.1 demo-app
kind load docker-image demo-app:0.1 --name ${CLUSTER}

step "데모 앱 배포"
${K} apply -f manifests/demo-app.yaml
${K} -n demo rollout restart deploy/gateway deploy/order deploy/payment >/dev/null
for d in gateway order payment loadgen; do ${K} -n demo rollout status deploy/$d --timeout 3m; done

step "완료"
${K} get pods -n ${NS} -o wide
${K} get pods -n demo -o wide
cat <<EOF

Grafana    : kubectl --context ${CTX} -n ${NS} port-forward svc/grafana 3000:80        → http://localhost:3000 (admin / admin)
Prometheus : kubectl --context ${CTX} -n ${NS} port-forward svc/kps-kube-prometheus-stack-prometheus 9090:9090 → http://localhost:9090
EOF
