"""Session context management tool.

New architecture:
- One JSON file per user (`{user_id}.json`)
- Inside each file, multiple sessions keyed by session_id
This supports an omnichannel experience: memory is user-centric,
with branches per session (channel).
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from app.config import MEMORY_DIR, USER_DIR

# Memory bounds to prevent unbounded growth
MAX_MESSAGE_HISTORY = 10  # Keep last N messages per session
MAX_TRACE_HISTORY = 5  # Keep last N execution traces per session


def _get_user_file(user_id: str) -> Path:
    """Return the path to the user's memory file."""
    return MEMORY_DIR / f"{user_id}.json"


def _load_user_memory(user_id: str) -> Dict[str, Any]:
    """
    Load full memory for a user (sessions only).

    Structure:
    {
        "user_id": "001",
        "sessions": { ... }  # per-session conversational context
    }
    
    Note: Personalization is stored separately in app/memory/User/{user_id}.json
    """
    user_file = _get_user_file(user_id)
    if not user_file.exists():
        return {"user_id": user_id, "sessions": {}}
    try:
        with open(user_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"user_id": user_id, "sessions": {}}
            data.setdefault("user_id", user_id)
            data.setdefault("sessions", {})
            return data
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading user memory for {user_id}: {e}")
        return {"user_id": user_id, "sessions": {}}


def _save_user_memory(user_id: str, memory: Dict[str, Any]) -> None:
    """Persist full memory for a user."""
    user_file = _get_user_file(user_id)
    try:
        with open(user_file, "w", encoding="utf-8") as f:
            json.dump(memory, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving user memory for {user_id}: {e}")
        raise


def get_session_context(user_id: str, session_id: str) -> Dict[str, Any]:
    """
    Retrieve session context for a given user and session.
    
    Args:
        user_id: User identifier
        session_id: Session identifier (channel/interaction)
        
    Returns:
        Dictionary containing session context, empty dict if not found
    """
    memory = _load_user_memory(user_id)
    sessions = memory.get("sessions", {})
    return sessions.get(session_id, {})


def save_session_context(user_id: str, session_id: str, context: Dict[str, Any]) -> None:
    """
    Save session context for a given user and session with bounded growth.
    
    Args:
        user_id: User identifier
        session_id: Session identifier
        context: Dictionary containing session context to save
    """
    memory = _load_user_memory(user_id)
    sessions = memory.setdefault("sessions", {})
    
    # Bound memory growth at the session level
    bounded_context = _bound_context(context)
    sessions[session_id] = bounded_context
    memory["user_id"] = user_id
    
    _save_user_memory(user_id, memory)


def get_user_memory(user_id: str) -> Dict[str, Any]:
    """Return full memory for a user (all sessions)."""
    return _load_user_memory(user_id)


def _get_user_personalization_file(user_id: str) -> Path:
    """Return the path to the user's personalization file (separate from sessions)."""
    return USER_DIR / f"{user_id}.json"


def _load_user_personalization(user_id: str) -> Dict[str, Any]:
    """Load personalization data from the User directory."""
    user_file = _get_user_personalization_file(user_id)
    if not user_file.exists():
        return {}
    try:
        with open(user_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading personalization for user {user_id}: {e}")
        return {}


def _save_user_personalization(user_id: str, personalization: Dict[str, Any]) -> None:
    """Save personalization data to the User directory."""
    user_file = _get_user_personalization_file(user_id)
    try:
        with open(user_file, "w", encoding="utf-8") as f:
            json.dump(personalization, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving personalization for user {user_id}: {e}")
        raise


def get_personalization(user_id: str) -> Dict[str, Any]:
    """
    Return personalization storage for a user.

    This is stored separately from sessions in app/memory/User/{user_id}.json.
    Intended for unstructured, longer-lived user information such as:
    - gender / style preferences
    - preferred sizes
    - orders currently being processed
    - any other stable attributes inferred from interactions
    """
    return _load_user_personalization(user_id)


def save_personalization(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge updates into the user's personalization storage.

    Args:
        user_id: User identifier
        updates: Arbitrary key/value pairs to upsert

    Returns:
        The updated personalization dictionary.
    """
    if updates is None:
        updates = {}

    personalization = _load_user_personalization(user_id)
    personalization.update(updates)
    _save_user_personalization(user_id, personalization)
    return personalization


def update_personalization(user_id: str, insights: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update personalization based on insights learned from conversation.
    
    This tool allows the LLM to learn from daily chats and update user preferences,
    such as gender, preferred sizes, style preferences, orders being processed, etc.
    
    Args:
        user_id: User identifier
        insights: Dictionary of personalization insights to update. Common keys:
            - gender: "male" | "female" | "other"
            - preferred_size: "XS" | "S" | "M" | "L" | "XL" | "XXL"
            - style_preferences: List[str] (e.g., ["casual", "sporty"])
            - orders_being_processed: List[Dict] (order tracking)
            - any other unstructured user attributes
    
    Returns:
        The updated personalization dictionary.
    """
    if not insights:
        return _load_user_personalization(user_id)
    
    return save_personalization(user_id, insights)


def clear_session(user_id: str, session_id: str) -> Dict[str, Any]:
    """
    Clear a specific session for a user.
    
    Returns a simple status dict.
    """
    memory = _load_user_memory(user_id)
    sessions = memory.get("sessions", {})
    if session_id in sessions:
        sessions.pop(session_id, None)
        _save_user_memory(user_id, memory)
        return {"status": "cleared"}
    return {"status": "not_found"}


def clear_user_memory(user_id: str) -> Dict[str, Any]:
    """
    Delete the entire memory file for a user (both sessions and personalization).
    
    Intended to be called when a user is deleted from the database
    to keep DB and simple memory fully in sync (DB-first).
    """
    cleared_sessions = False
    cleared_personalization = False
    
    # Clear sessions file
    user_file = _get_user_file(user_id)
    if user_file.exists():
        try:
            user_file.unlink()
            cleared_sessions = True
        except OSError as e:
            print(f"Error deleting sessions file for user {user_id}: {e}")
    
    # Clear personalization file
    personalization_file = _get_user_personalization_file(user_id)
    if personalization_file.exists():
        try:
            personalization_file.unlink()
            cleared_personalization = True
        except OSError as e:
            print(f"Error deleting personalization file for user {user_id}: {e}")
    
    if cleared_sessions or cleared_personalization:
        return {"status": "cleared", "sessions": cleared_sessions, "personalization": cleared_personalization}
    return {"status": "not_found"}


def _bound_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bound context growth by capping history and traces.
    
    Args:
        context: Original context dictionary
        
    Returns:
        Bounded context dictionary
    """
    bounded = context.copy()
    
    # Cap message history
    if "message_history" in bounded and isinstance(bounded["message_history"], list):
        bounded["message_history"] = bounded["message_history"][-MAX_MESSAGE_HISTORY:]
    
    # Cap trace history
    if "trace_history" in bounded and isinstance(bounded["trace_history"], list):
        bounded["trace_history"] = bounded["trace_history"][-MAX_TRACE_HISTORY:]
    
    # Cap step results (keep only recent ones)
    step_keys = [k for k in bounded.keys() if k.startswith("step_")]
    if len(step_keys) > MAX_MESSAGE_HISTORY:
        # Sort by step number and keep only recent
        step_keys_sorted = sorted(
            step_keys,
            key=lambda x: int(x.split("_")[1]) if x.split("_")[1].isdigit() else 0,
        )
        for key in step_keys_sorted[:-MAX_MESSAGE_HISTORY]:
            bounded.pop(key, None)
    
    return bounded

