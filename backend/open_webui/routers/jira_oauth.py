import os
from typing import Optional
import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from open_webui.utils.jira_oauth import (
    JiraOAuthError,
    complete_oauth_flow,
    set_user_record,
    extract_user_key_from_state,
)

router = APIRouter()

logger = logging.getLogger("openwebui.jira_oauth")
logger.setLevel(logging.INFO)

def _html_page(title: str, body: str, status_code: int = 200) -> HTMLResponse:
    html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>{title}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 2rem; }}
      .card {{ max-width: 860px; margin: 0 auto; padding: 1.5rem; border: 1px solid #e5e7eb; border-radius: 12px; }}
      .title {{ font-size: 1.25rem; margin-bottom: 0.75rem; font-weight: 600; }}
      .details {{ color: #374151; white-space: pre-wrap; }}
      code, pre {{ background: #f3f4f6; padding: 0.5rem; border-radius: 8px; display:block; overflow:auto; }}
      .hint {{ margin-top: 1rem; color: #6b7280; font-size: 0.95rem; }}
      .btn a {{ display:inline-block; padding:10px 14px; background:#111827; color:white; border-radius:10px; text-decoration:none; }}
    </style>
  </head>
  <body>
    <div class="card">
      <div class="title">{title}</div>
      <div class="details">{body}</div>
    </div>
  </body>
</html>"""
    return HTMLResponse(html, status_code=status_code)


@router.get("/atlassian/callback", response_class=HTMLResponse)
async def atlassian_oauth_callback(request: Request):
    post_auth_redirect = (os.environ.get("ATLASSIAN_POST_AUTH_REDIRECT") or "/").strip()

    # Atlassian can return these on failure
    err = (request.query_params.get("error") or "").strip()
    err_desc = (request.query_params.get("error_description") or "").strip()

    code = (request.query_params.get("code") or "").strip()
    state = (request.query_params.get("state") or "").strip()

    # ---- if Atlassian returned an explicit error
    if err:
        body = (
            f"OAuth failed (Atlassian error)\n\n"
            f"error: {err}\n"
            f"error_description: {err_desc}\n\n"
            f"Full callback URL:\n<pre>{str(request.url)}</pre>\n\n"
            "Common cause: redirect_uri mismatch, invalid client, or the auth URL was malformed.\n"
            "If your auth URL contains '&amp;' instead of '&', do NOT copy it as text; use the raw URL."
        )
        return _html_page("Jira OAuth failed", body, status_code=400)

    # ---- Missing code/state => usually malformed authorize URL (ex: &amp;)
    if not code or not state:
        body = (
            "OAuth failed\n\n"
            "Missing required query params: code and state.\n\n"
            f"Full callback URL:\n<pre>{str(request.url)}</pre>\n\n"
            "✅ This almost always happens when the authorization URL was copied with HTML escaping:\n"
            " - WRONG: ...audience=api.atlassian.com&amp;client_id=...\n"
            " - RIGHT: ...audience=api.atlassian.com&client_id=...\n\n"
            "Fix: make sure your tool prints the auth URL in a code block (raw) or as a clickable link.\n"
        )
        return _html_page("Jira OAuth failed", body, status_code=400)

    # ---- SECURITY: use state as the source of truth for user identity
    user_key = extract_user_key_from_state(state)
    if not user_key:
        body = (
            "OAuth failed\n\n"
            "Invalid state: cannot extract user identity.\n\n"
            f"state received:\n<pre>{state}</pre>\n\n"
            "Expected format: <user_key>:<random_uuid>"
        )
        return _html_page("Jira OAuth failed", body, status_code=400)

    # ---- OPTIONAL: ensure redirect URI matches exactly
    expected_redirect = (os.environ.get("ATLASSIAN_REDIRECT_URI") or "").strip()
    if expected_redirect:
        actual_callback = str(request.url).split("?", 1)[0]
        if expected_redirect.rstrip("/") != actual_callback.rstrip("/"):
            body = (
                "OAuth failed\n\n"
                "Redirect URI mismatch.\n\n"
                f"Expected ATLASSIAN_REDIRECT_URI:\n<pre>{expected_redirect}</pre>\n"
                f"Actual callback URL:\n<pre>{actual_callback}</pre>\n\n"
                "Fix: update ATLASSIAN_REDIRECT_URI to EXACTLY match the callback URL."
            )
            return _html_page("Jira OAuth failed", body, status_code=400)

    # ---- Complete flow, save record
    try:
        record = complete_oauth_flow(code)
        set_user_record(user_key, record)

        # ✅ redirect ONLY after success
        return RedirectResponse(url=post_auth_redirect or "/", status_code=302)

    except JiraOAuthError as exc:
        body = (
            "OAuth exchange failed\n\n"
            f"{exc}\n\n"
            f"callback URL:\n<pre>{str(request.url)}</pre>\n"
        )
        return _html_page("Jira OAuth failed", body, status_code=400)

    except Exception as exc:
        body = (
            "Unexpected error\n\n"
            f"{exc}\n\n"
            f"callback URL:\n<pre>{str(request.url)}</pre>\n"
        )
        return _html_page("Jira OAuth failed", body, status_code=500)
