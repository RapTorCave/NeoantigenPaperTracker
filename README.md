# SerovaPaperTracker
Tracking relevant research papers for cancer vaccines design etc
# 🧬 Neoantigen Vaccine Paper Tracker

Literature monitoring tool for neoantigen vaccine research. Automatically fetches recent papers from PubMed and BioRxiv/MedRxiv, scores their relevance using a local LLM, and serves everything through a clean web dashboard.


---

## How It Works

```
PubMed API ──┐
             ├── Fetcher ── SQLite ── Ollama (local LLM) ── Streamlit Dashboard
BioRxiv API ─┘
```

1. **Fetch** — Queries PubMed and BioRxiv/MedRxiv APIs for recent papers matching configurable search terms. Deduplicates across sources and runs.
2. **Score** — Sends each paper's title and abstract to a local LLM ([Ollama](https://ollama.com)) which returns a relevance score (1–10), a short summary, a key finding headline, and topic tags.
3. **Browse** — A Streamlit dashboard lets you filter by relevance, source, and starred status. You can star papers, add notes, and expand full abstracts.

All data accumulates in a local SQLite database across runs, so you build up a searchable archive over time.

## Quick Start

### Prerequisites

- **Python 3.10+**
- **[Ollama](https://ollama.com)** — free, local LLM runtime

### 1. Clone and install

```bash
git clone https://github.com/RapTorCave/NeoantigenPaperTracker.git
cd NeoantigenPaperTracker
python3 -m pip install -r requirements.txt
```

### 2. Set up Ollama

Install Ollama from [ollama.com](https://ollama.com), then:

```bash
# Start the server (keep this running in a separate terminal)
ollama serve

# Download the model (~4GB, one-time)
ollama pull mistral
```

### 3. Run the pipeline

```bash
python3 run_pipeline.py
```

This fetches recent papers and scores them. You'll see progress in the terminal:

```
============================================================
🔬 Neoantigen Vaccine Paper Fetch
============================================================
📚 Fetching from PubMed...
  Query 'neoantigen vaccine': 12 results, 8 new
  Query 'neoantigen mRNA vaccine': 6 results, 2 new
  ...
📄 Fetching from biorxiv...
  Matched 3 relevant papers
✅ Added 13 new papers to database

🤖 Scoring 13 papers with Ollama (mistral)...
  [1/13] Personalized neoantigen vaccine in combination with...
    → Score: 9/10 | Tags: mRNA, clinical-trial, combination-therapy
  ...
✅ Scored 13/13 papers
```

### 4. Launch the dashboard

```bash
python3 launch.py
```

This opens the dashboard automatically in your browser at [http://localhost:8501](http://localhost:8501).

> **Alternative:** You can also run `python3 -m streamlit run dashboard.py` directly if you prefer.

## Usage

### Routine workflow

Run the pipeline twice a week (or however often you like). Each run only fetches and scores *new* papers — previously seen papers are skipped. The database accumulates everything across runs, so the dashboard always shows your full archive.

```bash
# Full pipeline
python3 run_pipeline.py

# Or run steps independently
python3 run_pipeline.py --fetch   # Fetch only (no Ollama needed)
python3 run_pipeline.py --score   # Score only (needs Ollama running)
```

### Dashboard features

- **Filter** by minimum relevance score, source (PubMed / BioRxiv / MedRxiv), or starred status
- **Star** papers to bookmark them
- **Expand** any paper to read the full abstract and add notes
- **Open** papers directly in PubMed or the preprint server
- **Full archive** — drag the relevance slider down to 1 to see every paper ever fetched

## Project Structure

```
neoantigen-paper-tracker/
├── config.py            # Search queries, scoring prompt, all settings
├── fetcher.py           # PubMed + BioRxiv/MedRxiv API integration
├── scorer.py            # Ollama LLM scoring and summarisation
├── database.py          # SQLite storage layer
├── run_pipeline.py      # CLI entry point: fetch → score
├── dashboard.py         # Streamlit web UI
├── launch.py            # Dashboard launcher (opens browser automatically)
├── requirements.txt     # Python dependencies
├── .streamlit/
│   └── config.toml      # Streamlit settings (logging, browser behaviour)
├── .gitignore
├── papers.db            # SQLite database (created on first run, gitignored)
└── README.md
```

## Configuration

Everything is in `config.py`:

### Search queries

```python
PUBMED_QUERIES = [
    "neoantigen vaccine",
    "neoantigen mRNA vaccine",
    "personalized cancer vaccine peptide",
    # Add your own...
]

BIORXIV_QUERIES = [
    "neoantigen vaccine",
    "personalized cancer vaccine",
    # Add your own...
]
```

### Scoring criteria

The `RELEVANCE_SYSTEM_PROMPT` tells the LLM how to score papers. Edit this to match your team's focus — for example, if you only work on mRNA vaccines, you can tell it to score peptide papers lower.

### Other settings

| Setting | Default | Description |
|---------|---------|-------------|
| `LOOKBACK_DAYS` | `4` | How far back to search (4 days suits a twice-weekly schedule) |
| `MAX_PAPERS_PER_RUN` | `50` | Cap on papers processed per run |
| `OLLAMA_MODEL` | `mistral` | Local model to use. Alternatives: `llama3`, `gemma2` |
| `MIN_RELEVANCE_SCORE` | `5` | Default dashboard filter threshold |

## Data Sources

| Source | API | Auth required | What it returns |
|--------|-----|---------------|-----------------|
| **PubMed** | [NCBI E-utilities](https://www.ncbi.nlm.nih.gov/books/NBK25501/) | No | Published papers with full metadata and abstracts |
| **BioRxiv** | [BioRxiv API](https://api.biorxiv.org) | No | Preprints (often weeks/months ahead of formal publication) |
| **MedRxiv** | [BioRxiv API](https://api.biorxiv.org) | No | Clinical/health science preprints |

All APIs are free and require no authentication.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Ollama is not running` | Run `ollama serve` in a separate terminal |
| `Model 'mistral' not found` | Run `ollama pull mistral` |
| 0 papers found | Increase `LOOKBACK_DAYS` in `config.py`, or check search terms |
| JSON parse errors during scoring | Try a larger model (`llama3`) — smaller models occasionally struggle with structured output |
| PubMed returns 0 for recent dates | Normal — PubMed indexing can lag 1–2 days behind publication |
| Dashboard can't find papers | The database is created in the project folder. Make sure you're running commands from the project directory, or use `launch.py` |


## License

MIT
