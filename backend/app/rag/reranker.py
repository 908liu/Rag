import re


def _character_ngrams(text: str) -> set[str]:
    normalized = re.sub(r"\s+", "", text.lower())
    if len(normalized) < 2:
        return set(normalized)
    return {normalized[index : index + 2] for index in range(len(normalized) - 1)}


def rerank(question: str, matches: list[tuple[str, str, float | None]], limit: int):
    query_ngrams = _character_ngrams(question)
    if not query_ngrams:
        return matches[:limit]

    ranked = []
    match_count = len(matches)
    for index, match in enumerate(matches):
        _, text, distance = match
        overlap = len(query_ngrams & _character_ngrams(text)) / len(query_ngrams)
        semantic_score = max(0.0, min(1.0, 1.0 - distance)) if distance is not None else 0.0
        fusion_rank_score = 1.0 - index / max(match_count, 1)
        score = 0.35 * semantic_score + 0.55 * overlap + 0.10 * fusion_rank_score
        ranked.append((score, index, match))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [match for _, _, match in ranked[:limit]]