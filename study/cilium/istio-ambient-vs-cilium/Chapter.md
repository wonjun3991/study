1. TLS에 대해서
    - SHA-1 알고리즘 강제 때문에 1.1 Deprecated
    - 키 교환을 위한 통신 추가 때문에 1.2 -> 1.3
2. TLS 통신 방법
    - client hello
    - server hello
    - mTLS
3. Istio
    - Service Mesh의 구현체
    - k8s Add On
    - istiod
4. Istio Ambient mode
    - ztunnel
    - waypoint
5. Istio Ambient mode vs Cilium
    - CNI 사용 여부
    - 성능 상의 차이
    - 설치 방법과 관리 방법의 차이
    - 동작하는 방식들의 차이 L4, L7 
    - Cilium은 L3 도 지원하는데 이러한 부분에서의 차이