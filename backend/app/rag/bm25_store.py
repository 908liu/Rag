import re

from rank_bm25 import BM25Okapi


def tokenize(text: str) -> list[str]:
    normalized = re.sub(r"\s+", "", text.lower())
    latin_tokens = re.findall(r"[a-z0-9]+", normalized)
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", normalized)
    chinese_bigrams = [
        chinese_chars[index] + chinese_chars[index + 1]
        for index in range(len(chinese_chars) - 1)
    ]
    return latin_tokens + chinese_bigrams


def search(question: str, chunks: list[tuple[str, str]], limit: int) -> list[tuple[str, str, None]]:
    corpus_tokens = [tokenize(text) for _, text in chunks]
    query_tokens = tokenize(question)
    if not query_tokens or not any(corpus_tokens):
        return []

    scores = BM25Okapi(corpus_tokens).get_scores(query_tokens)
    query_token_set = set(query_tokens)
    matching_indices = [
        index for index, tokens in enumerate(corpus_tokens)
        if query_token_set.intersection(tokens)
    ]
    ranked_indices = sorted(matching_indices, key=lambda index: (-scores[index], index))[:limit]
    return [(chunks[index][0], chunks[index][1], None) for index in ranked_indices]