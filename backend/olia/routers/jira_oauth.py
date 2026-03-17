import os
import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from olia.utils.jira_oauth import (
    JiraOAuthError,
    complete_oauth_flow,
    set_user_record,
    extract_user_key_from_state,
    token_path_for_user,  # NEW helper
    safe_oauth_env_snapshot,  # NEW helper
)

router = APIRouter()

logger = logging.getLogger("olia.jira_oauth")
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

    err = (request.query_params.get("error") or "").strip()
    err_desc = (request.query_params.get("error_description") or "").strip()

    code = (request.query_params.get("code") or "").strip()
    state = (request.query_params.get("state") or "").strip()

    # SAFE env snapshot (no secrets)
    env_dbg = safe_oauth_env_snapshot()

    logger.info("Jira OAuth callback hit. url=%s", str(request.url))
    logger.info("Jira OAuth env snapshot: %s", env_dbg)

    if err:
        body = (
            f"OAuth failed (Atlassian error)\n\n"
            f"error: {err}\n"
            f"error_description: {err_desc}\n\n"
            f"Full callback URL:\n<pre>{str(request.url)}</pre>\n\n"
            f"Env snapshot (SAFE):\n<pre>{env_dbg}</pre>\n\n"
            "Common causes: redirect_uri mismatch, invalid client, malformed authorize URL.\n"
            "If your auth URL contains '&amp;' instead of '&', do NOT copy it as text."
        )
        logger.warning("OAuth failed from Atlassian error=%s desc=%s", err, err_desc)
        return _html_page("Jira OAuth failed", body, status_code=400)

    if not code or not state:
        body = (
            "OAuth failed\n\n"
            "Missing required query params: code and state.\n\n"
            f"Full callback URL:\n<pre>{str(request.url)}</pre>\n\n"
            f"Env snapshot (SAFE):\n<pre>{env_dbg}</pre>\n\n"
            "This usually happens when the authorization URL was copied with HTML escaping:\n"
            " - WRONG: ...audience=api.atlassian.com&amp;client_id=...\n"
            " - RIGHT: ...audience=api.atlassian.com&client_id=...\n"
        )
        logger.warning("OAuth failed missing params. code_present=%s state_present=%s", bool(code), bool(state))
        return _html_page("Jira OAuth failed", body, status_code=400)

    user_key = extract_user_key_from_state(state)
    if not user_key:
        body = (
            "OAuth failed\n\n"
            "Invalid state: cannot extract user identity.\n\n"
            f"state received:\n<pre>{state}</pre>\n\n"
            "Expected format: <user_key>:<random_uuid>"
        )
        logger.warning("OAuth failed invalid state=%s", state)
        return _html_page("Jira OAuth failed", body, status_code=400)

    expected_redirect = (os.environ.get("ATLASSIAN_REDIRECT_URI") or "").strip()
    if expected_redirect:
        actual_callback = str(request.url).split("?", 1)[0]
        if expected_redirect.rstrip("/") != actual_callback.rstrip("/"):
            body = (
                "OAuth failed\n\n"
                "Redirect URI mismatch.\n\n"
                f"Expected ATLASSIAN_REDIRECT_URI:\n<pre>{expected_redirect}</pre>\n"
                f"Actual callback URL:\n<pre>{actual_callback}</pre>\n\n"
                f"Env snapshot (SAFE):\n<pre>{env_dbg}</pre>\n\n"
                "Fix: update ATLASSIAN_REDIRECT_URI to EXACTLY match the callback URL."
            )
            logger.warning("Redirect mismatch expected=%s actual=%s", expected_redirect, actual_callback)
            return _html_page("Jira OAuth failed", body, status_code=400)

    try:
        record = complete_oauth_flow(code)  # may raise JiraOAuthError
        set_user_record(user_key, record)

        # log saved record safely (no tokens)
        saved_path = token_path_for_user(user_key)
        safe_keys = list(record.keys())
        logger.info("OAuth success. user_key=%s saved_path=%s record_keys=%s cloud_id=%s",
                    user_key, saved_path, safe_keys, record.get("cloud_id"))

        return RedirectResponse(url=post_auth_redirect or "/", status_code=302)

    except JiraOAuthError as exc:
        logger.exception("OAuth exchange failed: %s", exc)
        body = (
            "OAuth exchange failed\n\n"
            f"{exc}\n\n"
            f"callback URL:\n<pre>{str(request.url)}</pre>\n\n"
            f"Env snapshot (SAFE):\n<pre>{env_dbg}</pre>\n"
        )
        return _html_page("Jira OAuth failed", body, status_code=400)

    except Exception as exc:
        logger.exception("Unexpected error in callback: %s", exc)
        body = (
            "Unexpected error\n\n"
            f"{exc}\n\n"
            f"callback URL:\n<pre>{str(request.url)}</pre>\n\n"
            f"Env snapshot (SAFE):\n<pre>{env_dbg}</pre>\n"
        )
        return _html_page("Jira OAuth failed", body, status_code=500)
