"""Daily smoke probe (CI): ticker + one order book must answer 200.

Run with:  python tests/smoke_live.py
Exit 0 = API reachable, exit 1 = blocked/error (visible in CI).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from paribu_mcp import http, markets as M


def main() -> int:
    try:
        rows = M.parse_ticker_list(http.fetch_ticker("btc_tl"))
        assert rows and rows[0]["market"] == "btc_tl"
        assert rows[0]["last"] and rows[0]["last"] > 1_000_000
        book = http.fetch_orderbook("btc_tl", 5)
        assert book and book.get("bids") and book.get("asks")
        print(
            f"SMOKE OK: ticker btc_tl last={rows[0]['last']:,.0f} TL, "
            f"order book {len(book['bids'])} bids / {len(book['asks'])} asks"
        )
        return 0
    except Exception as e:  # noqa: BLE001 — smoke must report, not crash
        print(f"SMOKE FAIL: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
