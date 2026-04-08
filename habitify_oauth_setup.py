"""One-time OAuth setup for Habitify MCP server.

Performs dynamic client registration, PKCE authorization code flow,
and stores refresh token + client ID in .env for headless runtime use.

Works on headless machines: prints the auth URL for you to open anywhere,
then you paste back the redirect URL containing the code.

Usage:
    .venv/bin/python habitify_oauth_setup.py
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

# Habitify OAuth endpoints
REGISTRATION_URL = "https://account.habitify.me/reg"
AUTHORIZATION_URL = "https://account.habitify.me/auth"
TOKEN_URL = "https://account.habitify.me/token"

# Redirect URI — the server won't actually be running; user pastes the URL back
REDIRECT_URI = "http://localhost:8976/callback"

# Path to .env (same directory as this script)
ENV_PATH = Path(__file__).resolve().parent / ".env"


def _generate_code_verifier() -> str:
    return secrets.token_urlsafe(64)[:96]


def _generate_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _register_client() -> str:
    print("Registering OAuth client with Habitify...")
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            REGISTRATION_URL,
            json={
                "client_name": "claude-code-habitify-proxy",
                "redirect_uris": [REDIRECT_URI],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "none",
                "scope": "openid offline_access all",
            },
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"Client registration failed ({resp.status_code}): {resp.text}"
            )
        client_id = resp.json()["client_id"]
        print(f"  Client registered: {client_id}")
        return client_id


def _build_authorization_url(
    client_id: str, code_challenge: str, state: str
) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid offline_access all",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
        "prompt": "consent",
    }
    return f"{AUTHORIZATION_URL}?{urlencode(params)}"


def _extract_code_from_url(callback_url: str, expected_state: str) -> str:
    """Extract the authorization code from the pasted callback URL."""
    parsed = urlparse(callback_url)
    params = parse_qs(parsed.query)

    if "error" in params:
        desc = params.get("error_description", ["Unknown error"])[0]
        raise RuntimeError(f"Authorization failed: {desc}")

    returned_state = params.get("state", [None])[0]
    if returned_state != expected_state:
        raise RuntimeError("State mismatch — try running the setup again")

    code = params.get("code", [None])[0]
    if not code:
        raise RuntimeError("No authorization code in the URL")

    return code


def _exchange_code(
    client_id: str, auth_code: str, code_verifier: str
) -> tuple[str, str]:
    print("Exchanging authorization code for tokens...")
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": REDIRECT_URI,
                "client_id": client_id,
                "code_verifier": code_verifier,
                "scope": "openid offline_access all",
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Token exchange failed ({resp.status_code}): {resp.text}"
            )
        data = resp.json()
        access_token = data["access_token"]
        refresh_token = data.get("refresh_token")
        if not refresh_token:
            raise RuntimeError(
                "No refresh_token in response. "
                "Ensure 'offline_access' scope was granted."
            )
        print("  Tokens received successfully.")
        return access_token, refresh_token


def _update_env(client_id: str, refresh_token: str) -> None:
    env_vars = {
        "HABITIFY_CLIENT_ID": client_id,
        "HABITIFY_REFRESH_TOKEN": refresh_token,
    }

    existing_lines: list[str] = []
    if ENV_PATH.exists():
        existing_lines = ENV_PATH.read_text().splitlines()

    updated_keys: set[str] = set()
    new_lines: list[str] = []
    for line in existing_lines:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key in env_vars:
            new_lines.append(f"{key}={env_vars[key]}")
            updated_keys.add(key)
        else:
            new_lines.append(line)

    for key, value in env_vars.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}")

    content = "\n".join(new_lines)
    if not content.endswith("\n"):
        content += "\n"

    ENV_PATH.write_text(content)
    print(f"  Credentials written to {ENV_PATH}")


def main() -> None:
    print("=" * 60)
    print("Habitify OAuth Setup (headless-friendly)")
    print("=" * 60)
    print()

    # Step 1: Dynamic client registration
    client_id = _register_client()

    # Step 2: PKCE setup
    code_verifier = _generate_code_verifier()
    code_challenge = _generate_code_challenge(code_verifier)
    state = secrets.token_urlsafe(32)

    # Step 3: Print the auth URL
    auth_url = _build_authorization_url(client_id, code_challenge, state)
    print()
    print("Open this URL in any browser and log in to Habitify:")
    print()
    print(f"  {auth_url}")
    print()
    print("After authorizing, you'll be redirected to a localhost URL")
    print("that won't load. That's fine — just copy the FULL URL from")
    print("your browser's address bar and paste it below.")
    print()

    # Step 4: User pastes the callback URL
    callback_url = input("Paste the redirect URL here: ").strip()
    auth_code = _extract_code_from_url(callback_url, state)

    # Step 5: Exchange code for tokens
    access_token, refresh_token = _exchange_code(
        client_id, auth_code, code_verifier
    )

    # Step 6: Store credentials
    _update_env(client_id, refresh_token)

    print()
    print("=" * 60)
    print("Setup complete! Restart Claude Code to use Habitify MCP.")
    print("=" * 60)


if __name__ == "__main__":
    main()
