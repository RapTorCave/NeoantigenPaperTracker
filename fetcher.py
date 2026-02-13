"""
Fetches papers from PubMed and BioRxiv APIs.
No API key required for either service.
"""

import requests
import xml.etree.ElementTree as ET
import time
from datetime import datetime, timedelta
from config import PUBMED_QUERIES, BIORXIV_QUERIES, LOOKBACK_DAYS, MAX_PAPERS_PER_RUN
from database import paper_exists, insert_paper


# ── PubMed (NCBI E-utilities) ──────────────────────────────────────────────

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def _pubmed_search(query: str, max_results: int = 20) -> list[str]:
    """Search PubMed and return a list of PMIDs."""
    date_from = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y/%m/%d")
    date_to = datetime.now().strftime("%Y/%m/%d")

    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "sort": "date",
        "datetype": "pdat",
        "mindate": date_from,
        "maxdate": date_to,
        "retmode": "json",
    }

    try:
        resp = requests.get(PUBMED_SEARCH_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print(f"  ⚠ PubMed search error for '{query}': {e}")
        return []


def _pubmed_fetch_details(pmids: list[str]) -> list[dict]:
    """Fetch full details for a list of PMIDs."""
    if not pmids:
        return []

    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
    }

    try:
        resp = requests.get(PUBMED_FETCH_URL, params=params, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"  ⚠ PubMed fetch error: {e}")
        return []

    papers = []
    root = ET.fromstring(resp.content)

    for article in root.findall(".//PubmedArticle"):
        try:
            medline = article.find(".//MedlineCitation")
            pmid = medline.findtext(".//PMID")
            art = medline.find(".//Article")

            title = art.findtext(".//ArticleTitle", "No title")

            # Authors
            authors = []
            for author in art.findall(".//Author"):
                last = author.findtext("LastName", "")
                first = author.findtext("ForeName", "")
                if last:
                    authors.append(f"{first} {last}".strip())

            # Abstract
            abstract_parts = []
            for abs_text in art.findall(".//Abstract/AbstractText"):
                label = abs_text.get("Label", "")
                text = abs_text.text or ""
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
            abstract = " ".join(abstract_parts)

            # Journal
            journal = art.findtext(".//Journal/Title", "")

            # Date
            pub_date = medline.find(".//DateCompleted") or medline.find(".//DateRevised")
            if pub_date is not None:
                year = pub_date.findtext("Year", "")
                month = pub_date.findtext("Month", "01")
                day = pub_date.findtext("Day", "01")
                published_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            else:
                published_date = ""

            # DOI
            doi = ""
            for eid in article.findall(".//ArticleIdList/ArticleId"):
                if eid.get("IdType") == "doi":
                    doi = eid.text or ""
                    break

            papers.append({
                "id": f"pubmed:{pmid}",
                "source": "pubmed",
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "journal": journal,
                "published_date": published_date,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "doi": doi,
            })
        except Exception as e:
            print(f"  ⚠ Error parsing PubMed article: {e}")
            continue

    return papers


def fetch_pubmed() -> list[dict]:
    """Fetch recent papers from PubMed across all configured queries."""
    all_pmids = set()
    print("📚 Fetching from PubMed...")

    for query in PUBMED_QUERIES:
        pmids = _pubmed_search(query)
        new_pmids = [p for p in pmids if f"pubmed:{p}" not in all_pmids and not paper_exists(f"pubmed:{p}")]
        all_pmids.update(pmids)
        print(f"  Query '{query}': {len(pmids)} results, {len(new_pmids)} new")
        time.sleep(0.35)  # Be respectful to NCBI servers

    # Filter to only new papers
    new_pmids = [p for p in all_pmids if not paper_exists(f"pubmed:{p}")]
    print(f"  Total unique new PMIDs: {len(new_pmids)}")

    if not new_pmids:
        return []

    # Fetch in batches of 20
    papers = []
    for i in range(0, len(new_pmids), 20):
        batch = list(new_pmids)[i:i + 20]
        papers.extend(_pubmed_fetch_details(batch))
        time.sleep(0.35)

    return papers


# ── BioRxiv / MedRxiv ──────────────────────────────────────────────────────

BIORXIV_API_URL = "https://api.biorxiv.org/details"


def _biorxiv_search(server: str = "biorxiv") -> list[dict]:
    """Fetch recent papers from BioRxiv or MedRxiv."""
    date_from = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    date_to = datetime.now().strftime("%Y-%m-%d")
    url = f"{BIORXIV_API_URL}/{server}/{date_from}/{date_to}/0/100"

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("collection", [])
    except Exception as e:
        print(f"  ⚠ {server} fetch error: {e}")
        return []


def _matches_query(paper: dict, queries: list[str]) -> bool:
    """Check if a paper matches any of the search queries (case-insensitive)."""
    searchable = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    return any(q.lower() in searchable for q in queries)


def fetch_biorxiv() -> list[dict]:
    """Fetch recent relevant papers from BioRxiv and MedRxiv."""
    papers = []
    
    for server in ["biorxiv", "medrxiv"]:
        print(f"📄 Fetching from {server}...")
        raw_papers = _biorxiv_search(server)
        print(f"  Retrieved {len(raw_papers)} recent papers")

        for p in raw_papers:
            doi = p.get("doi", "")
            paper_id = f"{server}:{doi}"

            if not doi or paper_exists(paper_id):
                continue

            if not _matches_query(p, BIORXIV_QUERIES):
                continue

            authors_raw = p.get("authors", "")
            authors = [a.strip() for a in authors_raw.split(";") if a.strip()] if authors_raw else []

            papers.append({
                "id": paper_id,
                "source": server,
                "title": p.get("title", "No title"),
                "authors": authors,
                "abstract": p.get("abstract", ""),
                "journal": f"{server} (preprint)",
                "published_date": p.get("date", ""),
                "url": f"https://doi.org/{doi}" if doi else "",
                "doi": doi,
            })

        print(f"  Matched {len([pp for pp in papers if pp['source'] == server])} relevant papers")

    return papers


# ── Main Fetch Pipeline ────────────────────────────────────────────────────

def fetch_all() -> int:
    """Run the full fetch pipeline. Returns count of new papers added."""
    print("=" * 60)
    print(f"🔬 Neoantigen Vaccine Paper Fetch — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    all_papers = []

    # PubMed
    pubmed_papers = fetch_pubmed()
    all_papers.extend(pubmed_papers)

    # BioRxiv + MedRxiv
    biorxiv_papers = fetch_biorxiv()
    all_papers.extend(biorxiv_papers)

    # Deduplicate by DOI (in case same paper appears in multiple sources)
    seen_dois = set()
    unique_papers = []
    for p in all_papers:
        doi = p.get("doi", "")
        if doi and doi in seen_dois:
            continue
        if doi:
            seen_dois.add(doi)
        unique_papers.append(p)

    # Limit to max per run
    unique_papers = unique_papers[:MAX_PAPERS_PER_RUN]

    # Store in database
    for p in unique_papers:
        insert_paper(p)

    print(f"\n✅ Added {len(unique_papers)} new papers to database")
    return len(unique_papers)


if __name__ == "__main__":
    fetch_all()
