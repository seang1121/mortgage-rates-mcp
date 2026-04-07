# Mortgage Rates MCP Server

> Compare mortgage rates across **19 major US lenders** and **2 national benchmarks** through any AI assistant. 12 tools for real-time rates, comparison, calculation, recommendations, and alerts. Built for realtors, mortgage brokers, and homebuyers.

![Python](https://img.shields.io/badge/python-3.10+-blue)
![Lenders](https://img.shields.io/badge/lenders-19-brightgreen)
![Tools](https://img.shields.io/badge/MCP_tools-12-blue)
![Schedule](https://img.shields.io/badge/updates-7am_%26_7pm_EST-orange)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Quick Start

### For AI Users (Claude, ChatGPT, Cursor, Windsurf, VS Code)

```bash
pip install mortgage-rates-mcp
```

Add to your MCP client config:

**Claude Desktop** (`~/.config/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "mortgage-rates": {
      "command": "mortgage-rates-mcp",
      "env": {
        "MORTGAGE_API_URL": "https://your-api-url.com",
        "MORTGAGE_API_KEY": "mort_your_key_here"
      }
    }
  }
}
```

**ChatGPT Desktop** (MCP settings):
```json
{
  "mortgage-rates": {
    "command": "mortgage-rates-mcp",
    "env": {
      "MORTGAGE_API_URL": "https://your-api-url.com",
      "MORTGAGE_API_KEY": "mort_your_key_here"
    }
  }
}
```

**Cursor** (`.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "mortgage-rates": {
      "command": "mortgage-rates-mcp",
      "env": {
        "MORTGAGE_API_URL": "https://your-api-url.com",
        "MORTGAGE_API_KEY": "mort_your_key_here"
      }
    }
  }
}
```

Then ask your AI: *"What are today's best mortgage rates?"*

---

## 12 MCP Tools

| Tool | What It Does |
|------|-------------|
| `get_rates` | All current rates grouped by product (30yr, 15yr, ARM, FHA, VA) |
| `get_best_rate` | Single best rate for a loan type across all lenders |
| `compare_lenders` | Side-by-side: "Compare Chase vs Wells Fargo vs Navy Federal" |
| `get_rate_history` | 90-day trend with AM/PM tracking and direction indicator |
| `get_lender_details` | All products from one specific lender |
| `get_system_status` | Health check — last scrape time, lender count, uptime |
| `calculate_payment` | Monthly P&I, total interest, full breakdown |
| `generate_rate_sheet` | Client-ready PNG rate card image for texting to buyers |
| `set_rate_alert` | Get notified when rates drop below your target |
| `compare_scenarios` | 30yr vs 15yr vs ARM with breakeven analysis |
| `estimate_savings` | "Switching from Chase to Navy Federal saves you $141/month" |
| `get_recommendation` | AI-ranked top 5 picks with explanations based on your profile |

---

## 19 Lenders + 2 Benchmarks

### Tier 1 — Direct API (instant, most reliable)
| Lender | Data Source |
|--------|-----------|
| Freddie Mac (benchmark) | Weekly PMMS CSV |
| Mortgage News Daily (benchmark) | Real-time HTML |
| PennyMac | Public REST JSON API |
| Citizens Bank | Static JSON rate file |

### Tier 2 — Stealth Browser (reliable)
Bank of America, Wells Fargo, Citi, Navy Federal CU, SoFi, US Bank, Guaranteed Rate, Truist, Mr. Cooper

### Tier 3 — Stealth Browser (heavy anti-bot)
Chase (Akamai), Rocket Mortgage (Akamai), PNC (Akamai), USAA (Akamai), Flagstar (Cloudflare), LoanDepot (reCAPTCHA)

---

## Rate Schedule

Rates are scraped twice daily:
- **7:00 AM EST** — captures overnight changes
- **7:00 PM EST** — captures intraday movement

Both AM and PM data points are stored for trend analysis.

---

## Data Accuracy

Every scraped rate passes through a validation pipeline:
1. **Sanity bounds** — reject rates outside 2.5%–14.0%
2. **Benchmark cross-reference** — flag if >1.5% from national average
3. **APR validation** — APR must be >= base rate
4. **Product consistency** — 30yr must be > 15yr for same lender
5. **Staleness detection** — flag unchanged rates after 5+ scrapes

Failed lenders serve the last known good rate with a `stale` flag and timestamp.

---

## Self-Hosting the Backend

```bash
git clone https://github.com/seang1121/mortgage-rates-mcp.git
cd mortgage-rates-mcp
pip install -r requirements.txt
python -m patchright install chromium
cp .env.example .env  # edit with your settings
python scripts/create_database.py
python scripts/create_admin.py
python backend/app.py
```

The API runs on port 5001 by default.

---

## API Registration

Get a free API key:

```bash
curl -X POST http://localhost:5001/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "your_password"}'
```

Returns your `mort_*` API key. Currently **free with unlimited access**.

---

## Disclaimer

Rates shown are publicly advertised rates scraped from lender websites and are **not personalized quotes**. Actual rates depend on credit score, loan amount, property type, down payment, and other factors. This is not financial advice. Contact lenders directly for official quotes.

See [DISCLAIMER.md](DISCLAIMER.md) for full legal details including TILA/RESPA compliance.

---

## License

MIT License. See [LICENSE](LICENSE).
