# Chapter 15: Automatic Scaling 발표 대본

**총 발표 시간**: 약 28분 30초 (Q&A 제외) / 슬라이드 32장
**대상 청중**: K8s 기본 개념(Pod, Deployment, requests/limits) 알고 있는 개발자
**핵심 메시지**: 오토스케일링은 **누가 · 무엇을 보고 · 무엇을 조절하는가**로 정리된다. HPA=개수, VPA=자원, CA/Karpenter=노드. 책(2017)과 현실(2024+)의 간극도 같이 짚는다.

**슬라이드 조작**: ←/→ 또는 Space로 이동, `F`로 전체화면, 하단 버튼 클릭도 가능. URL 뒤 `#13`처럼 붙이면 해당 슬라이드로 바로 점프.

---

## 슬라이드 1: 표지 (Chapter 15 / Automatic Scaling)

**예상 시간**: 30초

안녕하세요. 오늘은 Kubernetes in Action 15장, "Automatic Scaling of Pods and Cluster Nodes"를 다룹니다. 부하에 따라 Pod과 노드를 자동으로 늘리고 줄이는 법이에요.

이 챕터는 결국 세 가지 질문으로 압축됩니다. **누가** 스케일을 조절하는가, **무엇을 보고** 판단하는가, 그리고 **무엇을** 조절하는가. 이 세 질문을 따라가면 HPA, VPA, Cluster Autoscaler가 자연스럽게 제자리를 찾습니다.

**다음 슬라이드 연결**: "먼저 오늘 다룰 세 축을 한 장으로 잡고 시작하겠습니다."

---

## 슬라이드 2: 오늘의 세 축 (HPA / VPA / CA)

**예상 시간**: 1분

이 표 한 장만 머리에 남기셔도 됩니다. **HPA는 가로, VPA는 세로, CA는 노드**입니다.

HPA(Horizontal Pod Autoscaler)는 Pod의 **개수**를 조절합니다. replica를 올리고 내리죠. VPA(Vertical Pod Autoscaler)는 Pod 하나의 **크기**, 즉 requests와 limits를 조절합니다. 단, VPA는 코어 내장이 아니라 애드온이에요. Cluster Autoscaler는 Pod이 아니라 **노드 개수**를 조절합니다.

여기서 미리 못 박을 게 하나 있습니다. HPA와 CA는 **협력** 관계예요. Pod이 늘어나서 들어갈 자리가 없으면 노드가 늘어나죠. 반면 HPA와 VPA는 같은 자원을 보면 **충돌**합니다. 이 협력과 충돌 구도가 오늘 발표의 뼈대입니다.

**강조**: HPA=개수, VPA=자원, CA=노드 / HPA↔CA 협력, HPA↔VPA 충돌
**다음 슬라이드 연결**: "그 전에, 스케일링의 가장 기본인 수평 대 수직부터 짚겠습니다."

---

## 슬라이드 3: 섹션 1 — 수평 vs 수직 확장

**예상 시간**: 20초

첫 번째 섹션입니다. 수평이냐 수직이냐는 쿠버네티스 이전부터 모든 시스템에 공통이던 두 방향이에요. 이 개념을 깔고 가야 HPA와 VPA가 왜 갈라지는지 보입니다.

**다음 슬라이드 연결**: "먼저 수직 확장부터."

---

## 슬라이드 4: 수직 확장 — 기계를 더 키운다

**예상 시간**: 1분

수직 확장은 말 그대로 기계 한 대를 더 키우는 겁니다. 4코어 16기가짜리를 16코어 64기가로 바꾸는 식이죠. DB를 RDS 인스턴스 클래스 업그레이드하는 게 전형적인 예입니다.

장점은 **단순함**입니다. 코드를 그대로 두고 하드웨어만 키우면 되니까 분산 복잡성이 없어요. 그래서 stateful한 RDB에 잘 맞습니다.

단점은 명확합니다. 하드웨어에는 **상한**이 있고, 한 대뿐이라 **SPOF**, 단일 장애점이 됩니다. 보통 교체하려면 재부팅이나 다운타임이 따르고, 고사양으로 갈수록 비용이 급격히 뛰어요.

**다음 슬라이드 연결**: "반대 방향, 수평 확장을 보겠습니다."

---

## 슬라이드 5: 수평 확장 — 기계를 더 늘린다

**예상 시간**: 1분

수평 확장은 같은 역할의 인스턴스를 여러 대로 늘리고 앞에 로드밸런서를 두는 방식입니다. 웹 서버 한 대를 열 대로 늘리는 거죠.

장점은 **거의 선형으로 확장**된다는 점, 그리고 한 대가 죽어도 나머지가 받아주는 **고가용성**입니다. 범용 장비를 쓰니 클라우드와도 잘 맞고요.

단점은 앱이 **무상태**라는 전제가 필요하다는 겁니다. 로드밸런서, 데이터 일관성, 네트워크 같은 분산의 복잡성이 따라옵니다. DB는 보통 read replica나 샤딩으로 풀고요.

**강조**: 클라우드 네이티브가 기본으로 선호하는 방향이 바로 이 수평입니다.
**다음 슬라이드 연결**: "둘을 표로 비교하면 선택 기준이 분명해집니다."

---

## 슬라이드 6: 핵심 트레이드오프

**예상 시간**: 1분

이 표가 수평과 수직의 모든 차이를 담고 있습니다. 상한은 수직이 하드웨어 한계, 수평은 사실상 무제한. 가용성은 수직이 SPOF, 수평이 HA. 복잡성은 수직이 낮고 수평이 높습니다.

한 줄로 정리하면 이렇습니다. 클라우드 네이티브는 **수평을 선호**하지만, DB 같은 stateful은 여전히 수직이 1차 선택지예요. 그래서 쿠버네티스는 둘 다 제공합니다. HPA로 수평을, VPA로 수직을요.

**다음 슬라이드 연결**: "이제 Pod 단위 스케일링으로 들어갑니다."

---

## 슬라이드 7: 섹션 2 — Pod 단위 스케일링

**예상 시간**: 20초

두 번째 섹션입니다. Pod 자체를 조절하는 두 방향, 수평인 HPA와 수직인 VPA를 봅니다. 분량상 HPA가 핵심이에요.

**다음 슬라이드 연결**: "HPA 컨트롤러가 대체 어디에 사는지부터."

---

## 슬라이드 8: HPA 컨트롤러는 어디에 있나

**예상 시간**: 1분

HPA를 별도의 데몬이나 Pod이라고 생각하기 쉬운데, 아닙니다. HPA는 **kube-controller-manager 안에서 도는 컨트롤 루프 하나**예요.

이 루프가 기본 15초마다 세 가지를 합니다. 첫째 메트릭을 조회하고, 둘째 필요한 replica 수를 계산하고, 셋째 대상의 **scale 서브리소스**를 수정합니다. Deployment나 ReplicaSet, StatefulSet의 scale을 건드리는 거죠. 주기는 `--horizontal-pod-autoscaler-sync-period` 플래그로 바뀝니다.

API는 autoscaling v1, v2가 있고 이건 apiserver에 내장되어 있습니다. 즉 HPA 자체는 코어예요.

**강조**: HPA = 별도 Pod이 아니라 컨트롤 루프 하나, scale 서브리소스를 수정
**다음 슬라이드 연결**: "그럼 이 루프가 보는 메트릭은 어디서 오는 걸까요?"

---

## 슬라이드 9: Pod 메트릭은 어떻게 수집되나 (원천)

**예상 시간**: 1분 15초

메트릭의 **원천은 노드 커널의 cgroup**입니다. 컨테이너가 실행되면 커널이 CPU·메모리 사용량을 cgroup에 기록해요.

이걸 위로 올리는 경로가 이 화살표입니다. **cAdvisor**가 cgroup 통계를 읽습니다. 중요한 건 cAdvisor가 별도 설치물이 아니라 **kubelet에 내장**되어 있다는 점이에요. 그다음 kubelet이 `/metrics/resource` 엔드포인트로 노출하고, **metrics-server**가 15초마다 이걸 긁어갑니다.

리눅스에서는 cgroup 기반이고, 그 외 환경에서는 런타임의 CRI Container Metrics를 씁니다.

**강조**: 원천은 cgroup, cAdvisor는 kubelet 내장
**다음 슬라이드 연결**: "그런데 왜 하필 메트릭 엔드포인트가 kubelet에 붙어 있을까요? kubelet이 뭘 하는 놈인지 보면 답이 나옵니다."

---

## 슬라이드 10: kubelet 구성요소 — cAdvisor는 일부일 뿐

**예상 시간**: 1분

cAdvisor가 kubelet 안에 있다고 했는데, cAdvisor는 kubelet의 아주 작은 일부일 뿐입니다.

왼쪽이 오늘 주제인 메트릭 관련 부분이에요. cAdvisor가 컨테이너별 CPU·메모리를 수집하고, Summary API가 요약을 주고, `/metrics/resource`를 metrics-server가 긁습니다.

오른쪽이 kubelet이 하는 나머지 일들입니다. **SyncLoop**으로 원하는 Pod 상태와 실제를 맞추고, **PLEG**으로 컨테이너 생성·종료 이벤트를 감지하고, **CRI 클라이언트**로 containerd나 CRI-O에 기동 명령을 내립니다. 볼륨, 이미지, 프로브, 상태, 축출, 노드 리스까지 관리하고요.

그러니까 kubelet은 **노드 위 컨테이너의 생사·상태·자원·볼륨을 책임지는 에이전트**이고, cAdvisor는 그 안의 자원 측정 모듈일 뿐입니다. "왜 메트릭 엔드포인트가 kubelet에 있나"의 답이 바로 이거예요.

**다음 슬라이드 연결**: "그런데 책에서는 이 파이프라인이 좀 다르게 그려져 있습니다. Heapster 이야기를 해야 해요."

---

## 슬라이드 11: Heapster의 죽음 → 지금의 파이프라인

**예상 시간**: 1분

책에는 Heapster가 등장합니다. 예전 구조는 kubelet과 cAdvisor의 데이터를 Heapster가 InfluxDB에 모으고, HPA가 그 Heapster를 직접 호출했어요.

문제는 HPA가 **특정 구현에 직접 의존**했다는 겁니다. 결합도가 높고 무거웠죠. 그래서 Heapster는 2019년에 폐기됩니다.

지금 구조는 오른쪽입니다. metrics-server가 kubelet의 `/metrics/resource`를 15초마다 긁어서 **최근값만 메모리에 들고** 있습니다. 저장은 안 해요. 그리고 자신을 APIService로 등록해서 Aggregation Layer를 통해 노출합니다. HPA나 `kubectl top`은 이 표준 경로로 조회하고요.

**강조**: 책의 Heapster는 죽었다. 지금은 metrics-server + Aggregation Layer.
**다음 슬라이드 연결**: "이 구조의 핵심을 콘센트에 비유해서 정리해 보겠습니다."

---

## 슬라이드 12: 인터페이스 · 소켓 · 구현체 — 콘센트 비유

**예상 시간**: 1분 30초

이 구조가 헷갈리기 쉬워서 콘센트로 비유했습니다.

벽이 kube-apiserver입니다. 그 벽에 박힌 **소켓이 Aggregation Layer**예요. 이건 apiserver에 내장되어 있습니다. 소켓의 **규격이 metrics.k8s.io**라는 API입니다. 그리고 거기 꽂는 **플러그가 metrics-server**고요. 이건 애드온이라 직접 설치해야 합니다.

핵심은 두 가지입니다. 첫째, 소켓은 항상 있지만 **플러그인 metrics-server를 안 깔면** `kubectl top`도 HPA도 전부 `<unknown>`이 뜹니다. 둘째, **HPA가 코어인 이유**가 여기서 나와요. HPA는 metrics.k8s.io라는 **인터페이스에 의존**하지, metrics-server라는 구현에 의존하지 않습니다. 그래서 구현체를 갈아끼워도 HPA는 그대로예요.

**강조**: 소켓=Aggregation Layer(내장), 규격=metrics.k8s.io, 플러그=metrics-server(애드온)
**다음 슬라이드 연결**: "이제 HPA가 실제로 replica를 어떻게 계산하는지 공식을 보겠습니다."

---

## 슬라이드 13: HPA 계산식

**예상 시간**: 1분 30초

공식은 의외로 간단합니다. **desiredReplicas = ceil(currentReplicas × 현재메트릭 / 목표메트릭)**.

예를 들어 지금 replica가 3개인데 현재 CPU가 90%, 목표가 50%라면, 3 곱하기 90 나누기 50은 5.4, 올림하면 6개가 됩니다.

여기서 가장 중요한 포인트. CPU 사용률은 노드 기준이 아니라 컨테이너의 **requests 대비 퍼센트**입니다. 그래서 **requests가 없으면 계산 자체가 불가능**해요. 14장에서 requests를 강조한 게 여기로 직결됩니다.

그리고 **tolerance가 10%** 있습니다. 비율이 0.9에서 1.1 사이면 변동을 안 줘요. 또 Not-Ready Pod이나 메트릭이 빠진 Pod은 보수적으로 보정합니다. 그래서 "공식대로면 6인데 실제로는 5"인 경우도 정상이에요.

**강조**: CPU는 requests 대비 %, requests 필수, tolerance 10%
**다음 슬라이드 연결**: "CPU 말고 어떤 메트릭으로 스케일할 수 있는지 보겠습니다."

---

## 슬라이드 14: 메트릭 종류 3가지

**예상 시간**: 1분

HPA가 쓸 수 있는 메트릭은 크게 셋입니다.

**Resource**는 metrics-server가 주는 CPU와 메모리. 가장 기본이죠. **Pods나 Object**는 custom.metrics.k8s.io를 통해 Prometheus Adapter로 들어오는 커스텀 메트릭으로, 초당 요청 수나 큐 길이 같은 거예요. **External**은 external.metrics.k8s.io로, KEDA가 가져오는 SQS나 PubSub 메시지 수 같은 클러스터 외부 신호입니다.

여러 메트릭을 동시에 지정하면 **각각 계산해서 가장 큰 replica를 채택**합니다. 안전한 쪽으로 가는 거죠. CPU보다 QPS나 큐 길이, p99 지연 같은 비즈니스 신호로 스케일하면 훨씬 정확합니다.

**다음 슬라이드 연결**: "그런데 메트릭이 출렁이면 스케일이 진동할 수 있습니다. 이걸 막는 게 behavior예요."

---

## 슬라이드 15: 스케일링 안정화 — flapping 방지

**예상 시간**: 1분

메트릭이 경계 근처에서 출렁이면 Pod이 늘었다 줄었다 진동합니다. 이걸 flapping이라고 하고, autoscaling v2의 `behavior`로 제어해요.

기본 철학이 비대칭입니다. **scale-up은 즉시** 합니다. 부하가 오면 빨리 대응해야 하니까요. 반대로 **scale-down은 기본 5분 안정화 윈도우**를 둡니다. 보수적으로 천천히 줄여서 진동을 막는 거예요.

코드를 키별로 보겠습니다. `behavior` 아래는 `scaleUp`과 `scaleDown`을 **방향별로 따로** 설정합니다. `stabilizationWindowSeconds`는 그 시간 동안의 추천값을 모아서, 축소는 **최댓값**을, 확대는 **최솟값**을 채택해 순간 변동을 무시하는 값이에요. 그래서 축소는 300, 즉 5분을 보수적으로 두고, 확대는 0으로 즉시 반응합니다.

`policies`는 변경 **속도의 상한**입니다. `type`이 `Pods`면 절대 개수, `Percent`면 현재 replica 대비 퍼센트예요. `value`가 그 상한 크기고, `periodSeconds`는 그 값을 "몇 초당"으로 적용할지의 시간창입니다. 그래서 이 예시는 **축소는 60초당 현재의 50%까지만, 확대는 60초당 최대 4개까지만**이라는 뜻이에요. 정책이 여러 개면 `selectPolicy`로 고르는데, 기본값은 가장 큰 변화를 허용하는 `Max`이고, `Disabled`로 두면 그 방향 스케일링을 아예 막습니다.

**강조**: 올릴 땐 빠르게, 내릴 땐 보수적으로
**다음 슬라이드 연결**: "여기까지가 HPA였고, 이제 수직 방향 VPA로 넘어갑니다."

---

## 슬라이드 16: 섹션 — VPA

**예상 시간**: 20초

VPA, Vertical Pod Autoscaler입니다. HPA가 개수를 늘린다면, VPA는 Pod 하나의 requests와 limits를 실사용량에 맞춰 자동으로 조정합니다.

**다음 슬라이드 연결**: "먼저 VPA가 코어가 아니라는 점과 구조부터."

---

## 슬라이드 17: 코어 빌트인 아님 + 3 컴포넌트

**예상 시간**: 1분

먼저 분명히 할 것. **VPA는 코어 내장이 아닙니다.** kubernetes/autoscaler 레포의 별도 애드온이라 직접 설치해야 해요. API 그룹은 autoscaling.k8s.io입니다.

구성은 세 컴포넌트예요. **Recommender**가 사용량을 분석해서 적정 requests 추천값을 계산합니다. **Updater**는 추천값과 동떨어진 기존 Pod을 축출해서 재생성을 유도하고요. **Admission Controller**는 새로 뜨는 Pod에 추천값을 주입합니다. mutating webhook이죠.

**강조**: VPA는 애드온(코어 X), Recommender·Updater·Admission Controller
**다음 슬라이드 연결**: "이 Updater가 얼마나 공격적으로 개입하느냐를 updateMode로 정합니다."

---

## 슬라이드 18: updateMode 4가지

**예상 시간**: 50초

VPA의 updateMode는 넷입니다.

**Off**는 추천만 하고 실제로는 안 바꿉니다. 가장 안전하고, 뒤에서 보겠지만 HPA와 병행할 때 이 모드를 씁니다. **Initial**은 생성 시점에만 주입해서 재시작 부담을 줄여요. **Recreate**는 Pod을 죽이고 새 값으로 다시 만듭니다. 무중단이 아니에요. **Auto**는 현재로선 Recreate와 같지만, 향후 In-place resize와 결합될 예정입니다.

**다음 슬라이드 연결**: "그런데 VPA를 쓸 때 가장 조심해야 할 함정이 있습니다. HPA와의 충돌이에요."

---

## 슬라이드 19: HPA와 VPA의 충돌

**예상 시간**: 1분 15초

오늘 발표에서 가장 중요한 함정입니다. **같은 자원, 즉 CPU나 메모리에 HPA와 VPA를 동시에 쓰면 안 됩니다.**

왜냐면 같은 CPU 신호를 보고 HPA는 "replica를 늘리자" 하고, VPA는 "requests를 늘리자" 합니다. 그런데 requests가 늘면 사용률 퍼센트가 떨어지니 HPA는 다시 줄이려 하고요. 둘이 반대로 반응하면서 시스템이 진동합니다.

그럼 어떻게 같이 쓰냐. 두 가지 조합이 안전해요. 하나는 **HPA는 CPU로, VPA는 Off 모드**로 추천만 받는 것. 다른 하나는 **HPA는 커스텀 QPS 같은 다른 신호로, VPA는 CPU·메모리**를 맡는 것. 핵심은 같은 자원을 두 컨트롤러가 동시에 건드리지 않게 하는 겁니다.

**강조**: 같은 자원에 HPA+VPA 동시 사용 금지
**다음 슬라이드 연결**: "VPA의 재시작 문제는 미래 기술로 풀리고 있습니다."

---

## 슬라이드 20: 무중단 수직 스케일링의 미래

**예상 시간**: 50초

전통적 VPA의 약점은 requests를 바꾸려면 Pod을 재시작해야 한다는 거였습니다.

그런데 코어에 **In-place Pod Resize**가 들어왔어요. resizePolicy로 지정하고, 1.27에서 알파, 1.33에서 베타입니다. 이게 VPA와 결합되면 **재시작 없이** 자원을 조정할 수 있습니다.

포인트는 이겁니다. 코어에 들어온 건 VPA가 아니라, **자원을 재시작 없이 바꾸는 In-place Resize**예요. VPA 자체는 여전히 애드온입니다.

**다음 슬라이드 연결**: "이제 마지막 레이어, 노드 단위로 올라갑니다."

---

## 슬라이드 21: 섹션 3 — Node 단위 스케일링

**예상 시간**: 20초

세 번째 섹션입니다. HPA로 Pod을 늘렸는데 **들어갈 노드가 없으면** 어떻게 될까요? 노드 자체를 늘리는 레이어가 필요합니다.

**다음 슬라이드 연결**: "그 일을 하는 게 Cluster Autoscaler입니다."

---

## 슬라이드 22: Cluster Autoscaler (CA)

**예상 시간**: 1분

Cluster Autoscaler는 노드 개수를 조절합니다.

Scale up은 이렇게 작동해요. Pod이 자원 부족으로 스케줄에 실패해서 **Pending** 상태가 되면, CA가 노드 그룹에 노드를 추가합니다. Scale down은 반대로 노드 활용률이 낮고 그 위 Pod을 다른 데로 옮길 수 있으면, drain하고 노드를 제거하고요.

전체 흐름은 이렇습니다. HPA가 replica를 늘림 → Pod이 노드 부족으로 Pending → CA가 노드 추가 → Pod이 스케줄됨. HPA와 CA의 협력이 바로 이거예요.

실무 팁 하나. **축소를 막는 요소**들이 비용 누수의 단골입니다. 빡빡한 PodDisruptionBudget, local storage를 쓰는 Pod, safe-to-evict false 어노테이션, 시스템 Pod 같은 것들이 노드를 못 줄이게 잡고 있어요.

**다음 슬라이드 연결**: "그런데 요즘은 CA의 대안으로 Karpenter가 많이 뜨고 있습니다."

---

## 슬라이드 23: Karpenter vs Cluster Autoscaler

**예상 시간**: 1분

Karpenter와 CA를 비교해 보겠습니다.

단위가 다릅니다. CA는 **미리 정의된 노드 그룹, 즉 ASG 안에서** 개수를 더하고 뺍니다. Karpenter는 그룹 없이 **Pending Pod에 딱 맞는 인스턴스를 즉석에서 골라** 띄워요. 그래서 속도가 CA는 ASG를 경유하느라 느리고, Karpenter는 직접 프로비저닝해서 빠릅니다. 비용도 Karpenter가 spot이나 인스턴스 타입을 섞어서 최적화할 수 있고요.

대신 범위는 CA가 모든 클라우드와 온프렘을 지원하는 반면, Karpenter는 주로 AWS입니다. 지금 다른 클라우드로 확산 중이고요.

**다음 슬라이드 연결**: "그런데 왜 Karpenter가 더 빠를까요? 이게 단순한 구현 차이가 아니라 근본적인 이유가 있습니다."

---

## 슬라이드 24: 왜 Karpenter가 더 빠른가 — 근본 2가지

**예상 시간**: 1분 30초

이 차이를 표면적으로 "직접 호출해서 빠르다"로만 알면 아깝습니다. 근본 원인이 둘이에요.

첫째, **프로비저닝의 간접성**입니다. 그림 위쪽을 보면 CA는 ASG의 desired 값을 +1만 합니다. 실제 EC2 기동은 ASG에 **위임**해요. 제어 루프가 두 개죠. 반면 Karpenter는 EC2 CreateFleet API를 **직접** 호출합니다. 루프가 하나예요.

둘째, **노드 그룹이 고정 템플릿**이라는 점입니다. CA는 미리 정의된 그룹 중에서 **고르기만** 합니다. 딱 맞는 게 없으면 재시도하고요. Karpenter는 Pending Pod의 requests를 보고 **최적 인스턴스 타입을 즉석에서 계산**합니다.

그런데 여기서 멈추지 말고 한 단계 더 들어가면, CA가 왜 이렇게 만들어졌냐는 거예요. CA는 **모든 클라우드에서 동작하는 이식성**을 위해 노드 그룹이라는 추상화를 거칩니다. 그 대가로 2단 루프와 템플릿을 떠안은 거죠. 즉 **Karpenter의 속도라는 이득과 AWS 종속이라는 비용은 같은 원인의 양면**입니다. 추상화를 버려서 빨라진 거예요.

**강조**: 속도(이득) = 이식성 상실(비용), 같은 원인의 양면
**다음 슬라이드 연결**: "그럼 이걸 실제로 어떻게 도입하고, Pod을 늘려서 노드가 따라 늘게 하는지 명령어로 보겠습니다."

---

## 슬라이드 25: Karpenter 도입 — 설치 & NodePool

**예상 시간**: 1분 15초

Karpenter 도입은 두 단계입니다. 먼저 **Helm으로 컨트롤러를 설치**해요. clusterName과 interruption 큐 정도만 지정하면 되고, IAM 역할·노드 역할·서브넷 태그는 eksctl이나 CloudFormation으로 미리 깔아둡니다. 컨트롤러 자신은 Karpenter가 못 띄우니까 관리형 노드그룹이나 Fargate에 한두 개만 올려둬요.

두 번째가 핵심인데, **노드그룹을 안 만듭니다.** 대신 CRD 두 개를 선언해요. **NodePool**은 "무엇을" — 어떤 노드를 허용할지입니다. capacity-type을 spot과 on-demand로 섞고, cpu 합계 상한을 1000으로 걸어 폭주를 막고, disruption 정책으로 비거나 저활용인 노드를 자동 정리하게 합니다. **EC2NodeClass**는 "어떻게" — 그 노드를 AWS에서 실제로 어떻게 만들지예요. AMI, 서브넷, 보안그룹, 노드 IAM 역할을 태그로 찾아옵니다.

**강조**: 노드그룹을 미리 안 만들고 제약만 준다 — 그게 Karpenter 즉석 선택의 출발점
**다음 슬라이드 연결**: "그럼 이 위에서 Pod을 늘리면 노드가 어떻게 따라오는지 실제 명령어로 보겠습니다."

---

## 슬라이드 26: Pod 늘리고 줄이기 → 노드 자동 증감

**예상 시간**: 1분 15초

이제 실습입니다. inflate라는 데모 Deployment를 만듭니다. pause 컨테이너라 아무 일도 안 하고 자리만 차지하는데, **requests를 1코어**로 줍니다. 이 requests가 중요해요 — 스케줄러가 "이 Pod이 들어갈 자리"를 requests로 계산하니까요. 13번 슬라이드에서 본 그 requests입니다.

늘리는 건 한 줄이에요. `kubectl scale`로 replica를 20으로 올립니다. 그러면 노드에 자리가 부족해 Pod들이 **Pending**에 빠지고, 그 Pending이 곧 **Karpenter의 입력**이 됩니다. Karpenter가 20개를 담을 최적 인스턴스를 골라 띄워요. 줄일 때도 한 줄, replica를 0으로 내리면 노드가 비고 disruption 정책에 따라 빈 노드를 정리합니다.

관찰은 오른쪽 명령어로 합니다. `get pods -w`로 Pending이 Running 되는 걸 보고, `get nodeclaims`로 Karpenter가 만든 노드 요청을, `get nodes -w`로 노드 증감을 봅니다. **eks-node-viewer**는 비용과 빈패킹을 실시간으로 보여줘서 데모할 때 그림이 제일 좋아요.

핵심은, 여기선 제가 `kubectl scale`로 직접 replica를 바꿨지만 **실제 운영에선 그걸 HPA가 부하 보고 자동으로** 합니다. HPA가 Pod을 늘리고 Karpenter가 노드를 받쳐주는 게 다음 장에서 볼 세 층위 협력이에요.

**강조**: replica 변경이 트리거, Pending이 Karpenter 입력, requests 필수
**다음 슬라이드 연결**: "이 협력을 전체 그림으로 정리해 보겠습니다."

---

## 슬라이드 27: 세 층위의 협력 흐름

**예상 시간**: 1분

전체 그림입니다. 부하가 올라가면 **HPA가 Pod 개수를 늘립니다**. 그런데 늘어난 Pod이 들어갈 자리가 없으면 **Pending**이 되죠. 그러면 **CA나 Karpenter가 노드를 늘리고**, 비로소 Pod이 스케줄에 성공합니다.

VPA는 이 흐름의 옆에서 Pod당 requests를 보정하는 역할이에요.

한 문장으로 정리하면. **HPA와 CA는 협력합니다.** Pod이 늘면 노드가 따라 늘죠. 반면 **HPA와 VPA는 같은 자원을 보면 충돌**합니다. 이 협력과 충돌 구도가 오늘의 핵심 뼈대였습니다.

**강조**: HPA↔CA 협력, HPA↔VPA(동일 자원) 충돌
**다음 슬라이드 연결**: "여기서 제가 실무에서 받은 질문 하나를 데모로 풀어보겠습니다. ArgoCD로 노드 증설을 볼 수 있냐는 거였어요."

---

## 슬라이드 28: ArgoCD로 Karpenter 노드 증설 보기

**예상 시간**: 1분 15초

"AWS에서 Karpenter로 노드가 늘어나는 걸 ArgoCD로 볼 수 있냐"는 질문을 받았는데, 여기서 **도구 역할 분리**가 핵심입니다.

ArgoCD는 노드를 보는 관측 도구가 아니라 **GitOps 배포기**예요. 노드 증설은 런타임에서 일어나는 일이라 ArgoCD의 Application tree에는 안 들어옵니다.

그럼 어떻게 데모하냐. 흐름은 이렇습니다. Git에서 replicas를 올려 커밋 → **ArgoCD가 sync** → Pod이 Pending → **Karpenter**가 감지 → **EC2 노드 생성**. 즉 ArgoCD는 **트리거** 역할이에요. replica를 commit으로 올리고, NodePool CRD를 시각화하는 정도까지입니다.

실제 **노드 증설 관찰**은 다른 도구로 합니다. AWS 공식 CLI인 **eks-node-viewer**가 노드 bin-packing과 비용을 실시간으로 보여줘서 Karpenter 데모 표준이고요, 아니면 `kubectl get nodes -w`나 Grafana, Prometheus를 씁니다.

**강조**: ArgoCD=트리거/배포, 노드 관찰=eks-node-viewer/kubectl -w/Grafana
**다음 슬라이드 연결**: "이제 책과 현실의 간극을 한 표로 정리하겠습니다."

---

## 슬라이드 29: 책 vs 현실

**예상 시간**: 1분

이 책이 2017년 1판이라 지금과 차이가 꽤 큽니다.

메트릭은 책의 Heapster가 2019년에 폐기되고 metrics-server와 Prometheus Adapter로 바뀌었습니다. HPA는 v1, CPU만 되던 게 **v2**로 가면서 메모리·커스텀·External에 behavior까지 생겼고요. 책이 "계획 중"이라던 앱 idling은 **코어에 끝내 안 들어왔습니다.** 진짜 idling은 Knative나 KEDA가 합니다. VPA는 코어가 아니라 **애드온으로 실현**됐고, In-place Resize와 결합 중이에요. scale-to-zero는 책에선 불가능했는데 지금은 **KEDA**가 합니다. 노드는 Cluster Autoscaler만 있던 게 **Karpenter**라는 대안이 떴고요.

**강조**: 책의 "계획 중"들이 코어가 아니라 애드온 생태계로 실현됐다
**다음 슬라이드 연결**: "그 중 scale-to-zero를 가능하게 한 KEDA를 잠깐 보겠습니다."

---

## 슬라이드 30: KEDA — 이벤트 기반 + scale-to-zero

**예상 시간**: 1분

기본 HPA는 minReplicas를 1 밑으로 못 내립니다. 항상 최소 한 개는 떠 있어야 해요. KEDA는 이 한계를 깹니다.

ScaledObject를 보면 minReplicaCount가 0이에요. 이벤트가 없으면 **0으로 완전히 축소**했다가, 이벤트가 오면 Pod을 깨우고 이후는 HPA에 위임합니다. 예시는 Kafka 토픽의 lag이 100을 넘으면 깨우는 설정이고요.

트리거 종류가 Kafka lag, SQS depth, RabbitMQ, cron 등 60개가 넘습니다. 이벤트 기반 워크로드, 특히 컨슈머에 잘 맞아요.

**강조**: KEDA = 0↔N scale-to-zero, 60+ scaler
**다음 슬라이드 연결**: "오늘 내용을 다섯 줄로 정리하겠습니다."

---

## 슬라이드 31: Key Takeaways

**예상 시간**: 1분

다섯 가지만 가져가시면 됩니다.

하나, **HPA는 가로 개수, VPA는 세로 자원, CA는 노드** — 세 단어로 구조가 잡힙니다. 둘, HPA 공식은 replica 곱하기 현재 나누기 목표의 올림이고, CPU는 **requests 대비**라서 requests가 필수예요. 14장과 직결됩니다. 셋, **HPA와 CA는 협력, HPA와 VPA는 충돌** — VPA는 Off 추천 모드로 병행하세요. 넷, metrics-server는 **애드온**이라 안 깔면 top도 HPA도 unknown입니다. 다섯, flapping은 behavior로, scale-to-zero는 KEDA로, 노드는 CA나 Karpenter로 푼다.

**다음 슬라이드 연결**: "여기까지입니다. 질문 받겠습니다."

---

## 슬라이드 32: Q&A

**예상 시간**: 15초

들어주셔서 감사합니다. HPA, VPA, Cluster Autoscaler, Karpenter, KEDA 어느 거든 질문 주세요.

---

## 부록: 예상 Q&A

**Q. requests를 안 잡으면 HPA가 정말 아예 안 도나요?**
CPU 기반 HPA는 사용률을 requests 대비로 계산하기 때문에 requests가 없으면 타깃을 계산할 수 없어 `<unknown>`이 뜨고 스케일하지 않습니다. 절대값 메트릭(`AverageValue`)이나 커스텀/External 메트릭은 requests 없이도 동작할 수 있습니다.

**Q. HPA랑 VPA를 정말 같이 못 쓰나요?**
같은 자원(예: 둘 다 CPU)만 금지입니다. HPA는 QPS 같은 커스텀 메트릭, VPA는 CPU·메모리처럼 **다른 신호**를 맡기거나, VPA를 `Off`(추천만)로 두면 함께 쓸 수 있습니다.

**Q. Karpenter가 항상 CA보다 낫나요?**
속도·비용 최적화는 Karpenter가 유리하지만, 멀티클라우드나 온프렘이면 CA가 사실상 표준입니다. Karpenter의 빠름은 AWS 종속이라는 비용과 한 묶음이에요(슬라이드 24).

**Q. metrics-server가 Prometheus를 대체하나요?**
아닙니다. metrics-server는 HPA·`kubectl top`용으로 **최근값만** 메모리에 두는 경량 컴포넌트입니다. 시계열 저장·대시보드·알람은 Prometheus의 몫이고, 커스텀 메트릭 HPA는 Prometheus Adapter를 통해 연결합니다.
