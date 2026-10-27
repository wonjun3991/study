# Cilium Study Curriculum (9 Weeks)

> **목표**
>
> Kubernetes Networking의 기초부터 Cilium의 핵심 기능을 이해하고,
> 최종적으로 **"왜 Cilium이 Istio의 대안으로 주목받는가?"**를 이해하는 것을 목표로 한다.

---

# 1주차 - 왜 Cilium인가?

## 목표

Cilium이 등장하게 된 배경과 Istio와 비교되는 이유를 이해한다.

## 핵심 질문

- Kubernetes에서 Cilium은 왜 등장했는가?
- Istio는 왜 Service Mesh를 만들었는가?
- Sidecar 방식의 문제점은 무엇인가?
- Cilium은 어떤 방식으로 이를 해결하는가?
- Cilium과 Istio는 경쟁 관계인가?

## 학습 내용

- Kubernetes Networking 복습
- Service Mesh 등장 배경
- Istio Sidecar Architecture
- Sidecar 방식의 장단점
- eBPF 기반 접근 방식
- Cilium Architecture
- CNI와 Service Mesh의 역할 차이
- Cilium과 Istio 비교

---

# 2주차 - CNI로서 Cilium은 Kubernetes 네트워크에 어떻게 붙는가?

## 목표

Pod Networking이 어떻게 구성되는지 이해하고,
Cilium이 Kubernetes Networking Layer에서 어떤 역할을 하는지 이해한다.

## 핵심 질문

- CNI란 무엇인가?
- Pod는 어떻게 네트워크를 가지는가?
- Pod IP는 누가 할당하는가?
- Node 간 Pod 통신은 어떻게 이루어지는가?
- Cilium은 기존 CNI와 무엇이 다른가?

## 학습 내용

- Kubernetes Network Model
- CNI 동작 원리
- Network Namespace
- Pause Container
- veth Pair
- IPAM
- Overlay / Native Routing
- VXLAN / Geneve
- Cilium Agent
- Cilium Operator
- Cilium Endpoint
- Cilium Identity

---

# 3주차 - Cilium eBPF Datapath와 kube-proxy Replacement

## 목표

Cilium이 eBPF를 이용하여 kube-proxy를 어떻게 대체하는지 이해한다.

## 핵심 질문

- kube-proxy는 무엇을 하는가?
- eBPF는 무엇인가?
- Cilium은 Service Routing을 어떻게 처리하는가?
- BPF Map은 무엇인가?
- 왜 kube-proxy가 필요 없어지는가?

## 학습 내용

- Kubernetes Service
- kube-proxy
- iptables / IPVS
- eBPF 기본 개념
- eBPF Hook
- BPF Map
- Cilium Service Load Balancing
- ClusterIP
- NodePort
- LoadBalancer
- DNAT / Reverse NAT
- Connection Tracking

---

# 4주차 - Network Policy는 어디서 강제되는가?

## 목표

Kubernetes NetworkPolicy와 CiliumNetworkPolicy가
실제로 어떻게 동작하는지 이해한다.

## 핵심 질문

- NetworkPolicy는 누가 적용하는가?
- Cilium은 어떻게 정책을 강제하는가?
- Default Deny는 어떻게 동작하는가?
- Label 기반 정책은 왜 중요한가?

## 학습 내용

- Kubernetes NetworkPolicy
- CiliumNetworkPolicy
- Default Allow
- Default Deny
- Ingress / Egress
- Endpoint Selector
- Identity 기반 Policy
- eBPF Policy Enforcement
- Policy Rollout 전략
- 운영 시 주의사항

---

# 5주차 - DNS / FQDN / L7 Policy와 Envoy

## 목표

L3/L4를 넘어 L7 Policy가 필요한 이유와
Envoy가 언제 개입하는지 이해한다.

## 핵심 질문

- DNS 기반 Policy는 어떻게 가능한가?
- HTTP Policy는 어떻게 동작하는가?
- eBPF만으로 가능한가?
- Envoy는 언제 필요한가?

## 학습 내용

- DNS Proxy
- FQDN Policy
- toFQDNs
- External API 접근 제어
- L7 Policy
- HTTP Method
- HTTP Path
- HTTP Header
- gRPC Policy
- Node-local Envoy
- eBPF와 Envoy의 역할 구분

---

# 6주차 - Hubble로 네트워크를 관측하는 방법

## 목표

네트워크 장애를 어떻게 분석하고
관측하는지 이해한다.

## 핵심 질문

- 통신이 왜 실패했는가?
- 어떤 Policy 때문에 막혔는가?
- 어느 Node에서 문제가 발생했는가?

## 학습 내용

- Hubble Architecture
- Hubble Relay
- Hubble UI
- Flow Log
- Policy Verdict
- Dropped Packet 분석
- DNS Visibility
- HTTP Visibility
- Service Dependency
- Prometheus
- Grafana 연동

---

# 7주차 - Gateway API와 Ingress

## 목표

Cilium이 North-South Traffic까지 처리할 수 있는지 이해한다.

## 핵심 질문

- Ingress는 무엇인가?
- Gateway API는 왜 등장했는가?
- Cilium은 Ingress Controller를 대체할 수 있는가?

## 학습 내용

- Ingress
- Gateway API
- GatewayClass
- Gateway
- HTTPRoute
- TLS Termination
- Path Routing
- Host Routing
- gRPC Routing
- Envoy Gateway
- ALB / NLB와의 역할 비교

---

# 8주차 - Cilium vs Istio Ambient

## 목표

Istio Ambient와 Cilium Service Mesh를 비교하여
어떤 환경에서 어떤 선택이 적합한지 이해한다.

## 핵심 질문

- Ambient Mesh는 무엇인가?
- ztunnel은 무엇인가?
- Waypoint Proxy는 무엇인가?
- Cilium과 Ambient의 차이는 무엇인가?

## 학습 내용

- Istio Ambient Architecture
- ztunnel
- Waypoint Proxy
- HBONE
- Ambient mTLS
- Cilium Service Mesh
- eBPF vs ztunnel
- Node-local Envoy vs Waypoint
- Traffic Management 비교
- Observability 비교
- Migration 전략

---

# 9주차 - Production 운영 전략

## 목표

실제 운영 환경에서 Cilium을 어떻게 도입해야 하는지 이해한다.

## 핵심 질문

- 운영 시 가장 많이 발생하는 장애는?
- 기존 CNI에서 어떻게 Migration 하는가?
- 운영 체크리스트는 무엇인가?

## 학습 내용

- Egress Gateway
- Transparent Encryption
- Cluster Mesh
- BGP
- Multi Cluster
- Helm 운영
- ArgoCD 연동
- GitOps
- Upgrade 전략
- Rollback 전략
- NetworkPolicy Rollout
- 장애 대응 전략
- Best Practice

---

# 전체 흐름

```text
1주차
왜 Cilium인가?
        │
        ▼
2주차
CNI와 Kubernetes Networking
        │
        ▼
3주차
eBPF Datapath & kube-proxy Replacement
        │
        ▼
4주차
Network Policy Enforcement
        │
        ▼
5주차
DNS / FQDN / L7 Policy & Envoy
        │
        ▼
6주차
Hubble Observability
        │
        ▼
7주차
Gateway API & Ingress
        │
        ▼
8주차
Cilium vs Istio Ambient
        │
        ▼
9주차
Production 운영 전략
```

## 최종 목표

스터디가 끝나면 다음 질문에 답할 수 있어야 한다.

- Kubernetes Networking은 어떻게 동작하는가?
- CNI는 어떤 역할을 하는가?
- Cilium은 eBPF를 어디에 사용하는가?
- kube-proxy 없이 Service Routing이 가능한 이유는?
- NetworkPolicy는 어떻게 강제되는가?
- Envoy는 언제 필요한가?
- Hubble은 무엇을 관측하는가?
- Gateway API는 왜 필요한가?
- Istio Ambient와 Cilium은 어떻게 다른가?
- 우리 서비스에 Cilium을 도입한다면 어떤 기능을 사용할 것인가?