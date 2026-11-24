"""HTTP API and the one-page UI."""

from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import anthropic
from actrag.api import CORPUS_DATE, DISCLAIMER
from actrag.demo import (
    DEMO_MODEL,
    FULL_MODEL,
    Limiter,
    client_ip,
    demo_on,
    is_spend_cap,
    visitor_key,
)
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, StringConstraints

from riskagent import agent
from riskagent.agent import AgentError, assess

log = logging.getLogger("riskagent")
STATIC = Path(__file__).parent / "static"
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class Answer(BaseModel):
    question: Text
    answer: Text


class Assess(BaseModel):
    description: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=20, max_length=4000)
    ]
    answers: list[Answer] = Field(default_factory=list, max_length=agent.MAX_QUESTIONS)


def who(key: str | None) -> str:
    return "visitor" if key else "owner"


def create_app(retriever=None, llm=None, client_factory=anthropic.Anthropic) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if retriever is None:
            from actrag.retrieve import Retriever

            app.state.retriever = Retriever.load()
        else:
            app.state.retriever = retriever
        if llm is not None:
            app.state.llm = llm
        elif os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
            # in the demo, a capped key should fail fast instead of retrying
            app.state.llm = anthropic.Anthropic(max_retries=1 if demo_on() else 2)
        else:
            app.state.llm = None  # /health and the UI still work; /assess explains what's missing
        app.state.limiter = Limiter()
        app.state.key_limiter = Limiter(per_ip=30, total=10**6)
        yield

    app = FastAPI(title="AI Act risk agent", lifespan=lifespan)

    @app.post("/assess")
    def assess_route(body: Assess, request: Request):
        key = visitor_key(request)  # a visitor's own key: never logged, stored or echoed
        if key:
            # their key, their cost; a looser limit still stops junk keys from burning our CPU
            if request.app.state.key_limiter.check(client_ip(request)):
                return JSONResponse({"error": "rate_limited"}, status_code=429)
            llm, model = client_factory(api_key=key), FULL_MODEL
        elif request.app.state.llm is None:
            return JSONResponse({"error": "no_api_key"}, status_code=503)
        elif demo_on():
            ip = client_ip(request)
            denied = request.app.state.limiter.check(ip)
            if denied:
                log.warning("demo %s for %s", denied, ip)  # owner-only logs; checks PROXY_HOPS
                return JSONResponse({"error": denied}, status_code=429)
            llm, model = request.app.state.llm, DEMO_MODEL
        else:
            llm, model = request.app.state.llm, agent.MODEL
        answers = [a.model_dump() for a in body.answers]
        try:
            o = assess(body.description, answers, request.app.state.retriever, llm, model=model)
        except AgentError as e:
            return JSONResponse({"error": e.code}, status_code=502)
        except anthropic.APIStatusError as e:
            # type and status only, so the owner can see why in the host's logs; never the key
            log.warning("anthropic %s %s (%s key)", type(e).__name__, e.status_code, who(key))
            # their key is wrong, can't run this, or is out of credit: retrying won't help
            if key and (e.status_code in (401, 402, 403) or is_spend_cap(e)):
                return JSONResponse({"error": "bad_key"}, status_code=401)
            paused = not key and is_spend_cap(e)
            return JSONResponse({"error": "paused" if paused else "upstream"}, status_code=503)
        except anthropic.APIError as e:
            log.warning("anthropic %s (%s key)", type(e).__name__, who(key))
            return JSONResponse({"error": "upstream"}, status_code=503)
        out = {"status": o.status}
        for field in ("assessment", "question", "missing"):
            if getattr(o, field) is not None:
                out[field] = getattr(o, field)
        if o.checked is not None:
            out["problems"] = o.checked.problems
        return out | {"model": model, "corpus_date": CORPUS_DATE, "disclaimer": DISCLAIMER}

    @app.get("/config")
    def config():
        demo = demo_on()
        return {"demo": demo, "model": DEMO_MODEL if demo else agent.MODEL, "byok": demo}

    @app.get("/examples")
    def examples():
        f = STATIC / "examples.json"
        return json.loads(f.read_text()) if f.exists() else []

    @app.get("/health")
    def health():
        return {"status": "ok", "corpus_date": CORPUS_DATE}

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC / "index.html")

    return app


def __getattr__(name):  # `uvicorn riskagent.api:app` builds the real app on first access
    if name == "app":
        globals()["app"] = create_app()
        return globals()["app"]
    raise AttributeError(name)
