"""HTTP API and the one-page UI."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import anthropic
from actrag.api import CORPUS_DATE, DISCLAIMER
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, StringConstraints

from riskagent import agent
from riskagent.agent import AgentError, assess

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


def create_app(retriever=None, llm=None) -> FastAPI:
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
            app.state.llm = anthropic.Anthropic()
        else:
            app.state.llm = None  # /health and the UI still work; /assess explains what's missing
        yield

    app = FastAPI(title="AI Act risk agent", lifespan=lifespan)

    @app.post("/assess")
    def assess_route(body: Assess, request: Request):
        if request.app.state.llm is None:
            return JSONResponse({"error": "no_api_key"}, status_code=503)
        answers = [a.model_dump() for a in body.answers]
        try:
            o = assess(
                body.description, answers, request.app.state.retriever, request.app.state.llm
            )
        except AgentError as e:
            return JSONResponse({"error": e.code}, status_code=502)
        except anthropic.APIError:
            return JSONResponse({"error": "upstream"}, status_code=503)
        out = {"status": o.status}
        for key in ("assessment", "question", "missing"):
            if getattr(o, key) is not None:
                out[key] = getattr(o, key)
        if o.checked is not None:
            out["problems"] = o.checked.problems
        return out | {"model": agent.MODEL, "corpus_date": CORPUS_DATE, "disclaimer": DISCLAIMER}

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
