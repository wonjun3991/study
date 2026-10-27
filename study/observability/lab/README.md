# Observability Lab (kind)

8주 커리큘럼 전체에서 공용으로 쓰는 실습 환경. Metric · Log · Trace 파이프라인을 kind 클러스터 하나에 모두 올린다.

## 구성

```
                    ┌──────────────── node (worker × 2) ────────────────┐
 loadgen ─▶ gateway ─▶ order ─▶ payment                                 │
              │ OTLP (trace·metric)          stdout JSON 로그             │
              ▼                               ▼ /var/log/pods/*.log       │
          otel-agent (DaemonSet) ◀── filelog receiver                    │
              │  k8sattributes · JSON 파싱(trace_id 승격)                  │
              └────────────────────────────────────────────────────────┘
              ▼ OTLP
          otel-gateway (Deployment)
              ├─ metric ─▶ Prometheus  (/api/v1/otlp)      ◀─ scrape: node-exporter, kube-state-metrics, kubelet
              ├─ log    ─▶ Loki        (/otlp)
              └─ trace  ─▶ Tempo       (:4317) ── metrics-generator ─▶ Prometheus (remote_write)
                                        ▼
                                     Grafana  (metric ↔ trace ↔ log 이동)
```

| 컴포넌트 | Chart (버전) | 역할 | 파일 |
|---|---|---|---|
| kind | `kindest/node:v1.36.1` | control-plane 1 + worker 2 | `kind-config.yaml` |
| kube-prometheus-stack | `prometheus-community/kube-prometheus-stack` 92.3.0 | Prometheus(TSDB·PromQL·OTLP 수신), Alertmanager, Grafana, node-exporter, kube-state-metrics | `helm/kube-prometheus-stack.yaml` |
| Loki | `grafana/loki` 7.3.0 (Loki 3.6) | 로그 저장 (SingleBinary, filesystem) | `helm/loki.yaml` |
| Tempo | `grafana/tempo` 1.24.4 (Tempo 2.9) | trace 저장 + span metrics/service graph 생성 | `helm/tempo.yaml` |
| OTel Collector gateway | `open-telemetry/opentelemetry-collector` 0.175.1 | 신호별 백엔드 라우팅 | `helm/otel-gateway.yaml` |
| OTel Collector agent | 같은 chart (DaemonSet) | 노드 단위 수집, k8s 메타데이터 부착, 로그 파일 수집 | `helm/otel-agent.yaml` |
| 데모 앱 | 직접 빌드 (`demo-app:0.1`) | FastAPI 3개 서비스 + OTel 자동 계측 | `demo-app/`, `manifests/demo-app.yaml` |

## 실행

```bash
cd study/observability/lab
./up.sh      # 클러스터 생성 ~ 데모 앱 배포까지 (멱등)
./down.sh    # kind 클러스터 삭제
```

모든 명령은 `--context kind-observability`를 명시한다. 기본 kubectl context가 다른(원격) 클러스터를 가리키고 있어도 안전하게 하기 위해서다.

## 접속

```bash
kubectl --context kind-observability -n observability port-forward svc/grafana 3000:80          # http://localhost:3000  admin/admin
kubectl --context kind-observability -n observability port-forward svc/kps-kube-prometheus-stack-prometheus 9090:9090 # http://localhost:9090
```

## 확인 포인트

| 신호 | 어디서 | 쿼리 예시 |
|---|---|---|
| Metric (앱, OTLP) | Grafana → Explore → Prometheus | `sum by (job, http_response_status_code) (rate(http_server_request_duration_seconds_count[1m]))` (`job` = `service.namespace/service.name`, 예: `demo/gateway`) |
| Metric (커스텀) | 〃 | `sum by (outcome) (rate(demo_orders_total[1m]))` |
| Metric (trace에서 생성) | 〃 | `histogram_quantile(0.95, sum by (le, service) (rate(traces_spanmetrics_latency_bucket[5m])))` |
| Metric (인프라, scrape) | 〃 | `sum by (namespace) (container_memory_working_set_bytes{container!=""})` |
| Log | Grafana → Explore → Loki | `{service_name="payment"} \| json \| level="ERROR"` |
| Trace | Grafana → Explore → Tempo | TraceQL: `{ resource.service.name = "gateway" && duration > 1s }` |
| 연결 | Tempo span → "Logs for this span" / Loki 로그의 `trace_id` → "View trace" / Prometheus 그래프의 exemplar 점 | |

## 설계 메모

- **앱 → agent 경로**: agent Service는 `internalTrafficPolicy: Local`이라 항상 같은 노드의 agent로 간다. source IP가 Pod IP로 유지되어 `k8sattributes`가 Pod를 식별할 수 있다.
- **로그는 OTLP로 보내지 않는다** (`OTEL_LOGS_EXPORTER=none`). 앱은 stdout에 JSON만 쓰고 agent의 filelog receiver가 수집한다. 같은 로그를 OTLP와 파일로 동시에 받으면 중복 저장되기 때문. agent의 `transform/json_logs`가 JSON의 `trace_id`를 LogRecord의 trace context로 승격시켜 Loki structured metadata가 된다.
- **Metric 경로가 2개**: 앱 metric은 OTLP push(gateway → Prometheus OTLP receiver), 인프라 metric은 Prometheus가 scrape. 같은 대상을 두 번 수집하지 않도록 나눴다.
- **HTTP semconv opt-in**: Python 자동 계측은 기본으로 옛 HTTP semconv(`http_server_duration_milliseconds`)를 내보낸다. `OTEL_SEMCONV_STABILITY_OPT_IN=http`로 stable 이름(`http_server_request_duration_seconds`, `http_response_status_code`)을 쓰게 했다.
- **agent는 worker 노드에만 뜬다**: control-plane taint 때문에 control-plane 노드의 Pod 로그(apiserver 등)는 수집하지 않는다. node-exporter는 toleration이 있어 3개 노드 모두에 뜬다.
- **kind에서 끈 scrape 대상**: etcd, kube-scheduler, kube-controller-manager, kube-proxy는 127.0.0.1에만 metric을 노출해서 target down이 된다.
- **Collector 컴포넌트 이름**: Collector 0.161부터 `otlp` exporter → `otlp_grpc`, `filelog` → `file_log`, `k8sattributes` → `k8s_attributes`처럼 이름이 바뀌었다. chart의 `rewriteDeprecatedComponentNames: true`(기본값)가 values의 옛 이름을 새 이름으로 바꿔준다.
- **`grafana/tempo` chart는 deprecated** 경고가 뜬다. 실습용 single binary로는 아직 동작하지만, 운영 구성은 `tempo-distributed`를 쓴다.
