from app.rag import vector_repository


class FakeCollection:
    def __init__(self) -> None:
        self.items = [
            {
                "text": "alice private document",
                "metadata": {"user_id": 1, "filename": "alice.txt"},
                "distance": 0.1,
            },
            {
                "text": "bob private document",
                "metadata": {"user_id": 2, "filename": "bob.txt"},
                "distance": 0.1,
            },
        ]
        self.last_query_where = None
        self.last_count_where = None

    def count(self, where=None):
        self.last_count_where = where
        return sum(item["metadata"]["user_id"] == where["user_id"] for item in self.items)

    def get(self, where, include):
        self.last_query_where = where
        selected = [item for item in self.items if item["metadata"]["user_id"] == where["user_id"]]
        return {
            "documents": [item["text"] for item in selected],
            "metadatas": [item["metadata"] for item in selected],
        }

    def query(self, query_texts, n_results, where, include):
        self.last_query_where = where
        selected = [item for item in self.items if item["metadata"]["user_id"] == where["user_id"]]
        selected = selected[:n_results]
        return {
            "documents": [[item["text"] for item in selected]],
            "metadatas": [[item["metadata"] for item in selected]],
            "distances": [[item["distance"] for item in selected]],
        }


def test_vector_queries_are_scoped_to_user(monkeypatch) -> None:
    collection = FakeCollection()
    monkeypatch.setattr(vector_repository, "_get_collection", lambda: collection)

    alice_chunks = vector_repository.get_user_chunks(user_id=1)
    alice_matches = vector_repository.search_chunks(user_id=1, question="private", limit=5)

    assert alice_chunks == [("alice.txt", "alice private document")]
    assert alice_matches == [("alice.txt", "alice private document", 0.1)]
    assert collection.last_count_where == {"user_id": 1}
    assert collection.last_query_where == {"user_id": 1}
