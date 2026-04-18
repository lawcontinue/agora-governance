"""
Precedent Store - Historical decision retrieval for governance consistency

Version: v1.1
License: Apache-2.0
"""

import json
import math
import os
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field


@dataclass
class Precedent:
    """Precedent data structure."""

    decision_id: str
    timestamp: str
    task_id: str
    description: str
    approved: bool
    stage: str
    reasoning: str
    local_reviews: Dict = field(default_factory=dict)
    global_votes: Optional[Dict] = None
    tmind_decision: Optional[Dict] = None
    precedent: bool = False
    precedent_weight: float = 0.0
    citation_count: int = 0
    tags: List[str] = field(default_factory=list)
    category: str = ""


def _tokenize(text: str) -> List[str]:
    """Simple whitespace + punctuation tokenizer."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return text.split()


def _compute_tf(tokens: List[str]) -> Dict[str, float]:
    """Compute term frequency."""
    if not tokens:
        return {}
    counts: Dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    total = len(tokens)
    return {t: c / total for t, c in counts.items()}


def _compute_idf(docs: List[List[str]]) -> Dict[str, float]:
    """Compute inverse document frequency (pure Python)."""
    n = len(docs)
    if n == 0:
        return {}
    df: Dict[str, int] = {}
    for doc in docs:
        seen = set(doc)
        for t in seen:
            df[t] = df.get(t, 0) + 1
    return {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}


def _tfidf_vector(tf: Dict[str, float], idf: Dict[str, float]) -> Dict[str, float]:
    """Compute TF-IDF vector."""
    return {t: tf.get(t, 0) * idf.get(t, 0) for t in idf}


def _cosine_sim(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Cosine similarity between two sparse vectors."""
    common = set(a.keys()) & set(b.keys())
    if not common:
        return 0.0
    dot = sum(a[k] * b[k] for k in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class PrecedentStore:
    """Precedent storage and retrieval with TF-IDF search."""

    def __init__(self, db_path: str = "precedents.jsonl"):
        self.db_path = db_path
        self.precedents: List[Precedent] = []
        self._idf: Dict[str, float] = {}
        self._doc_vectors: List[Dict[str, float]] = []

        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        self._load()

    def _load(self):
        if not os.path.exists(self.db_path):
            return
        with open(self.db_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    self.precedents.append(Precedent(**data))
                except (json.JSONDecodeError, TypeError):
                    continue
        self._build_index()

    def _save(self):
        with open(self.db_path, "w", encoding="utf-8") as f:
            for p in self.precedents:
                f.write(json.dumps(asdict(p), ensure_ascii=False) + "\n")

    def _build_index(self):
        """Build TF-IDF index (pure Python, no sklearn)."""
        if not self.precedents:
            self._idf = {}
            self._doc_vectors = []
            return

        docs = []
        for p in self.precedents:
            text = f"{p.reasoning} {' '.join(p.tags)} {p.description}"
            docs.append(_tokenize(text))

        # Fallback: if fewer than 2 docs, use simple string matching
        if len(docs) < 2:
            self._idf = {}
            self._doc_vectors = []
            return

        self._idf = _compute_idf(docs)
        self._doc_vectors = [_tfidf_vector(_compute_tf(d), self._idf) for d in docs]

    def add(self, precedent: Precedent):
        self.precedents.append(precedent)
        self._build_index()
        self._save()

    def search(self, query: str, threshold: float = 0.3, top_k: int = 10) -> List[Dict]:
        if not self.precedents:
            return []

        query_tokens = _tokenize(query)

        # Fallback for < 2 docs: simple substring matching
        if not self._idf:
            results = []
            query_lower = query.lower()
            for p in self.precedents:
                text = f"{p.reasoning} {' '.join(p.tags)} {p.description}".lower()
                if query_lower in text or any(t in text for t in query_tokens):
                    results.append({
                        "precedent": p,
                        "similarity": 0.5,
                        "weight": p.precedent_weight,
                    })
            results.sort(key=lambda x: x["weight"], reverse=True)
            return results[:top_k]

        # TF-IDF search
        query_tf = _compute_tf(query_tokens)
        query_vec = _tfidf_vector(query_tf, self._idf)

        results = []
        for idx, doc_vec in enumerate(self._doc_vectors):
            sim = _cosine_sim(query_vec, doc_vec)
            if sim >= threshold:
                results.append({
                    "precedent": self.precedents[idx],
                    "similarity": float(sim),
                    "weight": self.precedents[idx].precedent_weight,
                })

        results.sort(key=lambda x: (x["similarity"], x["weight"]), reverse=True)
        return results[:top_k]

    def get_by_id(self, decision_id: str) -> Optional[Precedent]:
        for p in self.precedents:
            if p.decision_id == decision_id:
                return p
        return None

    def update_weight(self, decision_id: str, weight: float):
        p = self.get_by_id(decision_id)
        if p:
            p.precedent_weight = max(0, min(weight, 5))
            self._save()

    def increment_citation(self, decision_id: str):
        p = self.get_by_id(decision_id)
        if p:
            p.citation_count += 1
            p.precedent_weight = _calculate_weight(p)
            self._save()

    def mark_as_precedent(self, decision_id: str, weight: float = 1.0):
        p = self.get_by_id(decision_id)
        if p:
            p.precedent = True
            p.precedent_weight = max(0, min(weight, 5))
            self._save()

    def get_stats(self) -> Dict:
        total = len(self.precedents)
        marked = sum(1 for p in self.precedents if p.precedent)
        avg_w = sum(p.precedent_weight for p in self.precedents) / total if total else 0
        return {
            "total_precedents": total,
            "marked_precedents": marked,
            "avg_weight": round(avg_w, 2),
        }


def _calculate_weight(precedent: Precedent) -> float:
    """Calculate precedent weight (0-5)."""
    if precedent.precedent:
        return float(precedent.precedent_weight)

    base = 1.0
    citation_bonus = precedent.citation_count * 0.5

    try:
        decision_time = datetime.fromisoformat(precedent.timestamp)
        age_months = (datetime.now() - decision_time).days / 30
        age_decay = min(age_months * 0.1, 2.0)
    except (ValueError, TypeError):
        age_decay = 0

    outcome_modifier = 1
    if precedent.global_votes:
        approve_count = sum(
            1 for v in precedent.global_votes.values()
            if isinstance(v, dict) and v.get("vote") == "approve"
        )
        outcome_modifier = 2 if approve_count >= 2 else 0

    return max(0, min(base + citation_bonus - age_decay + outcome_modifier, 5))
