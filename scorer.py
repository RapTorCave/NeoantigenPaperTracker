"""
Uses a local Ollama model to score paper relevance and generate summaries.
Completely free — no API keys needed.

Requires:
  1. Ollama installed (https://ollama.com)
  2. Ollama server running (ollama serve)
  3. A model pulled (ollama pull mistral)
"""

import json
import time
import requests
from config import RELEVANCE_SYSTEM_PROMPT, OLLAMA_BASE_URL, OLLAMA_MODEL
from database import get_unscored_papers, update_paper_scoring


def check_ollama() -> bool:
    """Check if Ollama is running and the model is available."""
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m["name"].split(":")[0] for m in resp.json().get("models", [])]
        if OLLAMA_MODEL not in models:
            print(f"  ⚠ Model '{OLLAMA_MODEL}' not found in Ollama.")
            print(f"    Available models: {', '.join(models) if models else 'none'}")
            print(f"    Run: ollama pull {OLLAMA_MODEL}")
            return False
        return True
    except requests.ConnectionError:
        print("  ⚠ Ollama is not running. Start it with: ollama serve")
        return False
    except Exception as e:
        print(f"  ⚠ Ollama check failed: {e}")
        return False


def parse_response(text: str) -> dict | None:
    """Parse JSON from the model response, handling common formatting issues."""
    # Strip markdown code blocks if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    text = text.removeprefix("```json").removesuffix("```").strip()

    try:
        result = json.loads(text)
        return {
            "relevance_score": max(1, min(10, int(result.get("relevance_score", 1)))),
            "summary": str(result.get("summary", "")),
            "key_finding": str(result.get("key_finding", "")),
            "tags": list(result.get("tags", [])),
        }
    except (json.JSONDecodeError, ValueError) as e:
        print(f"  ⚠ Failed to parse response: {e}")
        print(f"    Raw: {text[:200]}")
        return None


def score_paper(title: str, abstract: str, journal: str) -> dict | None:
    """Score a single paper using the local Ollama model."""
    user_message = f"""Please evaluate this paper:

**Title**: {title}
**Journal**: {journal}
**Abstract**: {abstract if abstract else 'No abstract available.'}

Respond with JSON only, no other text, no markdown code blocks."""

    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": RELEVANCE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                "stream": False,
                "options": {
                    "temperature": 0.3,
                },
            },
            timeout=120,
        )
        resp.raise_for_status()
        text = resp.json()["message"]["content"].strip()
        return parse_response(text)
    except Exception as e:
        print(f"  ⚠ Ollama error: {e}")
        return None


def score_all_unscored():
    """Score all papers that haven't been scored yet."""
    papers = get_unscored_papers()
    if not papers:
        print("✅ No unscored papers found.")
        return 0

    print(f"🤖 Scoring {len(papers)} papers with Ollama ({OLLAMA_MODEL})...")

    if not check_ollama():
        print("\n❌ Cannot score papers. Fix Ollama setup and retry.")
        return 0

    scored = 0
    for i, paper in enumerate(papers):
        print(f"  [{i + 1}/{len(papers)}] {paper['title'][:80]}...")

        result = score_paper(
            title=paper["title"],
            abstract=paper.get("abstract", ""),
            journal=paper.get("journal", ""),
        )

        if result:
            update_paper_scoring(
                paper_id=paper["id"],
                relevance_score=result["relevance_score"],
                summary=result["summary"],
                key_finding=result["key_finding"],
                tags=result["tags"],
            )
            print(f"    → Score: {result['relevance_score']}/10 | Tags: {', '.join(result['tags'])}")
            scored += 1

        time.sleep(0.2)

    print(f"\n✅ Scored {scored}/{len(papers)} papers")
    return scored


if __name__ == "__main__":
    score_all_unscored()
