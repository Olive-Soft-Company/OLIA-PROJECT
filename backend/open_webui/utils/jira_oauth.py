import os
import threading
import time
from typing import Any, Dict, List

import requests


BASE_TOKEN_DIR = "/data/openwebui/jira_oauth"
_TOKEN_LOCK = threading.Lock()


class JiraOAuthError(Exception):
    pass


class AtlassianOAuthClient:
    AUTH_URL = "https://auth.atlassian.com/authorize"
    TOKEN_URL = "https://auth.atlassian.com/oauth/token"
    ACCESSIBLE_RESOURCES_URL = (
        "https://api.atlassian.com/oauth/token/accessible-resources"
    )

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: str,
        audience: str = "api.atlassian.com",
    ) -> None:
        self.client_id = (client_id or "").strip()
        self.client_secret = (client_secret or "").strip()
        self.redirect_uri = (redirect_uri or "").strip()
        self.scopes = (scopes or "").strip()
        self.audience = (audience or "api.atlassian.com").strip()

        if not self.client_id or not self.client_secret or not self.redirect_uri:
            raise JiraOAuthError(
                "OAuth config missing. Please set ATLASSIAN_CLIENT_ID, "
                "ATLASSIAN_CLIENT_SECRET, and ATLASSIAN_REDIRECT_URI."
            )

    @classmethod
    def from_env(cls) -> "AtlassianOAuthClient":
        return cls(
            client_id=os.environ.get("ATLASSIAN_CLIENT_ID", ""),
            client_secret=os.environ.get("ATLASSIAN_CLIENT_SECRET", ""),
            redirect_uri=os.environ.get("ATLASSIAN_REDIRECT_URI", ""),
            scopes=os.environ.get("ATLASSIAN_SCOPES", ""),
            audience=os.environ.get("ATLASSIAN_AUDIENCE", "api.atlassian.com"),
        )

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        payload = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        response = requests.post(
            self.TOKEN_URL, json=payload, headers={"Accept": "application/json"}
        )
        if response.status_code < 200 or response.status_code >= 300:
            raise JiraOAuthError(
                "OAuth token exchange failed "
                f"({response.status_code}): {response.text}"
            )
        return response.json()

    def get_accessible_resources(self, access_token: str) -> List[Dict[str, Any]]:
        response = requests.get(
            self.ACCESSIBLE_RESOURCES_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        if response.status_code < 200 or response.status_code >= 300:
            raise JiraOAuthError(
                "Failed to fetch accessible resources "
                f"({response.status_code}): {response.text}"
            )
        data = response.json()
        if not isinstance(data, list):
            raise JiraOAuthError(f"Unexpected accessible-resources response: {data}")
        return data


def _token_path(user_key: str) -> str:
    safe_key = user_key.replace("/", "_").replace(":", "_")
    return os.path.join(BASE_TOKEN_DIR, f"user_{safe_key}.json")


def set_user_record(user_key: str, record: Dict[str, Any]) -> None:
    os.makedirs(BASE_TOKEN_DIR, exist_ok=True)
    path = _token_path(user_key)
    with _TOKEN_LOCK:
        with open(path, "w", encoding="utf-8") as handle:
            import json

            json.dump(record, handle, indent=2)


def build_user_record(token_payload: Dict[str, Any]) -> Dict[str, Any]:
    access_token = token_payload.get("access_token") or ""
    refresh_token = token_payload.get("refresh_token") or ""
    expires_in = int(token_payload.get("expires_in") or 3600)
    if not access_token:
        raise JiraOAuthError(
            f"OAuth token exchange returned no access_token: {token_payload}"
        )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": int(time.time() + expires_in),
    }


def choose_accessible_resource(resources: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not resources:
        raise JiraOAuthError("No accessible Jira resources found for this user.")
    return resources[0]


def complete_oauth_flow(code: str) -> Dict[str, Any]:
    oauth = AtlassianOAuthClient.from_env()
    token_payload = oauth.exchange_code_for_token(code)
    record = build_user_record(token_payload)
    resources = oauth.get_accessible_resources(record["access_token"])
    chosen = choose_accessible_resource(resources)

    cloud_id = chosen.get("id") or ""
    cloud_url = chosen.get("url") or ""
    if not cloud_id:
        raise JiraOAuthError(
            f"accessible-resources did not include an id: {chosen}"
        )

    record.update(
        {
            "cloud_id": cloud_id,
            "cloud_url": cloud_url,
            "resource_name": chosen.get("name") or "",
        }
    )
    return record