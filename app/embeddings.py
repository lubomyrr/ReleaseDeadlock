from functools import lru_cache


@lru_cache(maxsize=1)
def get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def generate_embeddings(texts: list[str]) -> list[list[float]]:
    return get_model().encode(texts).tolist()
