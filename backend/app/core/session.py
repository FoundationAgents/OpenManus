"""
OpenManus Backend Session Management
"""

from datetime import datetime
from typing import Any, Dict, Optional

from app.logger import logger


class SessionManager:
    """Session manager"""

    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, session_id: str, **kwargs) -> Dict[str, Any]:
        """Create new session"""
        session_data = {
            "status": "initializing",
            "progress": 0.0,
            "current_step": 0,
            "created_at": datetime.now(),
            **kwargs,
        }
        self.sessions[session_id] = session_data
        logger.info(f"Created session: {session_id}")
        return session_data

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        return self.sessions.get(session_id)

    def update_session(self, session_id: str, **kwargs) -> bool:
        """Update session data"""
        if session_id in self.sessions:
            self.sessions[session_id].update(kwargs)
            return True
        return False

    def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted session: {session_id}")
            return True
        return False

    def list_sessions(self) -> Dict[str, Dict[str, Any]]:
        """List all sessions"""
        return {
            session_id: {
                "session_id": session_id,
                "status": data["status"],
                "prompt": data.get("prompt", ""),
                "progress": data.get("progress", 0.0),
            }
            for session_id, data in self.sessions.items()
        }

    def cleanup_expired_sessions(self, timeout: int) -> int:
        """Clean up expired sessions"""
        current_time = datetime.now()
        expired_sessions = []

        for session_id, session_data in self.sessions.items():
            created_at = session_data.get("created_at", datetime.min)
            if current_time - created_at > timeout:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            self.delete_session(session_id)

        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

        return len(expired_sessions)

    def get_session_count(self) -> int:
        """Get current session count"""
        return len(self.sessions)


# Global session manager instance
session_manager = SessionManager()
