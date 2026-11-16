"""Parsers for Paribu's public API responses (docs.paribu.com/api).

All numbers arrive as strings; parsers normalise them to floats.
Market ids are lowercase ``base_quote`` (e.g. ``btc_tl`` — the Turkish
lira quote is spelled ``tl``).
"""
from __future__ import annotations

import re

_MARKET_RE = re.compile(r"^[a-z0-9]+_[a-z0-9]+$")


def normalize_market(market: str) -> str:
    """Accept "BTC_TL", "btc-tl", "btc/tl" and normalise to "btc_tl".

    Raises ValueError for anything that cannot be a market id.
    """
    m = (market or "").strip().lower().replace("-", "_").replace("/", "_").replace(" ", "_")
    if not _MARKET_RE.match(m):
        raise ValueError(
            f"invalid market id {market!r}: use lowercase base_quote, e.g. 'btc_tl'"
        )
    return m


def _f(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_ticker_row(row: dict) -> dict:
    """One /market/ticker row -> normalised 24h snapshot."""
    market = row["market"]
    base, quote = market.rsplit("_", 1)
    return {
        "market": market,
        "base": base,
        "quote": quote,
        "last": _f(row.get("last")),
        "first": _f(row.get("first")),
        "low": _f(row.get("low")),
        "high": _f(row.get("high")),
        "average": _f(row.get("average")),
        "change": _f(row.get("change")),
        "percentage": _f(row.get("percentage")),
        "volume": _f(row.get("volume")),
        "pair_volume": _f(row.get("pair_volume")),
    }


def parse_ticker_list(rows: list) -> list[dict]:
    return [parse_ticker_row(r) for r in rows]


def parse_orderbook(data: dict, market: str) -> dict:
    """One /orderbook body -> levels plus best bid/ask, mid and spread."""
    bids = [[_f(p), _f(a)] for p, a in data.get("bids") or []]
    asks = [[_f(p), _f(a)] for p, a in data.get("asks") or []]
    best_bid = bids[0][0] if bids else None
    best_ask = asks[0][0] if asks else None
    spread = mid = spread_pct = None
    if best_bid is not None and best_ask is not None:
        spread = round(best_ask - best_bid, 8)
        mid = round((best_ask + best_bid) / 2, 8)
        if mid:
            spread_pct = round(100 * spread / mid, 4)
    return {
        "market": market,
        "timestamp": data.get("timestamp"),
        "seq": data.get("seq"),
        "best_bid": best_bid,
        "best_ask": best_ask,
        "spread": spread,
        "mid_price": mid,
        "spread_pct": spread_pct,
        "bids": bids,
        "asks": asks,
    }


def parse_trades(rows: list, market: str) -> dict:
    """Recent /trades rows, newest first."""
    trades = [
        {
            "price": _f(t.get("price")),
            "amount": _f(t.get("amount")),
            "time": t.get("time"),
            "side": t.get("trade"),
        }
        for t in rows
    ]
    buys = sum(1 for t in trades if t["side"] == "buy")
    return {
        "market": market,
        "count": len(trades),
        "buys": buys,
        "sells": len(trades) - buys,
        "trades": trades,
    }


def parse_markets(payload: dict) -> list[dict]:
    """The config `markets` scope -> one row per tradable pair."""
    markets = payload.get("markets") or {}
    rows = []
    for market_id, m in markets.items():
        pairs = m.get("pairs") or {}
        rows.append(
            {
                "market": market_id,
                "base": pairs.get("market"),
                "quote": pairs.get("payment"),
                "price_precision": (m.get("precisions") or {}).get("price"),
                "amount_precision": (m.get("precisions") or {}).get("amount"),
                "price_step": (m.get("steps") or {}).get("price"),
                "amount_step": (m.get("steps") or {}).get("amount"),
                "labels": m.get("labels") or [],
                "otc_only": bool(m.get("otc_only", False)),
            }
        )
    rows.sort(key=lambda r: r["market"])
    return rows


def parse_currency(payload: dict, currency: str) -> dict:
    """The config currencies/fee_matrix/networks scopes -> one currency.

    Raises KeyError when the currency is not listed.
    """
    currencies = payload.get("currencies") or {}
    cur = currencies.get(currency)
    if cur is None:
        raise KeyError(f"unknown currency {currency!r}")
    fee_matrix = payload.get("fee_matrix") or {}
    networks = payload.get("networks") or {}
    net_rows = []
    for net_id in cur.get("networks") or []:
        net = networks.get(net_id) or {}
        fees = (fee_matrix.get(currency) or {}).get(net_id)
        net_rows.append(
            {
                "network": net_id,
                "name": net.get("name"),
                "estimated_arrival_minutes": net.get("estimated_arrival_minutes"),
                "explorer": (net.get("explorer") or {}).get("address"),
                "withdrawal_fee": fees[0] if isinstance(fees, list) and fees else fees,
            }
        )
    return {
        "symbol": cur.get("symbol"),
        "name": cur.get("name"),
        "type": cur.get("type"),
        "precision": cur.get("precision"),
        "step": cur.get("step"),
        "listing_date": cur.get("listing_date"),
        "labels": cur.get("labels") or [],
        "deposit_limits": cur.get("deposit_limits") or {},
        "withdraw_limits": cur.get("withdraw_limits") or {},
        "networks": net_rows,
    }


def market_movers(rows: list[dict], direction: str, limit: int) -> list[dict]:
    """Top gainers or losers by 24h percentage change."""
    rows = [r for r in rows if r.get("percentage") is not None]
    rows.sort(key=lambda r: r["percentage"], reverse=(direction == "gainers"))
    return rows[:limit]
