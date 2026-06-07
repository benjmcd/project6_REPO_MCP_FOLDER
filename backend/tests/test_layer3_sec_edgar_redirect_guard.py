"""Unit tests for _SecEdgarRedirectGuard — per-hop SSRF redirect validation.

These tests exercise redirect_request() directly with no live network calls.
"""
from __future__ import annotations

import email.message
import urllib.error
import urllib.request

import pytest

from app.services.layer3_sec_edgar_live_source_artifact import (
    _SecEdgarRedirectGuard,
    _SEC_OPENER,
)


def _make_headers() -> email.message.Message:
    """Minimal Message object that satisfies urllib's redirect_request signature."""
    return email.message.Message()


def _make_req(url: str) -> urllib.request.Request:
    return urllib.request.Request(url)


class TestSecEdgarRedirectGuard:
    """Direct unit tests for _SecEdgarRedirectGuard.redirect_request."""

    def setup_method(self) -> None:
        self.guard = _SecEdgarRedirectGuard()
        # Wire up the opener so the handler has a valid parent (needed for super() call).
        opener = urllib.request.build_opener(self.guard)
        self.guard.parent = opener

    # ------------------------------------------------------------------
    # Allowed targets — must return a Request without raising
    # ------------------------------------------------------------------

    def test_allowed_www_sec_gov(self) -> None:
        """Redirect to https://www.sec.gov/... is permitted."""
        newurl = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
        req = _make_req("https://www.sec.gov/start")
        result = self.guard.redirect_request(
            req, None, 301, "Moved", _make_headers(), newurl
        )
        assert isinstance(result, urllib.request.Request)

    def test_allowed_data_sec_gov(self) -> None:
        """Redirect to https://data.sec.gov/... is permitted (subdomain)."""
        newurl = "https://data.sec.gov/submissions/CIK0000789019.json"
        req = _make_req("https://www.sec.gov/start")
        result = self.guard.redirect_request(
            req, None, 302, "Found", _make_headers(), newurl
        )
        assert isinstance(result, urllib.request.Request)

    # ------------------------------------------------------------------
    # Blocked targets — must raise HTTPError, NOT follow the redirect
    # ------------------------------------------------------------------

    def test_blocked_off_domain(self) -> None:
        """Redirect to https://evil.example.com/... is blocked."""
        newurl = "https://evil.example.com/steal"
        req = _make_req("https://www.sec.gov/start")
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self.guard.redirect_request(
                req, None, 301, "Moved", _make_headers(), newurl
            )
        assert exc_info.value.url == newurl
        assert "blocked" in exc_info.value.reason.lower()

    def test_blocked_http_downgrade(self) -> None:
        """Redirect to http://www.sec.gov/... (plain HTTP) is blocked — scheme must be https."""
        newurl = "http://www.sec.gov/insecure"
        req = _make_req("https://www.sec.gov/start")
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self.guard.redirect_request(
                req, None, 301, "Moved", _make_headers(), newurl
            )
        assert exc_info.value.url == newurl

    def test_blocked_host_suffix_trick(self) -> None:
        """Redirect to https://attacker-sec.gov.evil.com/... is blocked (suffix exploit)."""
        newurl = "https://attacker-sec.gov.evil.com/exfil"
        req = _make_req("https://www.sec.gov/start")
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            self.guard.redirect_request(
                req, None, 302, "Found", _make_headers(), newurl
            )
        assert exc_info.value.url == newurl

    def test_blocked_internal_host(self) -> None:
        """Redirect to an internal/RFC-1918 host is blocked."""
        for internal_url in [
            "http://169.254.169.254/latest/meta-data/",
            "http://10.0.0.1/admin",
            "https://internal.corp/secret",
        ]:
            req = _make_req("https://www.sec.gov/start")
            with pytest.raises(urllib.error.HTTPError):
                self.guard.redirect_request(
                    req, None, 301, "Moved", _make_headers(), internal_url
                )


    # ------------------------------------------------------------------
    # User-Agent must SURVIVE an allowed redirect (codex P2 regression guard)
    # ------------------------------------------------------------------

    def test_user_agent_survives_allowed_redirect(self) -> None:
        """SEC fair-access User-Agent set in Request.headers must be carried onto the
        follow-up request after an allowed redirect. urllib's redirect_request rebuilds
        from req.headers (NOT unredirected_hdrs), so the UA MUST live in headers.
        Regression guard: an earlier impl used add_unredirected_header, which urllib
        drops on redirect — leaving SEC requests without the required identifying UA."""
        ua = "NexonPVP-Research contact@nexonpvp.net"
        req = urllib.request.Request(
            "https://www.sec.gov/start",
            headers={"User-Agent": ua, "Accept": "text/plain"},
        )
        newurl = "https://www.sec.gov/Archives/edgar/data/320193/x.htm"
        result = self.guard.redirect_request(
            req, None, 301, "Moved", _make_headers(), newurl
        )
        assert result.get_header("User-agent") == ua, (
            "User-Agent was lost across the redirect; it must be set in Request.headers "
            "(not add_unredirected_header) to survive HTTPRedirectHandler.redirect_request."
        )

    def test_user_agent_in_unredirected_header_does_not_survive(self) -> None:
        """Documents WHY the UA must be in headers: add_unredirected_header is dropped on
        redirect. This pins the urllib contract the fix depends on."""
        req = urllib.request.Request("https://www.sec.gov/start")
        req.add_unredirected_header("User-Agent", "DROPPED-ON-REDIRECT")
        newurl = "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json"
        result = self.guard.redirect_request(
            req, None, 302, "Found", _make_headers(), newurl
        )
        assert result.get_header("User-agent") is None


class TestSecOpenerIsWiredWithGuard:
    """Confirm the module-level _SEC_OPENER has _SecEdgarRedirectGuard installed."""

    def test_opener_has_redirect_guard(self) -> None:
        handlers = _SEC_OPENER.handlers
        guard_handlers = [h for h in handlers if isinstance(h, _SecEdgarRedirectGuard)]
        assert guard_handlers, (
            "_SEC_OPENER must contain a _SecEdgarRedirectGuard handler; "
            f"found handlers: {[type(h).__name__ for h in handlers]}"
        )
