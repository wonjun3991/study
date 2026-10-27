"""Observability 실습용 데모 서비스.

같은 이미지를 3개 Deployment로 띄우고 SERVICE_ROLE로 역할을 나눈다.

    loadgen ─▶ gateway /checkout ─▶ order /orders ─▶ payment /pay

계측 방식
- 자동 계측: `opentelemetry-instrument`가 FastAPI(서버 span, http.server.request.duration)와
  httpx(클라이언트 span + traceparent 헤더 전파)를 감싼다. 이 파일에는 그 코드가 없다.
- 수동 계측: 비즈니스 의미가 있는 span(reserve_inventory)과 metric(demo.orders)만 직접 만든다.
- 로그: stdout에 JSON 한 줄로 쓰고 trace_id/span_id를 넣는다.
  OTLP로 보내지 않고, OTel Collector agent가 파일(/var/log/pods)을 읽어 파싱한다.
"""
import asyncio
import json
import logging
import os
import random
import sys

import httpx
from fastapi import FastAPI, HTTPException
from opentelemetry import metrics, trace

ROLE = os.environ.get("SERVICE_ROLE", "gateway")
DOWNSTREAM_URL = os.environ.get("DOWNSTREAM_URL", "")
PAYMENT_SLOW_RATE = float(os.environ.get("PAYMENT_SLOW_RATE", "0.1"))
PAYMENT_ERROR_RATE = float(os.environ.get("PAYMENT_ERROR_RATE", "0.05"))


class JsonFormatter(logging.Formatter):
    """한 줄 JSON 로그. 현재 span이 있으면 trace_id/span_id를 함께 기록한다."""

    def format(self, record: logging.LogRecord) -> str:
        doc = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        ctx = trace.get_current_span().get_span_context()
        if ctx.is_valid:
            doc["trace_id"] = format(ctx.trace_id, "032x")
            doc["span_id"] = format(ctx.span_id, "016x")
        doc.update(getattr(record, "fields", {}))
        return json.dumps(doc, ensure_ascii=False)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
log = logging.getLogger(ROLE)

tracer = trace.get_tracer("demo-app")
meter = metrics.get_meter("demo-app")
orders_counter = meter.create_counter("demo.orders", unit="{order}", description="처리한 주문 수")

app = FastAPI(title=f"demo-{ROLE}")
client = httpx.AsyncClient(timeout=5.0)


@app.get("/healthz")
async def healthz():
    return {"ok": True}


if ROLE == "gateway":

    @app.get("/checkout")
    async def checkout():
        resp = await client.post(f"{DOWNSTREAM_URL}/orders", json={"item": random.choice(["book", "pen", "mug"])})
        if resp.status_code >= 400:
            log.error("checkout failed", extra={"fields": {"status": resp.status_code}})
            raise HTTPException(status_code=502, detail="order failed")
        log.info("checkout ok", extra={"fields": resp.json()})
        return resp.json()

elif ROLE == "order":

    @app.post("/orders")
    async def create_order(body: dict):
        # 수동 span: 자동 계측으로는 보이지 않는 "앱 내부 단계"
        with tracer.start_as_current_span("reserve_inventory") as span:
            span.set_attribute("order.item", body.get("item", "unknown"))
            await asyncio.sleep(random.uniform(0.02, 0.06))

        resp = await client.post(f"{DOWNSTREAM_URL}/pay", json={"amount": random.randint(1, 100)})
        outcome = "paid" if resp.status_code < 400 else "payment_failed"
        orders_counter.add(1, {"outcome": outcome})
        if outcome != "paid":
            log.warning("payment failed", extra={"fields": {"status": resp.status_code}})
            raise HTTPException(status_code=502, detail="payment failed")
        log.info("order created", extra={"fields": {"item": body.get("item")}})
        return {"order": "created", "item": body.get("item")}

elif ROLE == "payment":

    @app.post("/pay")
    async def pay(body: dict):
        roll = random.random()
        if roll < PAYMENT_ERROR_RATE:
            log.error("payment gateway timeout", extra={"fields": {"amount": body.get("amount")}})
            raise HTTPException(status_code=500, detail="gateway timeout")
        delay = random.uniform(1.0, 2.0) if roll < PAYMENT_ERROR_RATE + PAYMENT_SLOW_RATE else random.uniform(0.03, 0.15)
        await asyncio.sleep(delay)
        log.info("payment approved", extra={"fields": {"amount": body.get("amount"), "delay_s": round(delay, 3)}})
        return {"payment": "approved"}
