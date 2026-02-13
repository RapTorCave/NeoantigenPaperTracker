"""
Database layer for storing and querying papers.
Uses SQLite for simplicity — no external database needed.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from config import DB_PATH


def get_connection():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS papers (
            id TEXT PRIMARY KEY,           -- PubMed ID or BioRxiv DOI
            source TEXT NOT NULL,          -- 'pubmed' or 'biorxiv'
            title TEXT NOT NULL,
            authors TEXT,                  -- JSON list of author names
            abstract TEXT,
            journal TEXT,
            published_date TEXT,
            url TEXT,
            doi TEXT,
            
            -- LLM-generated fields
            relevance_score INTEGER,
            summary TEXT,
            key_finding TEXT,
            tags TEXT,                     -- JSON list of tags
            
            -- Metadata
            fetched_at TEXT NOT NULL,
            scored_at TEXT,
            
            -- User interaction
            starred INTEGER DEFAULT 0,
            notes TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_papers_relevance ON papers(relevance_score DESC);
        CREATE INDEX IF NOT EXISTS idx_papers_published ON papers(published_date DESC);
        CREATE INDEX IF NOT EXISTS idx_papers_source ON papers(source);
    """)
    conn.commit()
    conn.close()


def paper_exists(paper_id: str) -> bool:
    """Check if a paper is already in the database."""
    conn = get_connection()
    row = conn.execute("SELECT 1 FROM papers WHERE id = ?", (paper_id,)).fetchone()
    conn.close()
    return row is not None


def insert_paper(paper: dict):
    """Insert a new paper into the database."""
    conn = get_connection()
    conn.execute("""
        INSERT OR IGNORE INTO papers 
        (id, source, title, authors, abstract, journal, published_date, url, doi, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        paper["id"],
        paper["source"],
        paper["title"],
        json.dumps(paper.get("authors", [])),
        paper.get("abstract", ""),
        paper.get("journal", ""),
        paper.get("published_date", ""),
        paper.get("url", ""),
        paper.get("doi", ""),
        datetime.utcnow().isoformat(),
    ))
    conn.commit()
    conn.close()


def update_paper_scoring(paper_id: str, relevance_score: int, summary: str, key_finding: str, tags: list):
    """Update a paper with LLM-generated relevance score and summary."""
    conn = get_connection()
    conn.execute("""
        UPDATE papers 
        SET relevance_score = ?, summary = ?, key_finding = ?, tags = ?, scored_at = ?
        WHERE id = ?
    """, (
        relevance_score,
        summary,
        key_finding,
        json.dumps(tags),
        datetime.utcnow().isoformat(),
        paper_id,
    ))
    conn.commit()
    conn.close()


def get_unscored_papers() -> list[dict]:
    """Get papers that haven't been scored yet."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM papers WHERE relevance_score IS NULL ORDER BY fetched_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_papers(min_score: int = 1, limit: int = 100, source: str = None, tag: str = None) -> list[dict]:
    """Get scored papers, filtered and sorted by relevance."""
    query = "SELECT * FROM papers WHERE relevance_score >= ?"
    params = [min_score]
    
    if source:
        query += " AND source = ?"
        params.append(source)
    
    if tag:
        query += " AND tags LIKE ?"
        params.append(f'%"{tag}"%')
    
    query += " ORDER BY published_date DESC, relevance_score DESC LIMIT ?"
    params.append(limit)
    
    conn = get_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def toggle_star(paper_id: str):
    """Toggle the starred status of a paper."""
    conn = get_connection()
    conn.execute(
        "UPDATE papers SET starred = CASE WHEN starred = 1 THEN 0 ELSE 1 END WHERE id = ?",
        (paper_id,)
    )
    conn.commit()
    conn.close()


def update_notes(paper_id: str, notes: str):
    """Update user notes for a paper."""
    conn = get_connection()
    conn.execute("UPDATE papers SET notes = ? WHERE id = ?", (notes, paper_id))
    conn.commit()
    conn.close()


def get_stats() -> dict:
    """Get summary statistics for the dashboard."""
    conn = get_connection()
    stats = {}
    stats["total"] = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    stats["scored"] = conn.execute("SELECT COUNT(*) FROM papers WHERE relevance_score IS NOT NULL").fetchone()[0]
    stats["high_relevance"] = conn.execute("SELECT COUNT(*) FROM papers WHERE relevance_score >= 7").fetchone()[0]
    stats["starred"] = conn.execute("SELECT COUNT(*) FROM papers WHERE starred = 1").fetchone()[0]
    stats["sources"] = dict(conn.execute(
        "SELECT source, COUNT(*) FROM papers GROUP BY source"
    ).fetchall()) if stats["total"] > 0 else {}
    conn.close()
    return stats
