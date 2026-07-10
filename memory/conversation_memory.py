"""Per-user, in-memory conversation history.

Stores the last N (question, answer) pairs per user in a bounded deque. This is
process-local and resets on restart — acceptable for this project's scope.
"""

import logging
from collections import deque

from config import MEMORY_LAST_N

logger = logging.getLogger(__name__)

# user_id -> bounded deque of (question, answer) tuples.
_history: dict[int, deque[tuple[str, str]]] = {}


def add_exchange(user_id: int, question: str, answer: str) -> None:
    """Record one (question, answer) exchange for a user.

    Args:
        user_id: Telegram user id.
        question: The user's question.
        answer: The bot's answer.
    """
    if user_id not in _history:
        _history[user_id] = deque(maxlen=MEMORY_LAST_N)
    _history[user_id].append((question, answer))


def get_history(user_id: int) -> list[tuple[str, str]]:
    """Return the user's recent exchanges, oldest first.

    Args:
        user_id: Telegram user id.

    Returns:
        A list of (question, answer) pairs (empty if none recorded).
    """
    return list(_history.get(user_id, ()))


def clear(user_id: int) -> None:
    """Forget all conversation history for a user.

    Args:
        user_id: Telegram user id.
    """
    _history.pop(user_id, None)
    logger.info("Cleared conversation memory for user %s", user_id)
