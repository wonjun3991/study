# Jira REST API (curl-based)

Jira REST API v2를 curl로 직접 호출하는 패턴. Atlassian MCP 대신 사용한다.

## 환경변수

사용자가 `~/.zshrc` 또는 `~/.bashrc`에 설정:

```bash
export JIRA_BASE_URL="https://omelet.atlassian.net"
export JIRA_EMAIL="user@omelet.ai"
export JIRA_API_TOKEN="<atlassian-api-token>"
```

API 토큰 생성: https://id.atlassian.com/manage-profile/security/api-tokens

## 인증 테스트

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "$JIRA_BASE_URL/rest/api/2/myself" | jq .displayName
```

## API 패턴

### 1. 이슈 조회 (GET)

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "$JIRA_BASE_URL/rest/api/2/issue/TMS-481" | jq .
```

특정 필드만 조회:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "$JIRA_BASE_URL/rest/api/2/issue/TMS-481?fields=summary,status,description" | jq .
```

### 2. 이슈 생성 (POST)

큰 body는 `/tmp/jira-create.json` 임시 파일로 생성 후 전달:

```bash
# Step 1: Write tool로 /tmp/jira-create.json 생성
# Step 2: curl 실행
curl -s -X POST -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$JIRA_BASE_URL/rest/api/2/issue" \
  -d @/tmp/jira-create.json
```

JSON 구조 예시:

```json
{
  "fields": {
    "project": { "key": "TMS" },
    "issuetype": { "name": "Task" },
    "summary": "이슈 제목",
    "description": "위키 마크업으로 작성한 설명",
    "priority": { "name": "Medium" }
  }
}
```

### 3. 이슈 수정 (PUT)

```bash
curl -s -X PUT -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$JIRA_BASE_URL/rest/api/2/issue/TMS-481" \
  -d @/tmp/jira-update.json
```

### 4. 코멘트 추가 (POST)

```bash
curl -s -X POST -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$JIRA_BASE_URL/rest/api/2/issue/TMS-481/comment" \
  -d @/tmp/jira-comment.json
```

JSON 구조:

```json
{
  "body": "코멘트 내용 (위키 마크업 지원)"
}
```

### 5. JQL 검색 (GET)

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "$JIRA_BASE_URL/rest/api/2/search?jql=project%3DTMS+AND+key%3DTMS-481"
```

### 6. 트랜지션 조회 / 실행

```bash
# 가능한 트랜지션 조회
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "$JIRA_BASE_URL/rest/api/2/issue/TMS-481/transitions" | jq .

# 트랜지션 실행
curl -s -X POST -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$JIRA_BASE_URL/rest/api/2/issue/TMS-481/transitions" \
  -d '{"transition": {"id": "31"}}'
```

## v2 API 사용 이유

- description 필드에 **위키 마크업** 직접 사용 가능 (마크다운과 유사)
- v3는 ADF(Atlassian Document Format) JSON 필요 → curl로 작성 복잡
- commentBody도 plain text/wiki markup으로 전달 가능

## JSON 생성 패턴

큰 body는 `/tmp/jira-*.json` 임시 파일로 Write tool을 사용하여 생성한 후 `@/tmp/jira-*.json`으로 전달한다.

```bash
# Step 1: Write tool로 /tmp/jira-create.json 생성
# Step 2: curl로 전달
curl -s -X POST -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$JIRA_BASE_URL/rest/api/2/issue" \
  -d @/tmp/jira-create.json
```

## 에러 처리

- **401 Unauthorized**: `JIRA_EMAIL` 또는 `JIRA_API_TOKEN` 확인
- **404 Not Found**: 이슈 키 또는 URL 확인
- **400 Bad Request**: JSON body 형식 확인 (jq로 유효성 검증)

환경변수 미설정 확인:

```bash
[[ -z "$JIRA_BASE_URL" || -z "$JIRA_EMAIL" || -z "$JIRA_API_TOKEN" ]] && \
  echo "ERROR: JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN 환경변수를 설정하세요"
```

## 프로젝트 정보

- **Project Key**: `TMS`
- **Jira URL**: https://omelet.atlassian.net
