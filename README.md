# paribu-mcp 🇹🇷

mcp-name: io.github.mohammad-abbasi-sh/paribu-mcp

Unofficial **read-only** MCP server for **Paribu** (paribu.com), Türkiye's largest crypto exchange — live 24h tickers for 266 markets (BTC, ETH and 190+ coins vs TL and USDT), order books with spread and mid price, recent trades, the full 467-market catalogue, and currency metadata with networks and withdrawal fees.

> Part of the "Turkey MCP factory". Not affiliated with Paribu. Data comes from Paribu's official public API (`api.paribu.com`, docs at `docs.paribu.com/api`) — no login, no API key, read-only.

## For AI agents

- **Market ids** are lowercase `base_quote`, e.g. `btc_tl` — the Turkish lira quote is spelled `tl`, not `try`.
- **Ticker**: `paribu_get_ticker` with a market returns one 24h snapshot; without a market it returns a ranked list (default sort: pair volume). 266 markets have live tickers; the config lists 467 pairs (some are OTC-only or not yet trading).
- **Order book**: `paribu_get_orderbook` returns best bid/ask, spread, mid price and the levels. An unknown market answers with an error — Paribu itself returns HTTP 200 with a null body for it.
- **Trades**: `paribu_get_recent_trades` — limit 1–20 (the API maximum), newest first.
- **Catalogue**: `paribu_list_markets` lists all 467 pairs with price/amount precision and steps; `paribu_get_currency` returns a currency's networks, deposit/withdrawal limits and per-network withdrawal fees.
- **Movers**: `paribu_market_movers` ranks the top gainers/losers by 24h percentage.
- Every response carries `fetched_at` (UTC) and `source: api.paribu.com`.

## Install

```bash
uvx paribu-mcp
```

Or add to your MCP client config (e.g. Claude Desktop):

```json
{
  "mcpServers": {
    "paribu": {
      "command": "uvx",
      "args": ["paribu-mcp"]
    }
  }
}
```

## Tools

| Tool | What it does |
| --- | --- |
| `paribu_get_ticker` | 24h ticker for one market, or a ranked list of all 266 markets (filter by `tl`/`usdt`, sort by volume/change/%) |
| `paribu_get_orderbook` | Live order book: best bid/ask, spread, mid price, levels (1–100 per side) |
| `paribu_get_recent_trades` | Most recent public trades, newest first (1–20) |
| `paribu_list_markets` | Full 467-pair catalogue with precision, steps, labels, OTC flag |
| `paribu_get_currency` | Currency metadata: networks, arrival times, explorers, withdrawal fees, limits |
| `paribu_market_movers` | Top gainers / losers over the last 24h |
| `paribu_health` | Is the Paribu public API reachable right now? |

## Example

```json
{ "market": "btc_tl", "last": 3252946.0, "low": 3246001.0, "high": 3344137.0,
  "change": -84957.0, "percentage": -2.54, "volume": 32.147208,
  "pair_volume": 106109641.0 }
```

## Caveats

- Prices are live market data, not investment advice — verify on paribu.com before acting on them.
- An unknown market id on the ticker endpoint returns HTTP 500 with code `5001`; on the order book it returns HTTP 200 with a null body.
- The config endpoint is polled at most once per call; Paribu recommends polling it no more than every 60 seconds.
- Transport uses Chrome TLS impersonation with a plain-requests fallback; requests are spaced ~0.5s apart.

## Development

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"  # or: pip install -e . pytest
.venv/bin/python -m pytest tests/test_markets.py -v   # offline, recorded fixtures
.venv/bin/python -m pytest tests/test_live.py -v      # live, against api.paribu.com
.venv/bin/python tests/smoke_live.py                  # daily CI probe
```

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
