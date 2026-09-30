"""Bounded public-only fetch, with validated DNS pinned to the socket."""

import http.client
import ipaddress
import socket
import ssl
import subprocess
import sys
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
from markdownify import markdownify

from .config import settings
from .retrieval import public_url_shape


class InputError(Exception):
    pass


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, hostname, address, port):
        super().__init__(hostname, port=port, timeout=8, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        sock = socket.create_connection((self.address, self.port), timeout=self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


class PinnedHTTP(http.client.HTTPConnection):
    def __init__(self, hostname, address, port):
        super().__init__(hostname, port=port, timeout=8)
        self.address = address

    def connect(self):
        self.sock = socket.create_connection((self.address, self.port), timeout=self.timeout)


def public_addresses(hostname: str, port: int) -> list[str]:
    try:
        addresses = list(
            {r[4][0] for r in socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)}
        )
    except OSError as exc:
        raise InputError("The article hostname could not be resolved.") from exc
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise InputError("Only ordinary public internet URLs are allowed.")
    return addresses


def _fetch_article(url: str) -> str:
    for _ in range(4):
        if not public_url_shape(url) or len(url) > 2048:
            raise InputError("Use an http(s) article URL without credentials or custom ports.")
        parsed = urlsplit(url)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        addresses = public_addresses(parsed.hostname, port)
        conn_type = PinnedHTTPS if parsed.scheme == "https" else PinnedHTTP
        conn = conn_type(parsed.hostname, addresses[0], port)
        try:
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            conn.request(
                "GET",
                path,
                headers={
                    "User-Agent": "PassageScout/0.1",
                    "Accept": "text/html,text/plain",
                    "Accept-Encoding": "identity",
                },
            )
            response = conn.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                if not location:
                    raise InputError("Article redirect has no destination.")
                url = urljoin(url, location)
                continue
            if response.status != 200:
                raise InputError(
                    f"Article returned HTTP {response.status}; paste the text instead."
                )
            kind = response.getheader("Content-Type", "").split(";")[0]
            if kind not in {"text/html", "text/plain", "application/xhtml+xml"}:
                raise InputError("This URL is not an HTML or text article. Upload PDFs separately.")
            data = response.read(2_000_001)
            if len(data) > 2_000_000:
                raise InputError("Article exceeds the 2 MB fetch limit.")
            content = data.decode("utf-8", errors="replace")
            if kind != "text/plain":
                soup = BeautifulSoup(content, "html.parser")
                for tag in soup(["script", "style", "nav", "footer", "header", "form", "iframe"]):
                    tag.decompose()
                content = markdownify(
                    str(soup.find("article") or soup.find("main") or soup),
                    heading_style="ATX",
                    strip=["img", "a"],
                )
            content = content.strip()
            if len(content) < 50:
                raise InputError("No readable article text found. Paste the text instead.")
            if len(content) > settings().max_document_chars:
                raise InputError(
                    "Article exceeds the document character limit; paste a shorter excerpt."
                )
            return content
        except (OSError, http.client.HTTPException, ValueError) as exc:
            raise InputError(
                "Article could not be fetched safely; paste its text instead."
            ) from exc
        finally:
            conn.close()
    raise InputError("Too many article redirects.")


def extract_pdf(data: bytes) -> str:
    import json

    s = settings()
    if not data.startswith(b"%PDF-"):
        raise InputError("Upload a valid PDF file.")
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "passage_scout.pdf_worker",
                str(s.max_pdf_pages),
                str(s.max_document_chars),
            ],
            input=data,
            capture_output=True,
            timeout=12,
            check=False,
        )
        if result.returncode:
            raise InputError(
                "PDF extraction failed or exceeded its resource limits. Try a smaller PDF."
            )
        parsed = json.loads(result.stdout)
        if parsed.get("error"):
            raise InputError(parsed["error"])
        return parsed["text"]
    except (subprocess.TimeoutExpired, ValueError) as exc:
        raise InputError(
            "PDF extraction exceeded its limits; use a smaller selectable-text PDF."
        ) from exc


def fetch_article(url: str) -> str:
    import json

    try:
        result = subprocess.run(
            [sys.executable, "-m", "passage_scout.article_worker"],
            input=url.encode(),
            capture_output=True,
            timeout=20,
            check=False,
        )
        if result.returncode:
            raise InputError("Article fetch exceeded resource limits; paste its text instead.")
        parsed = json.loads(result.stdout)
        if parsed.get("error"):
            raise InputError(parsed["error"])
        return parsed["text"]
    except (subprocess.TimeoutExpired, ValueError) as exc:
        raise InputError("Article fetch timed out; paste its text instead.") from exc
