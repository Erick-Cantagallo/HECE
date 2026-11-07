# HECE/src/hece/tools.py
import hashlib
import json
import os
import re
import time
from typing import List, Optional

import arxiv


def _arxiv_id(entry_id) -> str:
    """'http://arxiv.org/abs/2401.01234v2' -> '2401.01234'."""
    return re.sub(r"v\d+$", "", str(entry_id).split("/abs/")[-1])


def _stem(keyword: str) -> str:
    """Crude stem so 'battery' also matches 'batteries' and 'membrane' matches 'membranes'."""
    k = keyword.lower()
    if k.endswith("y") and len(k) > 4:
        return k[:-1]
    return k[:-1] if k.endswith("e") and len(k) > 5 else k


class ScientificToolbox:
    """
    A collection of external tools to fetch real-world data for RAG.
    """
    last_error: Optional[str] = None      # set when the last search FAILED (vs. simply found nothing)
    RETRY_DELAYS = (5, 15)                # seconds to wait before each retry (e.g. after an HTTP 503)
    cache_dir: str = ".hece_cache"        # successful searches are cached here (only when use_cache=True)
    CACHE_TTL_SECONDS = 7 * 24 * 3600

    # ---------------------------------------------------------------- cache (spares the arXiv API)
    @staticmethod
    def _cache_file(query: str, max_results: int, keywords: Optional[List[str]]) -> str:
        key = json.dumps([query.lower().strip(), max_results, sorted(k.lower() for k in (keywords or []))])
        return os.path.join(ScientificToolbox.cache_dir, hashlib.sha1(key.encode("utf-8")).hexdigest() + ".json")

    @staticmethod
    def _cache_get(path: str) -> Optional[str]:
        try:
            with open(path, encoding="utf-8") as fh:
                entry = json.load(fh)
            if time.time() - float(entry["ts"]) <= ScientificToolbox.CACHE_TTL_SECONDS:
                return str(entry["text"])
        except (OSError, ValueError, KeyError):
            pass
        return None

    @staticmethod
    def _cache_put(path: str, text: str) -> None:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"ts": time.time(), "text": text}, fh)
        except OSError:
            pass  # a cache that cannot be written must never break a run

    # ---------------------------------------------------------------- search
    @staticmethod
    def _search_once(query: str, max_results: int, keywords: Optional[List[str]]) -> str:
        fetch = max(10, max_results * 5) if keywords else max_results
        try:
            # smaller pages and one library-level retry: be gentle with the API (we retry ourselves)
            client = arxiv.Client(page_size=fetch, delay_seconds=3.0, num_retries=1)
        except TypeError:
            client = arxiv.Client()          # older arxiv versions without these arguments
        search = arxiv.Search(query=query, max_results=fetch, sort_by=arxiv.SortCriterion.Relevance)

        needed = min(2, len(keywords)) if keywords else 0
        found = []   # (relevance, arrival order, title, id, summary)
        for order, paper in enumerate(client.results(search)):
            title = " ".join(str(paper.title).split())
            summary = str(paper.summary)
            if keywords:
                in_title = sum(1 for k in keywords if _stem(k) in title.lower())
                in_text = sum(1 for k in keywords if _stem(k) in f"{title} {summary}".lower())
                if in_text < needed:
                    continue
                relevance = 2 * in_title + in_text     # a keyword in the title says more than one in the abstract
            else:
                relevance = 0
            found.append((relevance, order, title, _arxiv_id(paper.entry_id), summary))
            if not keywords and len(found) >= max_results:
                break

        # Re-rank what was fetched (no extra request): most keywords first, arXiv's own order breaks ties.
        best = sorted(found, key=lambda f: (-f[0], f[1]))[:max_results]
        if not best:
            return ""
        return "REAL SCIENTIFIC LITERATURE RETRIEVED:\n" + "".join(
            f"\n- [{n}] Title: {title}\n  ID: {pid}\n  Summary: {summary}\n" for n, (_, _, title, pid, summary) in enumerate(best, 1))

    @staticmethod
    def search_arxiv(query: str, max_results: int = 2, keywords: Optional[List[str]] = None,
                     use_cache: bool = False) -> str:
        """
        Searches ArXiv and returns titles, IDs and abstracts.
        If `keywords` is given, a paper is kept only when at least min(2, len(keywords)) of them
        appear in its title/abstract. Transient failures (e.g. HTTP 503) are retried with a delay;
        HTTP 429 (rate limit) is NOT retried, because retrying is what makes it worse.
        With use_cache=True, successful searches (including "nothing relevant") are reused for 7 days.
        Returns "" when nothing relevant is found or when every attempt failed
        (the latter also sets ScientificToolbox.last_error).
        """
        ScientificToolbox.last_error = None
        cache_path = ScientificToolbox._cache_file(query, max_results, keywords) if use_cache else None
        if cache_path:
            cached = ScientificToolbox._cache_get(cache_path)
            if cached is not None:
                print("    -> [RAG] Using cached ArXiv result (no request sent).")
                return cached

        delays = (0,) + tuple(ScientificToolbox.RETRY_DELAYS)
        for delay in delays:
            if delay:
                print(f"    -> [RAG] Retrying ArXiv in {delay}s...")
                time.sleep(delay)
            try:
                result = ScientificToolbox._search_once(query, max_results, keywords)
                ScientificToolbox.last_error = None
                if cache_path:
                    ScientificToolbox._cache_put(cache_path, result)
                return result
            except Exception as exc:
                ScientificToolbox.last_error = f"{type(exc).__name__}: {exc}"
                print(f"    -> [RAG] ArXiv search FAILED: {ScientificToolbox.last_error}")
                if "429" in str(exc):
                    print("    -> [RAG] Rate limited by ArXiv: not retrying (try again in a few minutes, or untick the ArXiv option).")
                    break
        return ""
