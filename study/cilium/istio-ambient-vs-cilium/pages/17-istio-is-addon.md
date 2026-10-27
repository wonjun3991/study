# Istio는 k8s Add-On이다

<div class="stack" data-stack="CRD — networking · security · telemetry · extensions.istio.io 4개 API 그룹|Webhook — Mutating(사이드카 주입) · Validating(설정 검증)|istio-system 네임스페이스 — istiod Deployment|전제 조건 — 이미 동작하는 CNI" data-accent="cyan|green|gold|red"></div>

<!--
"애드온"이라는 말이 추상적이라 실제로 무엇이 설치되는지로 풀었습니다.
맨 위, CRD입니다. API 그룹이 네 개입니다. networking에 VirtualService와 DestinationRule, security에 AuthorizationPolicy와 PeerAuthentication이 들어갑니다. 쿠버네티스 API를 확장하는 방식입니다.
그 다음 웹훅이 두 종류. Mutating이 사이드카를 파드 스펙에 끼워넣고, Validating이 잘못된 설정을 거부합니다.
그리고 istio-system에 istiod 파드 하나.
맨 아래 빨간 층이 오늘 강조하고 싶은 부분입니다. Istio는 파드에 IP를 주지 않습니다. Calico나 Cilium이 이미 그 일을 해놓은 상태를 가정합니다.
이게 5장에서 Cilium과 비교할 첫 번째 항목입니다.
-->
