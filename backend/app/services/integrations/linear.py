from __future__ import annotations

from urllib.parse import urlencode

from app.core.config import get_settings


class LinearIntegrationService:
    def authorize_url(self, state: str) -> str:
        settings = get_settings()
        query = urlencode(
            {
                "client_id": settings.linear_client_id,
                "redirect_uri": settings.linear_redirect_uri,
                "response_type": "code",
                "scope": "read write",
                "state": state,
            }
        )
        return f"https://linear.app/oauth/authorize?{query}"


LINEAR_INTEGRATION = LinearIntegrationService()
