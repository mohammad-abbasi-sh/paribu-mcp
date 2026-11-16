"""MCP server: unofficial read-only access to Paribu crypto exchange."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from . import http as _http
from . import markets as _M

mcp = FastMCP("paribu-mcp")

INSTRUCTIONS = """\
Unofficial read-only MCP server for Paribu (paribu.com), Türkiye's \
largest crypto exchange — live 24h tickers for 266 markets (BTC/ETH/ \
190+ coins vs TL and USDT), order books with spread and mid price, \
recent trades, the full 467-market catalogue with price/amount steps, \
currency metadata with networks and withdrawal fees, and top \
gainers/losers. Uses Paribu's official public API (api.paribu.com) — \
no login, no API key. Market ids are lowercase base_quote, e.g. \
btc_tl (the lira quote is spelled tl). Read-only; transport uses \
Chrome TLS impersonation with a plain-requests fallback; requests are \
spaced ~0.5s apart. Built by Mohammad Abbasi (mohammad-abbasi-sh) — https://almanibama.ir · https://mabbasi.ir — Turkey \
MCP factory.\
"""

_SOURCE = "api.paribu.com"
_DISCLAIMER = (
    "Unofficial read-only market data from Paribu's public API; "
    "verify on paribu.com before acting on it. Not investment advice."
)
_SORTS = ("pair_volume", "percentage", "volume", "change", "last")


def _envelope() -> dict:
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": _SOURCE,
        "disclaimer": _DISCLAIMER,
    }


def _ok(payload: dict) -> str:
    return json.dumps({**_envelope(), **payload}, ensure_ascii=False)


def _err(e: Exception) -> str:
    return _ok({"error": str(e)})


def _validate_limit(limit: int, lo: int, hi: int) -> int:
    if not lo <= limit <= hi:
        raise ValueError(f"limit must be between {lo} and {hi}")
    return limit


@mcp.tool()
def paribu_get_ticker(
    market: str | None = None,
    quote: str | None = None,
    limit: int = 10,
    sort: str = "pair_volume",
) -> str:
    """24h ticker snapshot(s) from Paribu.
    market: one market id, e.g. "btc_tl" (omit for a ranked list of all
    266 markets). quote: filter the list to "tl" or "usdt" (ignored
    when market is given). limit 1..266. sort: "pair_volume" (default),
    "percentage", "volume", "change" or "last" — descending.
    Returns last/first/low/high/average price, 24h change and
    percentage, base volume and pair (quote) volume."""
    try:
        _validate_limit(limit, 1, 266)
        if sort not in _SORTS:
            raise ValueError(f"sort must be one of {', '.join(_SORTS)}")
        if market:
            m = _M.normalize_market(market)
            rows = _M.parse_ticker_list(_http.fetch_ticker(m))
            return _ok({"market": m, "count": len(rows), "ticker": rows[0] if rows else None})
        rows = _M.parse_ticker_list(_http.fetch_ticker())
        if quote:
            q = quote.strip().lower()
            if q not in ("tl", "usdt"):
                raise ValueError("quote must be 'tl' or 'usdt'")
            rows = [r for r in rows if r["quote"] == q]
        rows.sort(key=lambda r: (r.get(sort) is None, r.get(sort) or 0), reverse=True)
        return _ok(
            {
                "quote": quote,
                "sort": sort,
                "total_markets": len(rows),
                "count": len(rows[:limit]),
                "tickers": rows[:limit],
            }
        )
    except (ValueError, _http.ParibuError) as e:
        return _err(e)


@mcp.tool()
def paribu_get_orderbook(market: str, limit: int = 20) -> str:
    """Live order book for one market: best bid/ask, spread, mid price
    and the price levels on each side.
    market: e.g. "btc_tl". limit 1..100 price levels per side
    (default 20)."""
    try:
        m = _M.normalize_market(market)
        _validate_limit(limit, 1, 100)
        data = _http.fetch_orderbook(m, limit)
        if data is None:
            raise ValueError(f"unknown market {m!r} — Paribu lists no order book for it")
        book = _M.parse_orderbook(data, m)
        book["bids"] = book["bids"][:limit]
        book["asks"] = book["asks"][:limit]
        return _ok(book)
    except (ValueError, _http.ParibuError) as e:
        return _err(e)


@mcp.tool()
def paribu_get_recent_trades(market: str, limit: int = 10) -> str:
    """Most recent public trades for one market, newest first.
    market: e.g. "btc_tl". limit 1..20 (the API maximum)."""
    try:
        m = _M.normalize_market(market)
        _validate_limit(limit, 1, 20)
        rows = _http.fetch_trades(m, limit)
        return _ok(_M.parse_trades(rows, m))
    except (ValueError, _http.ParibuError) as e:
        return _err(e)


@mcp.tool()
def paribu_list_markets(quote: str | None = None, limit: int = 50) -> str:
    """The full Paribu market catalogue from the exchange config:
    467 pairs with base/quote, price and amount precision and steps,
    labels and the OTC-only flag.
    quote: filter to "tl" or "usdt" (omit for all). limit 1..467."""
    try:
        _validate_limit(limit, 1, 467)
        rows = _M.parse_markets(_http.fetch_config("markets"))
        if quote:
            q = quote.strip().lower()
            if q not in ("tl", "usdt"):
                raise ValueError("quote must be 'tl' or 'usdt'")
            rows = [r for r in rows if r["quote"] == q]
        return _ok(
            {
                "quote": quote,
                "total_markets": len(rows),
                "count": len(rows[:limit]),
                "markets": rows[:limit],
            }
        )
    except (ValueError, _http.ParibuError) as e:
        return _err(e)


@mcp.tool()
def paribu_get_currency(currency: str) -> str:
    """Currency metadata from the exchange config: name, type,
    precision/step, listing date, deposit and withdrawal limits, and
    per-network details (name, estimated arrival, explorer link,
    withdrawal fee).
    currency: e.g. "btc", "eth", "usdt", "xrp"."""
    try:
        c = (currency or "").strip().lower()
        if not c:
            raise ValueError("currency must not be empty")
        payload = _http.fetch_config("currencies,fee_matrix,networks")
        try:
            cur = _M.parse_currency(payload, c)
        except KeyError as e:
            raise ValueError(str(e)) from e
        return _ok(cur)
    except (ValueError, _http.ParibuError) as e:
        return _err(e)


@mcp.tool()
def paribu_market_movers(
    direction: str = "gainers", quote: str | None = None, limit: int = 10
) -> str:
    """Top gainers or losers on Paribu over the last 24h, ranked by
    percentage change.
    direction: "gainers" (default) or "losers". quote: filter to "tl"
    or "usdt" (omit for all). limit 1..50."""
    try:
        if direction not in ("gainers", "losers"):
            raise ValueError("direction must be 'gainers' or 'losers'")
        _validate_limit(limit, 1, 50)
        rows = _M.parse_ticker_list(_http.fetch_ticker())
        if quote:
            q = quote.strip().lower()
            if q not in ("tl", "usdt"):
                raise ValueError("quote must be 'tl' or 'usdt'")
            rows = [r for r in rows if r["quote"] == q]
        movers = _M.market_movers(rows, direction, limit)
        return _ok(
            {
                "direction": direction,
                "quote": quote,
                "count": len(movers),
                "movers": movers,
            }
        )
    except (ValueError, _http.ParibuError) as e:
        return _err(e)


@mcp.tool()
def paribu_health() -> str:
    """Check whether Paribu's public API is reachable right now.

    Returns status ok (HTTP 200), blocked (HTTP 403/429 — bot wall or
    rate limit) or error, plus the HTTP status and the probed URL.
    One polite request; it does not fetch any listings."""
    return _ok(_http.health_check())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    import sys

    sys.exit(main())
