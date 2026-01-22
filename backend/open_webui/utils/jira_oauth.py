import os
import json
import threading
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from pathlib import Path

import requests

from open_webui.env import DATA_DIR

# Use DATA_DIR (app/backend/data) for Jira OAuth tokens - same location as webui.db
# Can be overridden via JIRA_OAUTH_TOKEN_DIR environment variable
_DEFAULT_TOKEN_DIR = Path(DATA_DIR) / "jira_oauth"
BASE_TOKEN_DIR = os.getenv("JIRA_OAUTH_TOKEN_DIR", str(_DEFAULT_TOKEN_DIR))
_TOKEN_LOCK = threading.Lock()

import logging
logger = logging.getLogger("openwebui.jira_oauth")


class JiraOAuthError(Exception):
    pass


def _env_get_any(*names: str) -> str:
    for n in names:
        v = (os.environ.get(n) or "").strip()
        if v:
            return v
    return ""


def safe_oauth_env_snapshot() -> Dict[str, Any]:
    """
    SAFE snapshot: never prints secrets.
    """
    cid = _env_get_any("ATLASSIAN_CLIENT_ID", "ATLASSIAN_OAUTH_CLIENT_ID", "JIRA_CLIENT_ID")
    csec = _env_get_any("ATLASSIAN_CLIENT_SECRET","OAUTH_CLIENT_SECRET", "ATLASSIAN_OAUTH_CLIENT_SECRET", "JIRA_CLIENT_SECRET")
    ruri = _env_get_any("ATLASSIAN_REDIRECT_URI", "ATLASSIAN_OAUTH_REDIRECT_URI", "JIRA_REDIRECT_URI")
    scopes = (os.environ.get("ATLASSIAN_SCOPES") or "").strip()
    aud = (os.environ.get("ATLASSIAN_AUDIENCE") or "").strip()
    return {
        "ATLASSIAN_CLIENT_ID": (cid[:6] + "...") if cid else "MISSING",
        "ATLASSIAN_CLIENT_SECRET_SET": bool(csec),
        "ATLASSIAN_REDIRECT_URI": ruri or "MISSING",
        "ATLASSIAN_SCOPES": scopes or "DEFAULT/EMPTY",
        "ATLASSIAN_AUDIENCE": aud or "api.atlassian.com",
        "JIRA_OAUTH_TOKEN_DIR": BASE_TOKEN_DIR,
    }


class AtlassianOAuthClient:
    AUTH_URL = "https://auth.atlassian.com/authorize"
    TOKEN_URL = "https://auth.atlassian.com/oauth/token"
    ACCESSIBLE_RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"

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
        # allow alias env names to avoid “configured but code can’t read it”
        client_id = _env_get_any("ATLASSIAN_CLIENT_ID", "ATLASSIAN_OAUTH_CLIENT_ID", "JIRA_CLIENT_ID")
        client_secret = _env_get_any("ATLASSIAN_CLIENT_SECRET", "OAUTH_CLIENT_SECRET", "ATLASSIAN_OAUTH_CLIENT_SECRET","JIRA_CLIENT_SECRET")
        redirect_uri = _env_get_any("ATLASSIAN_REDIRECT_URI", "ATLASSIAN_OAUTH_REDIRECT_URI", "JIRA_REDIRECT_URI")

        scopes = os.environ.get("ATLASSIAN_SCOPES", "read:jira-work write:jira-work offline_access")
        audience = os.environ.get("ATLASSIAN_AUDIENCE", "api.atlassian.com")

        logger.info("OAuth from_env snapshot: %s", safe_oauth_env_snapshot())
        return cls(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scopes=scopes,
            audience=audience,
        )

    def build_authorize_url(self, state: str) -> str:
        params = {
            "audience": self.audience,
            "client_id": self.client_id,
            "scope": self.scopes,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "response_type": "code",
            "prompt": "consent",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        payload = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        response = requests.post(self.TOKEN_URL, json=payload, headers={"Accept": "application/json"}, timeout=30)
        if response.status_code < 200 or response.status_code >= 300:
            raise JiraOAuthError(f"OAuth token exchange failed ({response.status_code}): {response.text}")
        return response.json()

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
        }
        response = requests.post(self.TOKEN_URL, json=payload, headers={"Accept": "application/json"}, timeout=30)
        if response.status_code < 200 or response.status_code >= 300:
            raise JiraOAuthError(f"OAuth refresh failed ({response.status_code}): {response.text}")
        return response.json()

    def get_accessible_resources(self, access_token: str) -> List[Dict[str, Any]]:
        response = requests.get(
            self.ACCESSIBLE_RESOURCES_URL,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            timeout=30,
        )
        if response.status_code < 200 or response.status_code >= 300:
            raise JiraOAuthError(f"Failed to fetch accessible resources ({response.status_code}): {response.text}")
        data = response.json()
        if not isinstance(data, list):
            raise JiraOAuthError(f"Unexpected accessible-resources response: {data}")
        return data


def token_path_for_user(user_key: str) -> str:
    safe_key = (user_key or "").replace("/", "_").replace(":", "_")
    return os.path.join(BASE_TOKEN_DIR, f"user_{safe_key}.json")


def get_user_record(user_key: str) -> Dict[str, Any]:
    path = token_path_for_user(user_key)
    if not os.path.exists(path):
        return {}
    with _TOKEN_LOCK:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return {}


def set_user_record(user_key: str, record: Dict[str, Any]) -> None:
    os.makedirs(BASE_TOKEN_DIR, exist_ok=True)
    path = token_path_for_user(user_key)
    with _TOKEN_LOCK:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2)


def delete_user_record(user_key: str) -> None:
    path = token_path_for_user(user_key)
    with _TOKEN_LOCK:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass


def build_user_record(token_payload: Dict[str, Any]) -> Dict[str, Any]:
    access_token = token_payload.get("access_token") or ""
    refresh_token = token_payload.get("refresh_token") or ""
    
    # Force token expiration to 1 month (30 days) regardless of expires_in from Atlassian
    # 30 days = 30 * 24 * 60 * 60 = 2,592,000 seconds
    ONE_MONTH_SECONDS = 30 * 24 * 60 * 60
    expires_at = int(time.time() + ONE_MONTH_SECONDS)

    if not access_token:
        raise JiraOAuthError(f"OAuth token exchange returned no access_token: {list(token_payload.keys())}")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
    }


def choose_accessible_resource(resources: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not resources:
        raise JiraOAuthError("No accessible Jira resources found for this user.")
    chosen = resources[0]
    logger.info("Accessible resource chosen: id=%s name=%s url=%s",
                chosen.get("id"), chosen.get("name"), chosen.get("url"))
    return chosen


def complete_oauth_flow(code: str) -> Dict[str, Any]:
    oauth = AtlassianOAuthClient.from_env()

    logger.info("Starting token exchange (code_present=%s)", bool(code))
    token_payload = oauth.exchange_code_for_token(code)
    record = build_user_record(token_payload)

    logger.info("Token exchange OK. Fetching accessible resources...")
    resources = oauth.get_accessible_resources(record["access_token"])
    chosen = choose_accessible_resource(resources)

    cloud_id = chosen.get("id") or ""
    cloud_url = chosen.get("url") or ""
    if not cloud_id:
        raise JiraOAuthError(f"accessible-resources did not include an id: {chosen}")

    record.update({"cloud_id": cloud_id, "cloud_url": cloud_url, "resource_name": chosen.get("name") or ""})
    logger.info("OAuth flow complete. cloud_id=%s cloud_url=%s", cloud_id, cloud_url)
    return record


def extract_user_key_from_state(state: str) -> Optional[str]:
    state = (state or "").strip()
    if ":" not in state:
        return None
    return state.split(":", 1)[0] or None
