import io
import socket

import httpx
import pytest
from fastapi.testclient import TestClient
from passage_scout import demo, providers
from passage_scout.config import settings
from passage_scout.inputs import InputError, extract_pdf, public_addresses
from passage_scout.main import app
from passage_scout.retrieval import cited_evidence, rank
from passage_scout.usage import BudgetExceeded, Usage
from pypdf import PdfWriter


@pytest.fixture
def client():
    with TestClient(app, base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
        yield client


def test_demo_never_uses_provider(client, monkeypatch):
    async def forbidden(*args, **kwargs):
        pytest.fail("Demo must not call providers")

    monkeypatch.setattr(httpx.AsyncClient, "post", forbidden)
    sample = client.get("/api/sample").json()
    result = client.post(
        "/api/ask", json={"question": sample["questions"][0], "document": sample["text"]}
    ).json()
    assert result["citations"][0]["url"].startswith("https://www.epa.gov/")
    assert "Prepared demo" in result["label"]
    assert result["trace_id"] != "0" * 32


def test_arbitrary_demo_is_illustrative(client):
    result = client.post(
        "/api/ask", json={"question": demo.QUESTIONS[0], "document": "Fake trees"}
    ).json()
    assert "not document-grounded" in result["label"]
    assert result["citations"] == []


def test_invalid_question_and_large_document(client):
    assert client.post("/api/ask", json={"question": " "}).status_code == 422
    response = client.post("/api/ask", json={"question": "PRIVATE" * 200})
    assert response.status_code == 422
    assert "PRIVATE" not in response.text
    assert client.post("/api/document/text", json={"text": "x" * 100001}).status_code == 422


def test_live_missing_keys_is_explicit(client, monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    monkeypatch.setenv("GROQ_API_KEY", "")
    settings.cache_clear()
    result = client.post("/api/ask", json={"mode": "live", "question": "Explain trees"})
    assert result.status_code == 503
    assert "server-side" in result.json()["detail"]


def test_remote_guard():
    with TestClient(app, base_url="http://localhost", client=("203.0.113.10", 12345)) as client:
        result = client.post("/api/document/url", json={"url": "https://example.com"})
        assert result.status_code == 403


def test_origin_guard(client):
    result = client.post(
        "/api/document/url",
        json={"url": "https://example.com"},
        headers={"origin": "https://evil.example"},
    )
    assert result.status_code == 403


@pytest.mark.parametrize(
    "ip", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "::ffff:127.0.0.1", "192.168.1.1"]
)
def test_private_dns_rejected(monkeypatch, ip):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **kw: [(2, 1, 6, "", (ip, 80))])
    with pytest.raises(InputError):
        public_addresses("example.com", 80)


def test_mixed_dns_rejected(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **kw: [(2, 1, 6, "", ("1.1.1.1", 80)), (2, 1, 6, "", ("10.0.0.1", 80))],
    )
    with pytest.raises(InputError):
        public_addresses("example.com", 80)


def test_pdf_invalid_and_blank():
    with pytest.raises(InputError):
        extract_pdf(b"not a PDF")
    writer = PdfWriter()
    writer.add_blank_page(200, 200)
    output = io.BytesIO()
    writer.write(output)
    with pytest.raises(InputError, match="No selectable text"):
        extract_pdf(output.getvalue())


def test_rank_and_citation_validation():
    sources = [
        {
            "url": "https://www.epa.gov/heatislands/benefits-trees-and-vegetation",
            "raw_content": "Trees reduce heat through shade and evapotranspiration. Water evaporates from leaves.",
        },
        {
            "url": "https://docs.python.org/3/",
            "raw_content": "Python has dictionaries and lists. Functions organize reusable code into modules.",
        },
    ]
    ranked = rank("How do trees cool through evapotranspiration?", sources)
    assert ranked[0]["url"].startswith("https://www.epa.gov")
    assert cited_evidence("Trees provide shade [1]", ranked)[0]["id"] == 1
    for text in ["No citations", "Invented [99]", "Mixed [1] [99]"]:
        with pytest.raises(ValueError):
            cited_evidence(text, ranked)
    assert rank("trees", [{"url": "javascript:alert(1)", "raw_content": "Trees " * 30}]) == []


def test_budget_reservation_and_settlement(monkeypatch):
    ledger = Usage()
    reservation = ledger.reserve(7000)
    with pytest.raises(BudgetExceeded):
        ledger.reserve(7000)
    ledger.settle(reservation, 100)
    assert ledger.snapshot()["groq"]["tokens_today"] == 100
    ledger.reserve(7000)
    assert ledger.snapshot()["tavily"]["credits_reserved"] == 4


@pytest.mark.asyncio
async def test_live_contract_and_failure(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq")
    settings.cache_clear()
    monkeypatch.setattr(providers, "usage", Usage())
    calls = []

    async def fake_post(self, url, headers, json):
        calls.append((url, json))
        if url.endswith("/search"):
            data = {"results": [{"url": "https://www.epa.gov/trees"}]}
        elif url.endswith("/extract"):
            data = {
                "results": [
                    {
                        "url": "https://www.epa.gov/trees",
                        "raw_content": "Trees cool cities through shade and evapotranspiration. Water evaporates from tree leaves.",
                    }
                ]
            }
        else:
            data = {
                "choices": [{"message": {"content": "Trees cool through shade. [1]"}}],
                "usage": {"total_tokens": 120},
            }
        return httpx.Response(200, json=data, headers={"x-ratelimit-remaining-requests": "999"})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    result = await providers.live_answer("How do trees cool cities?", "Trees provide shade")
    assert result["mode"] == "live" and result["citations"][0]["id"] == 1
    assert [url.rsplit("/", 1)[-1] for url, _ in calls] == ["search", "extract", "completions"]
    assert calls[0][1]["search_depth"] == "basic"
    assert calls[1][1]["extract_depth"] == "basic"
    assert providers.usage.snapshot()["groq"]["tokens_today"] == 120
    settings.cache_clear()


@pytest.mark.asyncio
async def test_provider_error_does_not_leak_body():
    class Client:
        async def post(self, *args, **kwargs):
            return httpx.Response(429, text="SECRET AND DOCUMENT TEXT")

    with pytest.raises(providers.ProviderError) as exc:
        await providers.post(Client(), "https://example.com", "SECRET", {})
    assert "SECRET" not in str(exc.value)
    assert "429" in str(exc.value)


def test_trusted_host_blocks_rebinding(client):
    result = client.get("/api/health", headers={"host": "attacker.example"})
    assert result.status_code == 400


def test_token_required_when_configured(client, monkeypatch):
    monkeypatch.setenv("LIVE_ACCESS_TOKEN", "local-test-token")
    settings.cache_clear()
    try:
        response = client.post("/api/ask", json={"mode": "live", "question": "Trees?"})
        assert response.status_code == 401
        response = client.post(
            "/api/ask",
            json={"mode": "live", "question": "Trees?"},
            headers={"x-live-token": "local-test-token"},
        )
        assert response.status_code == 503
    finally:
        settings.cache_clear()


def test_successful_pdf_and_page_limit(monkeypatch):
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    page = writer.add_blank_page(300, 300)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    stream = DecodedStreamObject()
    stream.set_data(
        b"BT /F1 12 Tf 20 200 Td (Trees provide cooling through shade and evaporation.) Tj ET"
    )
    page[NameObject("/Contents")] = stream
    output = io.BytesIO()
    writer.write(output)
    assert "Trees provide cooling" in extract_pdf(output.getvalue())
    writer.add_blank_page(300, 300)
    output = io.BytesIO()
    writer.write(output)
    monkeypatch.setenv("MAX_PDF_PAGES", "1")
    settings.cache_clear()
    try:
        with pytest.raises(InputError, match="page limit"):
            extract_pdf(output.getvalue())
    finally:
        settings.cache_clear()


def test_redirect_is_revalidated(monkeypatch):
    from passage_scout import inputs

    visited = []

    def addresses(host, port):
        visited.append(host)
        if host == "internal.example":
            raise InputError("private destination")
        return ["1.1.1.1"]

    class Response:
        status = 302

        def getheader(self, name):
            return "http://internal.example/"

    class Connection:
        def __init__(self, *args):
            pass

        def request(self, *args, **kwargs):
            pass

        def getresponse(self):
            return Response()

        def close(self):
            pass

    monkeypatch.setattr(inputs, "public_addresses", addresses)
    monkeypatch.setattr(inputs, "PinnedHTTPS", Connection)
    with pytest.raises(InputError, match="private destination"):
        inputs._fetch_article("https://public.example/")
    assert visited == ["public.example", "internal.example"]


def test_telemetry_correlates_without_exception_content(caplog):
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from passage_scout.telemetry import stage, trace_provider

    exporter = InMemorySpanExporter()
    trace_provider.add_span_processor(SimpleSpanProcessor(exporter))
    with pytest.raises(ValueError):
        with stage("test.safe"):
            raise ValueError("PRIVATE_DOCUMENT_SENTINEL")
    spans = exporter.get_finished_spans()
    assert spans[-1].status.status_code.name == "ERROR"
    assert not spans[-1].events
    assert "PRIVATE_DOCUMENT_SENTINEL" not in caplog.text
    assert "trace_id" in caplog.text


def test_body_limit(client, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "1000")
    settings.cache_clear()
    try:
        response = client.post(
            "/api/document/text",
            content=b"x" * 101001,
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 413
    finally:
        settings.cache_clear()
