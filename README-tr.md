# paribu-mcp 🇹🇷

mcp-name: io.github.mohammad-abbasi-sh/paribu-mcp

**Paribu** (paribu.com) için resmi olmayan, **salt okunur** MCP sunucusu — Türkiye'nin en büyük kripto borsası: 266 piyasada canlı 24 saatlik fiyatlar (BTC, ETH ve 190+ coin; TL ve USDT karşısında), spread ve orta fiyatlı emir defterleri, son işlemler, 467 piyasadan oluşan tam katalog ve ağlar ile çekim ücretlerini içeren para birimi bilgileri.

> "Turkey MCP factory" projesinin bir parçasıdır. Paribu ile bağlantısı yoktur. Veriler Paribu'nun resmi herkese açık API'sinden gelir (`api.paribu.com`, belgeler: `docs.paribu.com/api`) — giriş yok, API anahtarı yok, salt okunur.

## Yapay zekâ ajanları için

- **Piyasa kodları** küçük harfle `baz_karşılık` biçimindedir, örn. `btc_tl` — Türk lirası karşılığı `tl` olarak yazılır, `try` değil.
- **Fiyat (ticker)**: `paribu_get_ticker` bir piyasayla çağrılırsa tek bir 24 saatlik özet döner; piyasasız çağrılırsa sıralı bir liste döner (varsayılan sıralama: çift hacmi). Canlı fiyat 266 piyasada vardır; yapılandırmada 467 çift listelenir (bazıları yalnızca OTC'dir veya henüz işlem görmüyordur).
- **Emir defteri**: `paribu_get_orderbook` en iyi alış/satış fiyatını, spread'i, orta fiyatı ve seviyeleri döner. Bilinmeyen bir piyasada hata döner — Paribu'nun kendisi bu durumda HTTP 200 ile boş gövde döner.
- **İşlemler**: `paribu_get_recent_trades` — limit 1–20 (API'nin azamisi), en yeniden eskiye.
- **Katalog**: `paribu_list_markets` 467 çiftin tamamını fiyat/tutar hassasiyeti ve adımlarıyla listeler; `paribu_get_currency` bir para biriminin ağlarını, yatırma/çekme limitlerini ve ağ başına çekim ücretlerini döner.
- **Hareket edenler**: `paribu_market_movers` son 24 saatin en çok yükselen/düşenlerini yüzde değişime göre sıralar.
- Her yanıt `fetched_at` (UTC) ve `source: api.paribu.com` içerir.

## Kurulum

```bash
uvx paribu-mcp
```

Veya MCP istemcinizin yapılandırmasına ekleyin (örn. Claude Desktop):

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

## Araçlar

| Araç | Ne yapar |
| --- | --- |
| `paribu_get_ticker` | Bir piyasanın 24 saatlik özeti veya 266 piyasanın sıralı listesi (`tl`/`usdt` filtresi, hacim/değişim/% sıralaması) |
| `paribu_get_orderbook` | Canlı emir defteri: en iyi alış/satış, spread, orta fiyat, seviyeler (her tarafta 1–100) |
| `paribu_get_recent_trades` | En son herkese açık işlemler, en yeniden eskiye (1–20) |
| `paribu_list_markets` | 467 çiftin tam kataloğu: hassasiyet, adımlar, etiketler, OTC işareti |
| `paribu_get_currency` | Para birimi bilgileri: ağlar, varış süreleri, gezgin bağlantıları, çekim ücretleri, limitler |
| `paribu_market_movers` | Son 24 saatin en çok yükselen / düşenleri |
| `paribu_health` | Paribu herkese açık API'sine şu an ulaşılabiliyor mu? |

## Örnek

```json
{ "market": "btc_tl", "last": 3252946.0, "low": 3246001.0, "high": 3344137.0,
  "change": -84957.0, "percentage": -2.54, "volume": 32.147208,
  "pair_volume": 106109641.0 }
```

## Dikkat edilecekler

- Fiyatlar canlı piyasa verisidir, yatırım tavsiyesi değildir — işlem yapmadan önce paribu.com'dan doğrulayın.
- Bilinmeyen bir piyasa kodu, fiyat uç noktasında HTTP 500 ve `5001` kodu; emir defterinde HTTP 200 ile boş gövde döner.
- Yapılandırma uç noktası çağrı başına en fazla bir kez sorgulanır; Paribu 60 saniyeden sık sorgulanmamasını önerir.
- Aktarım Chrome TLS taklidi ve düz requests yedeği kullanır; istekler ~0,5 sn arayla gönderilir.

## Geliştirme

```bash
python -m venv .venv && .venv/bin/pip install -e . pytest
.venv/bin/python -m pytest tests/test_markets.py -v   # çevrimdışı, kayıtlı örnekler
.venv/bin/python -m pytest tests/test_live.py -v      # canlı, api.paribu.com'a karşı
.venv/bin/python tests/smoke_live.py                  # günlük CI denetimi
```

Built by [Mohammad Abbasi](https://github.com/mohammad-abbasi-sh) — [Almanibama](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
