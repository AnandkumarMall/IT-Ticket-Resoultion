"""
nlp_service.py
--------------
Reusable NLP recommendation engine.
Converts nlp_engine.ipynb logic into a standalone Python service.

NO LLM. NO summarisation.
Uses TF-IDF vectorization + cosine similarity only.
Returns top-k matching historical tickets with their resolution text.
"""

import os
import re

import nltk
import pandas as pd
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ---------------------------------------------------------------------------
# Download NLTK resources (runs once; skips if already present)
# ---------------------------------------------------------------------------
nltk.download("stopwords", quiet=True)
nltk.download("wordnet", quiet=True)

_stop_words = set(stopwords.words("english"))
_lemmatizer = WordNetLemmatizer()

# Path to the historical ticket dataset (relative to this file)
_DATA_PATH = os.path.join(
    os.path.dirname(__file__),   # backend/
    "..",                         # IT_Ticket Resoultion - Copy/
    "data",
    "enterprise_synthetic_tickets.csv",
)


# ===========================================================================
#  TEXT CLEANING
# ===========================================================================

def _clean_text(text: str) -> str:
    """
    Lowercase → remove non-alpha chars → tokenise →
    remove stop-words (len > 2) → lemmatise → rejoin.
    """
    text = str(text).lower()
    text = re.sub(r"[^a-zA-Z\s]", "", text)
    tokens = text.split()
    tokens = [
        _lemmatizer.lemmatize(word)
        for word in tokens
        if word not in _stop_words and len(word) > 2
    ]
    return " ".join(tokens)


# ===========================================================================
#  VECTORIZER (loaded once at module import time)
# ===========================================================================

class _TicketVectorizer:
    """
    Loads the CSV, deduplicates descriptions, cleans text and fits
    a TF-IDF model with unigrams + bigrams.
    """

    def __init__(self, filepath: str):
        self.df = pd.read_csv(filepath)

        # Remove duplicate descriptions to avoid identical top results
        self.df = self.df.drop_duplicates(subset=["description"]).reset_index(drop=True)

        # Clean every description
        self.df["cleaned"] = self.df["description"].apply(_clean_text)

        # Fit TF-IDF with bigrams for richer matching
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_df=0.95,
            min_df=1,
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.df["cleaned"])
        print(f"[NLP] Vectorizer fitted on {len(self.df)} unique historical tickets.")

    def transform_query(self, query: str):
        """Transform a raw query string into a TF-IDF vector."""
        cleaned = _clean_text(query)
        return self.vectorizer.transform([cleaned])


# Singleton — fitted once when the module is first imported
_vectorizer = _TicketVectorizer(_DATA_PATH)


# ===========================================================================
#  PUBLIC API
# ===========================================================================

def get_top_similar_tickets(description: str, top_k: int = 3, threshold: float = 0.10):
    """
    Return the top-k most similar historical tickets for a given description.

    Parameters
    ----------
    description : str
        The new (incoming) ticket description.
    top_k : int
        Maximum number of results to return (default 3).
    threshold : float
        Minimum similarity score to include a result (default 0.10).

    Returns
    -------
    list[dict]
        Each dict contains:
            ticket_id, description, category, priority, resolution,
            similarity_score
    """
    query_vec = _vectorizer.transform_query(description)

    similarities = cosine_similarity(
        query_vec,
        _vectorizer.tfidf_matrix,
    ).flatten()

    # Optional boost / penalty for category keyword match in query
    query_lower = description.lower()
    df = _vectorizer.df

    for idx, row in df.iterrows():
        category = str(row.get("category", "")).lower()
        if category and category in query_lower:
            similarities[idx] = min(similarities[idx] * 1.25, 1.0)  # boost
        else:
            similarities[idx] = similarities[idx] * 0.90             # slight penalty

    # Sort descending and pick top_k above threshold
    sorted_indices = similarities.argsort()[::-1]

    results = []
    for idx in sorted_indices:
        if similarities[idx] < threshold:
            continue

        row = df.iloc[idx]
        results.append(
            {
                "ticket_id":       int(row["ticket_id"]),
                "description":     str(row["description"]),
                "category":        str(row.get("category", "")),
                "priority":        str(row.get("priority", "")),
                "resolution":      str(row["resolution"]),
                "similarity_score": round(float(similarities[idx]), 4),
            }
        )

        if len(results) == top_k:
            break

    return results
