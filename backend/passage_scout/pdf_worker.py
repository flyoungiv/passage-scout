"""Isolate untrusted PDF decompression/parsing from the API process."""

import io
import json
import sys


def main():
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
        # RLIMIT_AS is unsupported on macOS; CPU and parent wall timeout still apply.
        if sys.platform != "darwin":
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(sys.stdin.buffer.read(10_000_001)))
        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported.")
        if len(reader.pages) > int(sys.argv[1]):
            raise ValueError("PDF exceeds the configured page limit.")
        chunks = []
        total = 0
        for index, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            total += len(text)
            if total > int(sys.argv[2]):
                raise ValueError("PDF exceeds the document character limit.")
            chunks.append(f"## Page {index + 1}\n\n{text}")
        if total < 30:
            raise ValueError(
                "No selectable text found. OCR is not supported; use the original PDF viewer or paste text."
            )
        print(json.dumps({"text": "\n\n".join(chunks)}))
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}))
    except Exception:
        print(json.dumps({"error": "Could not read this PDF. Try another file."}))


if __name__ == "__main__":
    main()
