"""
Streamlit dashboard for the Neoantigen Vaccine Paper Tracker.
Run with: streamlit run dashboard.py
"""


import streamlit as st
import json
from database import get_papers, get_stats, toggle_star, update_notes, init_db

init_db()

# ── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Neoantigen Vaccine Tracker",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    .stApp { font-family: 'DM Sans', sans-serif; }
    
    .paper-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 0.75rem;
    }
    .paper-title {
        font-size: 1rem;
        font-weight: 600;
        color: #0f172a;
        line-height: 1.4;
        margin-bottom: 0.3rem;
    }
    .paper-meta {
        font-size: 0.8rem;
        color: #64748b;
        margin-bottom: 0.5rem;
    }
    .paper-summary {
        font-size: 0.88rem;
        color: #334155;
        line-height: 1.55;
        margin-bottom: 0.5rem;
    }
    .paper-finding {
        font-size: 0.85rem;
        color: #1e40af;
        font-weight: 500;
        background: #eff6ff;
        padding: 0.4rem 0.7rem;
        border-radius: 6px;
        border-left: 3px solid #3b82f6;
        margin-bottom: 0.5rem;
    }
    .tag {
        display: inline-block;
        background: #f1f5f9;
        color: #475569;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
        font-size: 0.72rem;
        font-family: 'JetBrains Mono', monospace;
        margin-right: 0.25rem;
    }
    .score-badge {
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        white-space: nowrap;
    }
    .score-high { background: #dcfce7; color: #166534; }
    .score-med  { background: #fef9c3; color: #854d0e; }
    .score-low  { background: #f1f5f9; color: #64748b; }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ── Helpers ─────────────────────────────────────────────────────────────────

def score_class(score: int) -> str:
    if score >= 7: return "score-high"
    if score >= 5: return "score-med"
    return "score-low"

def render_tags(tags_json: str) -> str:
    try:
        tags = json.loads(tags_json) if tags_json else []
    except json.JSONDecodeError:
        tags = []
    return " ".join(f'<span class="tag">{t}</span>' for t in tags)

def format_authors(authors_json: str, max_show: int = 3) -> str:
    try:
        authors = json.loads(authors_json) if authors_json else []
    except json.JSONDecodeError:
        authors = []
    if not authors: return "Unknown authors"
    if len(authors) <= max_show: return ", ".join(authors)
    return ", ".join(authors[:max_show]) + f" et al."


# ── Header + Filters (inline, no sidebar) ──────────────────────────────────

st.markdown("## 🧬 Neoantigen Vaccine Tracker")

stats = get_stats()
st.caption(f"{stats['total']} papers · {stats['high_relevance']} high relevance · {stats['starred']} starred")

# Compact filter row
col_score, col_source, col_starred = st.columns([2, 2, 1])

with col_score:
    min_score = st.select_slider(
        "Min relevance",
        options=list(range(1, 11)),
        value=5,
    )
with col_source:
    source_filter = st.selectbox(
        "Source",
        options=["All", "PubMed", "BioRxiv", "MedRxiv"],
        label_visibility="collapsed",
    )
with col_starred:
    show_starred_only = st.checkbox("⭐ only")

source_map = {"All": None, "PubMed": "pubmed", "BioRxiv": "biorxiv", "MedRxiv": "medrxiv"}

st.markdown("---")

# ── Load Papers ─────────────────────────────────────────────────────────────

papers = get_papers(
    min_score=min_score,
    limit=200,
    source=source_map[source_filter],
)

if show_starred_only:
    papers = [p for p in papers if p.get("starred")]


# ── Paper List ──────────────────────────────────────────────────────────────

if not papers:
    st.info("No papers found. Try lowering the relevance filter, or run `python3 run_pipeline.py` to fetch new papers.")
else:
    for paper in papers:
        score = paper.get("relevance_score") or 0
        cls = score_class(score)
        starred = "⭐ " if paper.get("starred") else ""

        title = paper.get("title") or "Untitled"
        authors = format_authors(paper.get("authors") or "[]")
        journal = paper.get("journal") or ""
        pub_date = paper.get("published_date") or ""
        key_finding = paper.get("key_finding") or ""
        summary = paper.get("summary") or ""
        tags = paper.get("tags") or "[]"

        # Card
        st.markdown(f"""
        <div class="paper-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem;">
                <div class="paper-title">{starred}{title}</div>
                <span class="score-badge {cls}">{score}/10</span>
            </div>
            <div class="paper-meta">
                {authors} · {journal} · {pub_date}
            </div>
            {"<div class='paper-finding'>💡 " + key_finding + "</div>" if key_finding else ""}
            {"<div class='paper-summary'>" + summary + "</div>" if summary else ""}
            <div>{render_tags(tags)}</div>
        </div>
        """, unsafe_allow_html=True)

        # Actions
        c1, c2, c3 = st.columns([1, 1, 6])
        with c1:
            star_label = "Unstar" if paper.get("starred") else "☆ Star"
            if st.button(star_label, key=f"star_{paper['id']}"):
                toggle_star(paper["id"])
                st.rerun()
        with c2:
            if paper.get("url"):
                st.link_button("Open ↗", paper["url"])

        # Expandable abstract + notes
        with st.expander("Abstract & notes"):
            st.markdown(paper.get("abstract") or "No abstract available.")
            notes = st.text_area(
                "Notes",
                value=paper.get("notes") or "",
                key=f"notes_{paper['id']}",
                placeholder="Add notes...",
                label_visibility="collapsed",
            )
            if st.button("Save", key=f"save_{paper['id']}"):
                update_notes(paper["id"], notes)
                st.success("Saved!")
