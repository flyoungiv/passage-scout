"""Offline retrieval/citation regression cases, not a live quality benchmark."""

import json
from pathlib import Path

from passage_scout.retrieval import cited_evidence, rank

cases = json.loads(
    (Path(__file__).resolve().parents[1] / "tests/fixtures/retrieval.json").read_text()
)
passed = 0
for case in cases:
    evidence = rank(case["question"], case["sources"])
    ok = bool(evidence) and evidence[0]["url"] == case["expected_url"]
    if ok:
        ok = cited_evidence("Supported claim [1]", evidence)[0]["url"] == case["expected_url"]
    passed += int(ok)
    print(f"{case['id']}: {'PASS' if ok else 'FAIL'}")
print(f"Top-1 retrieval + citation mapping: {passed}/{len(cases)} fixed cases")
raise SystemExit(0 if passed == len(cases) else 1)
