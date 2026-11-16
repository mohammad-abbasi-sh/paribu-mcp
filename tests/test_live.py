"""Live tests: hit the real Paribu public API (no key, read-only).

Kept small and polite (~0.5s between requests, one call per tool).
Run with:  python -m pytest tests/test_live.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from paribu_mcp import http, markets as M  # noqa: E402
from paribu_mcp.server import (  # noqa: E402
    paribu_get_currency,
    paribu_get_orderbook,
    paribu_get_recent_trades,
    paribu_get_ticker,
    paribu_health,
    paribu_list_markets,
    paribu_market_movers,
)


def _parse(out: str) -> dict:
    return json.loads(out)


def test_live_ticker_single():
    out = _parse(paribu_get_ticker(market="btc_tl"))
    assert "error" not in out
    t = out["ticker"]
    assert t["market"] == "btc_tl"
    assert t["last"] and t["last"] > 1_000_000  # BTC in lira
    assert t["low"] <= t["last"] <= t["high"]


def test_live_ticker_list_sorted():
    out = _parse(paribu_get_ticker(quote="tl", limit=5))
    assert "error" not in out
    assert out["total_markets"] >= 200
    assert len(out["tickers"]) == 5
    vols = [t["pair_volume"] for t in out["tickers"]]
    assert vols == sorted(vols, reverse=True)


def test_live_orderbook():
    out = _parse(paribu_get_orderbook("eth_tl", limit=5))
    assert "error" not in out
    assert out["best_bid"] and out["best_ask"]
    assert out["best_bid"] < out["best_ask"]
    assert out["spread"] > 0
    assert len(out["bids"]) == 5 and len(out["asks"]) == 5


def test_live_orderbook_unknown_market():
    out = _parse(paribu_get_orderbook("zzz_tl"))
    assert "error" in out
    assert "unknown market" in out["error"]


def test_live_recent_trades():
    out = _parse(paribu_get_recent_trades("btc_tl", limit=3))
    assert "error" not in out
    assert out["count"] == 3
    assert out["buys"] + out["sells"] == 3
    assert all(t["price"] for t in out["trades"])


def test_live_list_markets():
    out = _parse(paribu_list_markets(quote="usdt", limit=5))
    assert "error" not in out
    assert out["total_markets"] >= 200
    assert all(m["quote"] == "usdt" for m in out["markets"])


def test_live_get_currency():
    out = _parse(paribu_get_currency("usdt"))
    assert "error" not in out
    assert out["name"] == "Tether"
    assert len(out["networks"]) >= 3
    assert any(n["withdrawal_fee"] for n in out["networks"])


def test_live_market_movers():
    out = _parse(paribu_market_movers("gainers", limit=5))
    assert "error" not in out
    assert len(out["movers"]) == 5
    pcts = [m["percentage"] for m in out["movers"]]
    assert pcts == sorted(pcts, reverse=True)


def test_live_health():
    out = _parse(paribu_health())
    assert out["status"] == "ok"
    assert out["http_status"] == 200
