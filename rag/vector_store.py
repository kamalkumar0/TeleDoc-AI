"""ChromaDB wrapper providing per-user, isolated vector collections.

Each Telegram user gets a collection named ``user_<telegram_user_id>``. ChromaDB
returns *distances*; we convert these to a similarity score (``1 - distance``)
and discard weak matches below ``SIMILARITY_THRESHOLD``.
"""

import logging

import chromadb

from config import CHROMA_PATH, SIMILARITY_THRESHOLD, TOP_K_CHUNKS

logger = logging.getLogger(__name__)

# A single persistent client is shared across the process.
_client = chromadb.PersistentClient(path=CHROMA_PATH)


def _collection_name(user_id: int) -> str:
    """Return the deterministic collection name for a user."""
    return f"user_{user_id}"


def _get_collection(user_id: int):
    """Get (or lazily create) the user's collection.

    The collection uses cosine distance so that ``score = 1 - distance`` in
    :func:`query` is a true cosine similarity in ``[-1, 1]``. (Chroma defaults to
    L2, which would make that conversion meaningless.)
    """
    return _client.get_or_create_collection(
        name=_collection_name(user_id),
        metadata={"hnsw:space": "cosine"},
    )


def add_document(
    user_id: int,
    filename: str,
    chunks: list[str],
    embeddings: list[list[float]],
) -> None:
    """Store a document's chunks and their embeddings in the user's collection.

    Args:
        user_id: Telegram user id (collection owner).
        filename: Original PDF filename, stored as chunk metadata.
        chunks: The text chunks.
        embeddings: One embedding vector per chunk (same order/length as chunks).
    """
    if not chunks:
        logger.warning("add_document called with no chunks for user %s", user_id)
        return

    collection = _get_collection(user_id)
    # IDs must be unique within the collection; namespace by filename + index.
    ids = [f"{filename}::{i}" for i in range(len(chunks))]
    metadatas = [
        {"user_id": user_id, "filename": filename, "chunk_index": i}
        for i in range(len(chunks))
    ]
    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    logger.info(
        "Stored %d chunks for user %s from '%s'", len(chunks), user_id, filename
    )


def query(
    user_id: int, query_embedding: list[float], top_k: int = TOP_K_CHUNKS
) -> list[dict]:
    """Retrieve the most similar chunks for a user's query.

    Args:
        user_id: Telegram user id.
        query_embedding: Embedding of the question.
        top_k: Maximum number of chunks to return.

    Returns:
        A list of ``{"text", "score", "source"}`` dicts sorted by descending
        similarity, filtered to those at/above ``SIMILARITY_THRESHOLD``. Empty
        list if the collection is empty or nothing clears the threshold.
    """
    collection = _get_collection(user_id)
    if collection.count() == 0:
        return []

    # Never request more results than exist, or Chroma logs a warning.
    n_results = min(top_k, collection.count())
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    # Chroma returns one list per query; we sent a single query.
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    matches: list[dict] = []
    for text, meta, distance in zip(documents, metadatas, distances):
        score = 1.0 - distance  # cosine distance -> similarity
        if score >= SIMILARITY_THRESHOLD:
            matches.append(
                {
                    "text": text,
                    "score": score,
                    "source": meta.get("filename", "unknown"),
                }
            )
    return matches


def list_documents(user_id: int) -> list[str]:
    """Return the distinct filenames the user has uploaded.

    Args:
        user_id: Telegram user id.

    Returns:
        A sorted list of unique filenames (empty if none).
    """
    collection = _get_collection(user_id)
    if collection.count() == 0:
        return []

    # Pull metadata only; we just need the filenames.
    records = collection.get(include=["metadatas"])
    filenames = {
        meta.get("filename")
        for meta in records["metadatas"]
        if meta.get("filename")
    }
    return sorted(filenames)


def clear_user(user_id: int) -> None:
    """Delete the user's entire collection (all their documents).

    Args:
        user_id: Telegram user id.
    """
    name = _collection_name(user_id)
    try:
        _client.delete_collection(name=name)
        logger.info("Deleted collection for user %s", user_id)
    except Exception as exc:
        # delete_collection raises if it does not exist; that is a no-op for us.
        logger.info("No collection to delete for user %s (%s)", user_id, exc)
