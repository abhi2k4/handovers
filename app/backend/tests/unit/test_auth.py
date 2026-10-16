"""Sign-in pieces that need no Keycloak: the authorization request, safe redirects, sealing."""

import base64
import hashlib
from urllib.parse import parse_qs, urlparse

from api.auth import _known_provider, _safe_next
from core import keycloak, security
from core.config import Settings

S = Settings(keycloak_url="http://keycloak:8180", keycloak_public_url="http://localhost:8180")


def test_the_authorization_request_uses_pkce_and_the_public_issuer() -> None:
    req = keycloak.begin_sign_in(S)
    url = urlparse(req.url)
    q = {k: v[0] for k, v in parse_qs(url.query).items()}
    # The browser goes to the public address; the backend talks to the internal one.
    assert req.url.startswith("http://localhost:8180/realms/handovers/protocol/openid-connect/auth")
    assert S.keycloak_internal_realm_url == "http://keycloak:8180/realms/handovers"
    expected = base64.urlsafe_b64encode(hashlib.sha256(req.verifier.encode()).digest()).rstrip(b"=")
    assert q["code_challenge"] == expected.decode() and q["code_challenge_method"] == "S256"
    assert q["state"] == req.state and q["nonce"] == req.nonce
    assert q["redirect_uri"] == "http://localhost:5173/api/auth/callback"
    assert "kc_idp_hint" not in q


def test_a_provider_goes_straight_to_its_sign_in_page() -> None:
    q = parse_qs(urlparse(keycloak.begin_sign_in(S, "google").url).query)
    assert q["kc_idp_hint"] == ["google"]
    assert _known_provider("microsoft") == "microsoft"
    assert _known_provider("myspace") is None  # only registered providers


def test_only_same_site_paths_are_followed_after_sign_in() -> None:
    assert _safe_next("/handovers/ho:1") == "/handovers/ho:1"
    for bad in ("https://evil.example", "//evil.example", "/\\evil", "javascript:x", None, ""):
        assert _safe_next(bad) is None


def test_secrets_round_trip_and_sessions_are_hashed() -> None:
    sealed = security.encrypt('{"state": "x"}')
    assert "state" not in sealed and security.decrypt(sealed) == '{"state": "x"}'
    token = security.new_token()
    assert security.token_hash(token) != token and len(security.token_hash(token)) == 64
    assert security.mask("ghp_abcdef1234") == "••••1234" and security.mask("abc") == "••••"


def test_sign_out_ends_the_keycloak_session_too() -> None:
    url = keycloak.end_session_url(S, "id-token")
    q = parse_qs(urlparse(url).query)
    assert url.startswith("http://localhost:8180/realms/handovers/protocol/openid-connect/logout")
    assert q["id_token_hint"] == ["id-token"]
    assert q["post_logout_redirect_uri"] == ["http://localhost:5173/login"]


def test_app_links_live_under_dashboard() -> None:
    from core.config import Settings

    s = Settings(app_public_url="https://handovers.example/")
    assert s.app_url() == "https://handovers.example/dashboard"
    assert (
        s.app_url("/handovers/ho:1?tab=clearance")
        == "https://handovers.example/dashboard/handovers/ho:1?tab=clearance"
    )
    assert s.app_url("/login?error=x") == "https://handovers.example/dashboard/login?error=x"
