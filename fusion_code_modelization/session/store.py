from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from ..core.config import DEFAULT_LOCAL_MODEL
from ..core.hooks import scrub_secrets
from .state import Session, SessionConfig, SessionMessage, SessionState

logger = logging.getLogger(__name__)

_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,128}$")


def _validate_session_id(session_id: str) -> str:
    if not isinstance(session_id, str) or not _SESSION_ID_RE.match(session_id):
        logger.warning("rejected invalid session_id: %r", session_id)
        raise ValueError(f"invalid session_id: {session_id!r}")
    return session_id


class SessionStore:
    def __init__(self, base_dir: str | Path = ".fusion/sessions"):
        self._base_dir = Path(base_dir).expanduser().resolve()
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, session: Session) -> None:
        session.updated_at = time.time()
        path = self._session_path(session.session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = session.to_dict()
        for msg in data.get("messages", []):
            msg["content"] = scrub_secrets(str(msg.get("content", "")))
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.debug("Session saved: %s", session.session_id)

    def load(self, session_id: str) -> Session | None:
        try:
            path = self._session_path(session_id)
        except ValueError:
            logger.warning("rejected load invalid session_id: %r", session_id)
            return None
        if not path.exists():
            logger.warning("Session not found: %s", session_id)
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return self._from_dict(data)
        except Exception as e:
            logger.error("Failed to load session %s: %s", session_id, e)
            return None

    def delete(self, session_id: str) -> bool:
        try:
            path = self._session_path(session_id)
        except ValueError:
            logger.warning("rejected delete invalid session_id: %r", session_id)
            return False
        if path.exists():
            path.unlink()
            logger.info("Session deleted: %s", session_id)
            return True
        return False

    def list_sessions(self) -> list[Session]:
        sessions = []
        for path in self._base_dir.rglob("session.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                sessions.append(self._from_dict(data))
            except Exception as e:
                logger.warning("Failed to parse %s: %s", path, e)
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    def list_by_state(self, state: SessionState) -> list[Session]:
        return [s for s in self.list_sessions() if s.state == state]

    def _session_path(self, session_id: str) -> Path:
        _validate_session_id(session_id)
        return self._base_dir / session_id / "session.json"

    @staticmethod
    def _from_dict(data: dict[str, Any]) -> Session:
        config_data = data.get("config", {})
        config = SessionConfig(
            session_id=data.get("session_id", ""),
            name=data.get("name", ""),
            working_dir=config_data.get("working_dir", ""),
            model=config_data.get("model", DEFAULT_LOCAL_MODEL),
            temperature=config_data.get("temperature", 0.1),
            max_tokens=config_data.get("max_tokens", 4096),
            security_mode=config_data.get("security_mode", "manual"),
            allowed_dirs=config_data.get("allowed_dirs", []),
            cluster_nodes=config_data.get("cluster_nodes", []),
        )
        messages = [
            SessionMessage(
                role=m.get("role", ""),
                content=m.get("content", ""),
                timestamp=m.get("timestamp", 0.0),
            )
            for m in data.get("messages", [])
        ]
        return Session(
            session_id=data.get("session_id", ""),
            name=data.get("name", ""),
            state=SessionState(data.get("state", "idle")),
            config=config,
            messages=messages,
            created_at=data.get("created_at", 0.0),
            updated_at=data.get("updated_at", 0.0),
            error=data.get("error", ""),
        )
