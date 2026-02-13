"""
Main pipeline: fetch papers → score with LLM → ready for dashboard.
Run this twice a week (e.g., Monday and Thursday mornings).

Usage:
    python3 run_pipeline.py          # Fetch + score
    python3 run_pipeline.py --fetch  # Fetch only (no Ollama needed)
    python3 run_pipeline.py --score  # Score only (requires Ollama)
"""

import logging
logging.getLogger("streamlit").setLevel(logging.ERROR)

import sys
from database import init_db
from fetcher import fetch_all
from scorer import score_all_unscored

init_db()


def main():
    args = sys.argv[1:]

    if "--fetch" in args:
        fetch_all()
    elif "--score" in args:
        score_all_unscored()
    else:
        # Full pipeline
        new_count = fetch_all()
        if new_count > 0:
            print()
            score_all_unscored()
        else:
            print("\nNo new papers to score.")

    print("\n🚀 Done! Run `streamlit run dashboard.py` to view results.")


if __name__ == "__main__":
    main()
