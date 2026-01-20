import os
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import HTMLResponse

from open_webui.utils.auth import get_current_user
from open_webui.utils.jira_oauth import JiraOAuthError, complete_oauth_flow, set_user_record


router = APIRouter()


def _html_page(
    title: str,
    body: str,
    status_code: int = 200,
    redirect_url: Optional[str] = None,
) -> HTMLResponse:
    redirect_meta = (
        f'<meta http-equiv="refresh" content="2; url={redirect_url}" />'
        if redirect_url
        else ""
    )
    redirect_cta = (
        f'<a href="{redirect_url}">Return to OpenWebUI</a>' if redirect_url else ""
    )
    html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>{title}</title>
    {redirect_meta}
    <style>
      body {{ font-family: Arial, sans-serif; margin: 2rem; }}
      .card {{ max-width: 720px; margin: 0 auto; padding: 1.5rem; border: 1px solid #e5e7eb; border-radius: 12px; }}
      .title {{ font-size: 1.25rem; margin-bottom: 0.75rem; }}
      .details {{ color: #374151; white-space: pre-wrap; }}
      .hint {{ margin-top: 1rem; color: #6b7280; font-size: 0.95rem; }}
    </style>
  </head>
  <body>
    <div class="card">
      <div class="title">{title}</div>
      <div class="details">{body}</div>
      <div class="hint">{redirect_cta}</div>
      <div class="hint">You can return to OpenWebUI after closing this tab.</div>
    </div>
  </body>
</html>"""
    return HTMLResponse(html, status_code=status_code)


def _extract_user_key_from_state(state: str) -> Optional[str]:
    if ":" not in state:
        return None
    return state.split(":", 1)[0] or None


@router.get("/atlassian/callback", response_class=HTMLResponse)
async def atlassian_oauth_callback(request: Request):
    post_auth_redirect = os.environ.get("ATLASSIAN_POST_AUTH_REDIRECT", "").strip()
    code = (request.query_params.get("code") or "").strip()
    state = (request.query_params.get("state") or "").strip()
    if not code or not state:
        return _html_page(
            "Jira OAuth failed",
            "Missing required query params: code and state.",
            status_code=400,
            redirect_url=post_auth_redirect or None,
        )

    expected_redirect = os.environ.get("ATLASSIAN_REDIRECT_URI", "").strip()
    if expected_redirect:
        actual_redirect = str(request.url).split("?", 1)[0]
        if expected_redirect.rstrip("/") != actual_redirect.rstrip("/"):
            return _html_page(
                "Jira OAuth failed",
                "Redirect URI mismatch. Update ATLASSIAN_REDIRECT_URI to exactly "
                f"match this callback URL: {actual_redirect}",
                status_code=400,
                redirect_url=post_auth_redirect or None,
            )

    user_key_from_state = _extract_user_key_from_state(state)
    user_key: Optional[str] = None
    user_hint = ""

    try:
        user = await get_current_user(
            request=request,
            response=HTMLResponse(),
            background_tasks=BackgroundTasks(),
        )
        if user.role not in {"user", "admin"}:
            raise ValueError("Unverified user.")
        user_key = str(user.id or user.email or "")
        if not state.startswith(f"{user_key}:"):
            return _html_page(
                "Jira OAuth failed",
                "Invalid state for the current user. Please run jira_connect again "
                "from the same OpenWebUI account.",
                status_code=400,
                redirect_url=post_auth_redirect or None,
            )
    except Exception:
        if not user_key_from_state:
            return _html_page(
                "Jira OAuth failed",
                "Unable to determine user identity. Please log into OpenWebUI and "
                "restart the Jira connection flow.",
                status_code=401,
                redirect_url=post_auth_redirect or None,
            )
        user_key = user_key_from_state
        user_hint = (
            "We could not verify your OpenWebUI session, so the user identity was "
            "derived from the OAuth state. If this is unexpected, please log in and "
            "restart the connection."
        )

    try:
        record = complete_oauth_flow(code)
        set_user_record(user_key, record)
        message = (
            "✅ Jira OAuth completed successfully.\n\n"
            f"Site: {record.get('resource_name','')}\n"
            f"URL: {record.get('cloud_url','')}\n"
            f"cloudId: {record.get('cloud_id','')}"
        )
        if user_hint:
            message = f"{message}\n\nNote: {user_hint}"
        return _html_page(
            "Jira OAuth success",
            message,
            redirect_url=post_auth_redirect or "/",
        )
    except JiraOAuthError as exc:
        return _html_page(
            "Jira OAuth failed",
            f"OAuth exchange failed: {exc}",
            status_code=400,
            redirect_url=post_auth_redirect or None,
        )
    except Exception as exc:
        return _html_page(
            "Jira OAuth failed",
            f"Unexpected error: {exc}",
            status_code=500,
            redirect_url=post_auth_redirect or None,
        )