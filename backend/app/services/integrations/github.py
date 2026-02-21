from __future__ import annotations

from urllib.parse import urlencode

from app.core.config import get_settings


class GitHubIntegrationService:
    def authorize_url(self, state: str) -> str:
        settings = get_settings()
        query = urlencode(
            {
                "client_id": settings.github_client_id,
                "redirect_uri": settings.github_redirect_uri,
                "scope": "repo read:user",
                "state": state,
            }
        )
        return f"https://github.com/login/oauth/authorize?{query}"


GITHUB_INTEGRATION = GitHubIntegrationService()
