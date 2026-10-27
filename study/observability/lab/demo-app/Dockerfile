FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
# opentelemetry-bootstrap: 설치된 라이브러리(fastapi, httpx …)에 맞는 자동 계측 패키지를 추가 설치
RUN pip install --no-cache-dir -r requirements.txt \
 && opentelemetry-bootstrap -a install

COPY main.py .

# opentelemetry-instrument가 SDK 초기화 + 자동 계측을 한 뒤 uvicorn을 실행한다
# (exporter 주소, service.name 등은 Deployment의 OTEL_* 환경변수로 설정)
CMD ["opentelemetry-instrument", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
