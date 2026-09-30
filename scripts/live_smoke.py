"""Opt-in: consumes provider quota; does not print source or answer text."""

import asyncio

from passage_scout.config import settings
from passage_scout.providers import ProviderError, live_answer


async def main():
    if not settings().live_ready:
        raise SystemExit("Missing local TAVILY_API_KEY and GROQ_API_KEY; live smoke was not run.")
    try:
        result = await live_answer(
            "How do urban trees reduce heat?", "Trees provide shade and evapotranspiration."
        )
    except ProviderError as exc:
        raise SystemExit(str(exc)) from None
    assert result["mode"] == "live" and result["citations"]
    print(f"Live providers succeeded; {len(result['citations'])} validated citation(s).")


if __name__ == "__main__":
    asyncio.run(main())
