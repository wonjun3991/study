# ① 실제로 뜨는 리소스 - Cilium

**기본 설치** - 이 셋이 전부다

| 오브젝트 | 종류 | 개수 |
|---|---|---|
| `cilium` (agent) | **DaemonSet** | 노드 수 |
| `cilium-operator` | **Deployment** | 2 |
| `cilium-envoy` | **DaemonSet** | 노드 수 - **1.16부터 신규 설치 기본값** |

**선택 (opt-in)** - 켜야 뜬다

| 오브젝트 | 종류 | 조건 |
|---|---|---|
| `ztunnel-cilium` | DaemonSet | `encryption.type: ztunnel` - **1.19 Beta** |

`cilium-envoy`는 예전엔 에이전트 파드 안의 프로세스였다. 지금은 별도 DaemonSet이 기본이고 **L7을 쓰든 안 쓰든 노드마다 하나 뜬다.**

<!--
Cilium 쪽입니다. 기본과 선택을 나눠서 적었습니다.

위 표가 기본 설치입니다. 셋뿐이에요. 에이전트가 DaemonSet, 오퍼레이터가 Deployment 두 개, 그리고 envoy가 DaemonSet입니다.

세 번째 줄을 강조하고 싶습니다. cilium-envoy는 1.16부터 신규 설치의 기본값입니다. 옵션이 아니라 기본이에요. 예전에는 에이전트 파드 안에서 프로세스로 돌았는데, 수명주기를 따로 관리하려고 별도 DaemonSet으로 분리했습니다. 그래서 L7 정책을 하나도 안 써도 노드마다 하나씩 떠 있습니다.

아래 표가 선택입니다. ztunnel은 켜야 뜹니다. encryption.type을 ztunnel로 줘야 하고, 1.19에서 들어온 Beta예요. 기본 설치에는 없습니다.

이 구분이 다음 장 숫자에서 중요해집니다. 기본만 세는 것과 ztunnel을 켠 걸 세는 게 다르니까요.
-->
