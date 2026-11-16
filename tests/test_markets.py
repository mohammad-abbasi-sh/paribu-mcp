"""Offline tests: parse real captured fixtures (see tests/fixtures/)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from paribu_mcp import markets as M  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures"


def load(name: str):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- market ids

def test_normalize_market():
    assert M.normalize_market("btc_tl") == "btc_tl"
    assert M.normalize_market("BTC_TL") == "btc_tl"
    assert M.normalize_market("btc-tl") == "btc_tl"
    assert M.normalize_market(" BTC/TL ") == "btc_tl"
    assert M.normalize_market("1inch_usdt") == "1inch_usdt"
    for bad in ("", "btc", "btc_tl_extra_long_x", "btc tl tl", "btc_tl!"):
        with pytest.raises(ValueError):
            M.normalize_market(bad)


# ---------------------------------------------------------------- ticker

def test_ticker_single():
    rows = M.parse_ticker_list(load("ticker_btc.json"))
    assert len(rows) == 1
    t = rows[0]
    assert t["market"] == "btc_tl"
    assert t["base"] == "btc" and t["quote"] == "tl"
    assert t["last"] == 3252946.0
    assert t["first"] == 3337903.0
    assert t["low"] == 3246001.0
    assert t["high"] == 3344137.0
    assert t["average"] == 3300742.0
    assert t["change"] == -84957.0
    assert t["percentage"] == -2.54
    assert t["volume"] == 32.147208
    assert t["pair_volume"] == 106109641.0


def test_ticker_all_count_and_quotes():
    rows = M.parse_ticker_list(load("ticker_all.json"))
    assert len(rows) == 266
    assert {r["quote"] for r in rows} == {"tl", "usdt"}
    assert all(r["last"] is not None and r["last"] > 0 for r in rows)
    btc = [r for r in rows if r["market"] == "btc_tl"][0]
    assert btc["last"] > 3_000_000  # BTC in lira, sanity bound


def test_ticker_unknown_is_error_body():
    body = load("ticker_unknown.json")
    assert body["code"] == 5001
    assert body["message"] == "Internal Server Error"


# ---------------------------------------------------------------- order book

def test_orderbook_parse():
    book = M.parse_orderbook(load("orderbook_btc.json"), "btc_tl")
    assert book["market"] == "btc_tl"
    assert book["timestamp"] == 1794821008
    assert book["seq"] == 64568542
    assert len(book["bids"]) == 5 and len(book["asks"]) == 5
    assert book["bids"][0] == [3252859.0, 0.046508]
    assert book["asks"][0] == [3253987.0, 0.105706]
    assert book["best_bid"] == 3252859.0
    assert book["best_ask"] == 3253987.0
    assert book["spread"] == 1128.0
    assert book["mid_price"] == 3253423.0
    assert abs(book["spread_pct"] - 0.0347) < 0.001
    # bids descend, asks ascend
    assert [b[0] for b in book["bids"]] == sorted(
        (b[0] for b in book["bids"]), reverse=True
    )
    assert [a[0] for a in book["asks"]] == sorted(a[0] for a in book["asks"])


def test_orderbook_unknown_is_null():
    assert load("orderbook_unknown.json") is None


# ---------------------------------------------------------------- trades

def test_trades_parse():
    data = M.parse_trades(load("trades_btc.json"), "btc_tl")
    assert data["market"] == "btc_tl"
    assert data["count"] == 5
    assert data["buys"] == 2 and data["sells"] == 3
    first = data["trades"][0]
    assert first["price"] == 3252946.0
    assert first["amount"] == 0.018632
    assert first["side"] == "sell"
    assert first["time"].startswith("2026-11-16T09:23:10")
    # newest first
    times = [t["time"] for t in data["trades"]]
    assert times == sorted(times, reverse=True)


def test_trades_bad_limit_is_4001():
    body = load("trades_bad.json")
    assert body["code"] == 4001
    assert "20" in body["message"]


# ---------------------------------------------------------------- config: markets

def test_config_markets_parse():
    rows = M.parse_markets(load("config_markets.json")["payload"])
    assert len(rows) == 467
    tl = [r for r in rows if r["quote"] == "tl"]
    usdt = [r for r in rows if r["quote"] == "usdt"]
    assert len(tl) == 243 and len(usdt) == 224
    btc = [r for r in rows if r["market"] == "btc_tl"][0]
    assert btc["base"] == "btc" and btc["quote"] == "tl"
    assert btc["amount_precision"] == 6
    assert btc["price_precision"] == 0
    assert btc["price_step"] == "1"
    assert btc["labels"] == ["crypto_tl"]
    assert btc["otc_only"] is False
    assert [r["market"] for r in rows] == sorted(r["market"] for r in rows)


# ---------------------------------------------------------------- config: currency

def test_config_currency_btc():
    cur = M.parse_currency(load("config_currency.json")["payload"], "btc")
    assert cur["symbol"] == "btc"
    assert cur["name"] == "Bitcoin"
    assert cur["type"] == "crypto"
    assert cur["precision"] == 8
    assert cur["listing_date"] == "2017-02-14T00:00:00Z"
    assert cur["withdraw_limits"]["min_once"] == "0.00006"
    assert len(cur["networks"]) == 1
    net = cur["networks"][0]
    assert net["network"] == "btc"
    assert net["name"] == "Bitcoin (BTC)"
    assert net["estimated_arrival_minutes"] == 10
    assert "blockchain.com" in net["explorer"]
    assert net["withdrawal_fee"] == {"btc": "0.00005"}


def test_config_currency_usdt_networks_and_fees():
    cur = M.parse_currency(load("config_currency.json")["payload"], "usdt")
    assert cur["name"] == "Tether"
    assert [n["network"] for n in cur["networks"]] == ["eth", "sol", "trx", "arb"]
    fees = {n["network"]: n["withdrawal_fee"] for n in cur["networks"]}
    assert fees["eth"] == {"usdt": "1.5"}
    assert fees["trx"] == {"usdt": "5"}
    assert fees["arb"] == {"usdt": "0.25"}


def test_config_currency_unknown_raises():
    with pytest.raises(KeyError):
        M.parse_currency(load("config_currency.json")["payload"], "not_a_coin")


# ---------------------------------------------------------------- movers

def test_market_movers():
    rows = M.parse_ticker_list(load("ticker_all.json"))
    gainers = M.market_movers(rows, "gainers", 5)
    assert len(gainers) == 5
    pcts = [r["percentage"] for r in gainers]
    assert pcts == sorted(pcts, reverse=True)
    losers = M.market_movers(rows, "losers", 5)
    assert [r["percentage"] for r in losers] == sorted(
        (r["percentage"] for r in losers)
    )
    assert gainers[0]["percentage"] >= losers[0]["percentage"]
