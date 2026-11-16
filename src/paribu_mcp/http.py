"""HTTP layer for paribu_mcp.

Paribu publishes an official public REST API at https://api.paribu.com
(docs: https://docs.paribu.com/api) — no login, no API key for market
data. All four public endpoints used here were verified live 2026-11-16:

- GET /market/ticker[?market=btc_tl] — 24h ticker(s); unknown market ->
  HTTP 500 {"message": "Internal Server Error", "code": 5001}
- GET /orderbook?market=btc_tl&limit=100 — bids/asks; unknown market ->
  HTTP 200 with a null body (not an error status)
- GET /trades?market=btc_tl&limit=20 — recent trades, newest first;
  limit is required and must be 1..20 (else HTTP 400 code 4001)
- GET /initials/config?scope=markets,currencies,fee_matrix,networks —
  exchange config wrapped in {message, meta, payload}; unknown scope
  fails the whole request

Transport uses curl-cffi chrome120 impersonation (the proven
Turkey-factory pattern) with a plain-requests fallback, so one
transport failing does not break the server. Requests are kept
gentle (one at a time, ~0.5s apart) and read-only.
"""
from __future__ import annotations

import time

from curl_cffi import requests as _creq
import requests as _plain

BASE = "https://api.paribu.com"
TIMEOUT = 30.0
MIN_INTERVAL = 0.5  # seconds between requests — be polite

_HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_last_fetch = 0.0


class ParibuError(RuntimeError):
    pass


def _throttle() -> None:
    global _last_fetch
    wait = MIN_INTERVAL - (time.monotonic() - _last_fetch)
    if wait > 0:
        time.sleep(wait)
    _last_fetch = time.monotonic()


_PROFILES = ("chrome120", "chrome131", "safari17_0")
_MAX_ATTEMPTS = 2  # one retry with the next profile
_RETRY_BACKOFF = 1.0  # seconds between attempts
_profile_idx = 0  # sticky: profile that last succeeded


def _request(url: str, headers: dict, timeout: float = TIMEOUT):
    """GET with fingerprint rotation.

    Starts at the sticky profile (chrome120 on a fresh process), retries
    once with the next profile on HTTP 403/429 or a transport error, then
    returns the last response (so the caller raises the specific 403/429
    error) or raises a network error if every attempt failed at the
    transport.
    """
    global _profile_idx
    last_exc: Exception | None = None
    for k in range(_MAX_ATTEMPTS):
        profile = _PROFILES[(_profile_idx + k) % len(_PROFILES)]
        try:
            resp = _creq.get(url, impersonate=profile, headers=headers, timeout=timeout)
        except Exception as e:
            last_exc = e
            if k + 1 < _MAX_ATTEMPTS:
                time.sleep(_RETRY_BACKOFF)
                continue
            raise ParibuError(f"network error fetching {url}: {e}") from e
        if resp.status_code in (403, 429):
            if k + 1 < _MAX_ATTEMPTS:
                time.sleep(_RETRY_BACKOFF)
                continue
            return resp
        _profile_idx = (_profile_idx + k) % len(_PROFILES)
        return resp
    raise ParibuError(f"network error fetching {url}: {last_exc}") from last_exc


def _get_json(url: str):
    """GET a URL, return the decoded JSON body (or None for a null body).

    Raises ParibuError with a human-readable message for HTTP errors,
    including the API's own error codes (5001 unknown market, 4001
    bad parameter).
    """
    _throttle()
    headers = dict(_HEADERS)
    try:
        resp = _request(url, headers)
        status, text = resp.status_code, resp.text
    except Exception:
        # Fallback transport: plain requests with a browser UA.
        try:
            resp = _plain.get(url, headers={**headers, "User-Agent": _UA}, timeout=TIMEOUT)
            status, text = resp.status_code, resp.text
        except ParibuError:
            raise
        except Exception as e:
            raise ParibuError(f"network error fetching {url}: {e}") from e
    if status == 403:
        raise ParibuError(
            "api.paribu.com refused the request (HTTP 403, bot wall) — try again later"
        )
    if status == 429:
        raise ParibuError(
            "api.paribu.com rate-limited the request (HTTP 429) — try again later"
        )
    if status == 404:
        raise ParibuError(f"api.paribu.com has no endpoint at {url} (HTTP 404)")
    if status == 400:
        raise ParibuError(f"Paribu rejected the request (HTTP 400): {text[:200]}")
    if status == 500:
        raise ParibuError(
            "Paribu returned HTTP 500 — the market id is probably unknown "
            f"(code 5001): {text[:200]}"
        )
    if status != 200:
        raise ParibuError(f"api.paribu.com returned HTTP {status} for {url}")
    if text.strip() == "null":
        return None
    try:
        import json

        return json.loads(text)
    except ValueError as e:
        raise ParibuError(f"Paribu returned non-JSON for {url}: {text[:200]}") from e


def fetch_ticker(market: str | None = None) -> list:
    """24h ticker: one market (e.g. "btc_tl") or all markets when omitted."""
    url = f"{BASE}/market/ticker"
    if market:
        url += f"?market={market}"
    data = _get_json(url)
    if not isinstance(data, list):
        raise ParibuError(f"unexpected ticker response for {url}: {str(data)[:200]}")
    return data


def fetch_orderbook(market: str, limit: int = 20) -> dict | None:
    """Order book for a market. Returns None for an unknown market
    (the API answers HTTP 200 with a null body)."""
    data = _get_json(f"{BASE}/orderbook?market={market}&limit={limit}")
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ParibuError(f"unexpected orderbook response: {str(data)[:200]}")
    return data


def fetch_trades(market: str, limit: int = 20) -> list:
    """Recent public trades for a market, newest first. limit 1..20."""
    data = _get_json(f"{BASE}/trades?market={market}&limit={limit}")
    if not isinstance(data, list):
        raise ParibuError(f"unexpected trades response: {str(data)[:200]}")
    return data


def fetch_config(scope: str) -> dict:
    """Exchange config for one or more comma-separated scopes
    (markets, currencies, fee_matrix, networks). Returns the payload."""
    data = _get_json(f"{BASE}/initials/config?scope={scope}")
    if not isinstance(data, dict) or "payload" not in data:
        raise ParibuError(f"unexpected config response: {str(data)[:200]}")
    return data["payload"]


def health_check() -> dict:
    """One polite probe of the public API.

    Returns {"status": "ok"|"blocked"|"error", "http_status": int|None,
    "url": ..., "detail": ...}. Used by the `paribu_health` tool
    and the daily smoke CI.
    """
    url = f"{BASE}/market/ticker?market=btc_tl"
    try:
        rows = fetch_ticker("btc_tl")
        if not rows:
            return {
                "status": "error",
                "http_status": 200,
                "url": url,
                "detail": "ticker returned an empty list",
            }
    except ParibuError as e:
        msg = str(e)
        if "403" in msg:
            return {"status": "blocked", "http_status": 403, "url": url, "detail": msg}
        if "429" in msg:
            return {"status": "blocked", "http_status": 429, "url": url, "detail": msg}
        return {"status": "error", "http_status": None, "url": url, "detail": msg}
    return {"status": "ok", "http_status": 200, "url": url}
