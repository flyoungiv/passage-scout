import asyncio
import hmac
import ipaddress
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import demo
from .config import settings
from .inputs import InputError, extract_pdf, fetch_article
from .providers import ProviderError, live_answer
from .telemetry import stage
from .usage import BudgetExceeded, usage

app = FastAPI(title="Passage Scout", version="0.1.0")
provider_lock = asyncio.Lock()
input_lock = asyncio.Lock()


class BodyLimit:
    """Count chunked bodies too, before multipart/JSON parsing."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        total = 0

        async def limited():
            nonlocal total
            message = await receive()
            total += len(message.get("body", b""))
            if total > settings().max_upload_bytes + 100_000:
                raise HTTPException(413, "Request exceeds the upload limit.")
            return message

        await self.app(scope, limited, send)


app.add_middleware(BodyLimit)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings().allowed_hosts)


@app.exception_handler(RequestValidationError)
async def invalid_input(request, exc):
    # Default validation errors can reflect complete input; keep responses small and private.
    return JSONResponse(
        status_code=422, content={"detail": "Invalid input or input exceeds the allowed length."}
    )


def guard(request: Request, token: str | None):
    host = request.client.host if request.client else ""
    try:
        local = ipaddress.ip_address(host).is_loopback
    except ValueError:
        local = False
    expected = settings().live_access_token.get_secret_value()
    if expected:
        if not token or not hmac.compare_digest(token, expected):
            raise HTTPException(401, "A valid server access token is required.")
    elif not local:
        raise HTTPException(
            403,
            "Remote live/fetch requests are disabled. Configure LIVE_ACCESS_TOKEN on the server.",
        )
    # Reject browser cross-origin requests even on localhost (DNS rebinding/drive-by calls).
    origin = request.headers.get("origin")
    if origin:
        from urllib.parse import urlsplit

        if urlsplit(origin).netloc != request.headers.get("host"):
            raise HTTPException(403, "Cross-origin requests are not allowed.")


class DocumentInput(BaseModel):
    text: str = Field(min_length=1, max_length=100000)


class URLInput(BaseModel):
    url: str = Field(min_length=8, max_length=2048)


class AskInput(BaseModel):
    mode: Literal["demo", "live"] = "demo"
    question: str = Field(min_length=1, max_length=600)
    passage: str = Field(default="", max_length=2000)
    document: str = Field(default="", max_length=100000)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def config():
    s = settings()
    return {
        "live_ready": s.live_ready,
        "access_token_required": bool(s.live_access_token.get_secret_value()),
        "model": s.groq_model,
        "max_upload_bytes": s.max_upload_bytes,
        "max_pdf_pages": s.max_pdf_pages,
    }


@app.get("/api/sample")
def sample():
    return {"text": demo.SAMPLE, "questions": demo.QUESTIONS}


@app.get("/api/usage")
def get_usage():
    return usage.snapshot()


@app.post("/api/document/text")
def text_document(body: DocumentInput):
    if len(body.text) > settings().max_document_chars or not body.text.strip():
        raise HTTPException(422, "Text is empty or exceeds the document limit.")
    with stage("input.text"):
        return {"text": body.text}


@app.post("/api/document/url")
async def article(body: URLInput, request: Request, x_live_token: str | None = Header(None)):
    guard(request, x_live_token)
    if input_lock.locked():
        raise HTTPException(429, "Another document is being processed. Retry shortly.")
    async with input_lock:
        with stage("input.article"):
            try:
                return {"text": await asyncio.to_thread(fetch_article, body.url)}
            except InputError as exc:
                raise HTTPException(422, str(exc)) from exc


@app.post("/api/document/pdf")
async def pdf(
    request: Request, file: UploadFile = File(...), x_live_token: str | None = Header(None)
):
    guard(request, x_live_token)
    if input_lock.locked():
        raise HTTPException(429, "Another document is being processed. Retry shortly.")
    async with input_lock:
        with stage("input.pdf"):
            data = await file.read(settings().max_upload_bytes + 1)
            await file.close()
            if len(data) > settings().max_upload_bytes:
                raise HTTPException(413, "PDF exceeds the upload limit.")
            try:
                return {"text": await asyncio.to_thread(extract_pdf, data)}
            except InputError as exc:
                raise HTTPException(422, str(exc)) from exc


@app.post("/api/ask")
async def ask(body: AskInput, request: Request, x_live_token: str | None = Header(None)):
    if not body.question.strip():
        raise HTTPException(422, "Enter a question.")
    with stage("rag.request") as span:
        span.set_attribute("scout.mode", body.mode)
        trace_id = f"{span.get_span_context().trace_id:032x}"
        if body.mode == "demo":
            result = demo.answer(body.question, body.document)
        else:
            guard(request, x_live_token)
            if not settings().live_ready:
                raise HTTPException(
                    503,
                    "Live RAG needs server-side TAVILY_API_KEY and GROQ_API_KEY. Choose Demo to explore offline.",
                )
            if provider_lock.locked():
                raise HTTPException(429, "One live request is already running. Retry shortly.")
            async with provider_lock:
                try:
                    async with asyncio.timeout(80):
                        result = await live_answer(body.question, body.passage)
                except TimeoutError as exc:
                    raise HTTPException(
                        504, "Live retrieval timed out. Retry or choose Demo."
                    ) from exc
                except BudgetExceeded as exc:
                    raise HTTPException(429, str(exc)) from exc
                except ProviderError as exc:
                    raise HTTPException(502, str(exc)) from exc
        return {**result, "trace_id": trace_id}


frontend = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend.is_dir():
    app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
