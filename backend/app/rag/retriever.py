from app.rag import vector_repository
from app.rag.bm25_store import search as bm25_search


RRF_K = 60


def retrieve_candidates(user_id: int, question: str, limit: int = 20):
    vector_matches = vector_repository.search_chunks(user_id, question, limit)
    user_chunks = vector_repository.get_user_chunks(user_id)
    if not user_chunks:
        return vector_matches

    bm25_matches = bm25_search(question, user_chunks, limit)
    if not bm25_matches:
        return vector_matches

    fused_scores = {}
    fused_matches = {}
    for rank, match in enumerate([*vector_matches, *bm25_matches], start=1):
        filename, text, distance = match
        key = (filename, text)
        fused_matches.setdefault(key, match)
        fused_scores[key] = fused_scores.get(key, 0.0) + 1 / (RRF_K + rank)

    ordered_keys = sorted(fused_scores, key=lambda key: (-fused_scores[key], key[0], key[1]))
    return [fused_matches[key] for key in ordered_keys[: limit * 2]]