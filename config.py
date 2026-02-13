"""
Configuration for the Neoantigen Vaccine Paper Tracker.
Update these settings to customize your tracking scope.
"""

# ── Search Queries ──────────────────────────────────────────────────────────
# PubMed queries (uses NCBI E-utilities syntax)
PUBMED_QUERIES = [
    "neoantigen vaccine",
    "neoantigen mRNA vaccine",
    "personalized cancer vaccine peptide",
    "neoepitope vaccine",
    "tumor mutanome vaccine",
    "individualized neoantigen therapy",
    "personalized neoantigen immunotherapy",
]

# BioRxiv search terms (simple keyword search)
BIORXIV_QUERIES = [
    "neoantigen vaccine",
    "personalized cancer vaccine",
    "neoepitope vaccine",
    "tumor mutanome",
]

# ── Relevance Scoring Prompt ────────────────────────────────────────────────
RELEVANCE_SYSTEM_PROMPT = """You are a scientific literature analyst specializing in cancer immunotherapy, 
specifically neoantigen-based therapeutic vaccines.

The user's team is building neoantigen vaccines for cancer, focused on:
- mRNA-based neoantigen vaccines
- Peptide-based neoantigen vaccines

Score each paper's relevance from 1-10 based on these criteria:
- 9-10: Directly about neoantigen vaccine design, clinical trials, manufacturing, or efficacy (mRNA or peptide-based)
- 7-8: Closely related (e.g., neoantigen prediction algorithms, tumor immunology relevant to vaccine design, adjuvant systems for cancer vaccines)
- 5-6: Tangentially related (e.g., general cancer immunotherapy, checkpoint inhibitors combined with vaccines, antigen presentation)
- 3-4: Loosely related (e.g., general mRNA therapeutics, general peptide therapeutics not vaccine-focused)
- 1-2: Not relevant

Also provide a 2-3 sentence summary focused on what's actionable or novel for a neoantigen vaccine company.

Respond in JSON format:
{
    "relevance_score": <int 1-10>,
    "summary": "<string>",
    "key_finding": "<one-sentence headline of the main finding>",
    "tags": ["<tag1>", "<tag2>"]  // e.g., "mRNA", "peptide", "clinical-trial", "preclinical", "neoantigen-prediction", "manufacturing", "adjuvant", "combination-therapy"
}
"""

# ── Settings ────────────────────────────────────────────────────────────────
# Minimum relevance score to display in dashboard (1-10)
MIN_RELEVANCE_SCORE = 5

# Number of days to look back when fetching papers
LOOKBACK_DAYS = 4  # Twice-weekly = every 3-4 days, with 1 day buffer

# Maximum papers to process per run (to manage API costs)
MAX_PAPERS_PER_RUN = 50

# ── LLM (Ollama - local, free) ──────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "mistral"  # Good balance of speed and quality. Alternatives: llama3, gemma2

# Database path (always in the same directory as this file)
import os
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "papers.db")
