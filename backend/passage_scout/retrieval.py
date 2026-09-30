"""Small deterministic lexical ranker; inspectable, with no embedding service."""

import math
import re
from collections import Counter
from urllib.parse import urlsplit

STOP = set(
    "the a an and or to of in is it for on as how what do does are be this that with".split()
)


def words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP]


def public_url_shape(url: str) -> bool:
    try:
        p = urlsplit(url)
        return (
            p.scheme in {"http", "https"}
            and bool(p.hostname)
            and not p.username
            and not p.password
            and p.port in {None, 80, 443}
        )
    except ValueError:
        return False


def rank(query: str, sources: list[dict], limit: int = 5) -> list[dict]:
    candidates = []
    for source in sources[:5]:
        url = source.get("url", "")
        if not public_url_shape(url):
            continue
        # Hard cap before splitting: provider text is untrusted and may be huge.
        text = source.get("raw_content", "")[:40000]
        for offset in range(0, len(text), 1000):
            passage = text[offset : offset + 1200].strip()
            if len(passage) >= 40:
                candidates.append(
                    {"url": url, "title": source.get("title") or url, "passage": passage}
                )
    query_terms = set(words(query))
    counts = [Counter(words(c["passage"])) for c in candidates]
    for item, count in zip(candidates, counts):
        score = sum(
            (1 + math.log(count[t])) * math.log(1 + len(counts) / (1 + sum(t in c for c in counts)))
            for t in query_terms
            if count[t]
        )
        item["score"] = round(score / math.sqrt(max(1, sum(count.values()))), 5)
    candidates.sort(key=lambda c: c["score"], reverse=True)
    selected = []
    per_url: Counter = Counter()
    for item in candidates:
        if item["score"] <= 0 or per_url[item["url"]] >= 2:
            continue
        per_url[item["url"]] += 1
        selected.append({**item, "id": len(selected) + 1})
        if len(selected) == limit:
            break
    return selected


def cited_evidence(answer: str, evidence: list[dict]) -> list[dict]:
    ids = {int(i) for i in re.findall(r"\[(\d+)\]", answer)}
    known = {item["id"] for item in evidence}
    if not ids or not ids <= known:
        raise ValueError(
            "The model returned missing or invalid citations. Try a narrower question."
        )
    return [item for item in evidence if item["id"] in ids]
