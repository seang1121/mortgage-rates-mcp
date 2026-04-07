# 🏠 Mortgage Rates MCP Server

### The first AI-native mortgage rate comparison tool. 17 major lenders. 12 powerful tools. One command.

> **"What's the best 30-year rate right now?"** — Ask your AI assistant and get a real answer, backed by live data from the biggest lenders in America.

![Python](https://img.shields.io/badge/python-3.10+-blue?style=flat-square)
![Lenders](https://img.shields.io/badge/lenders-17-brightgreen?style=flat-square)
![Tools](https://img.shields.io/badge/MCP_tools-12-blue?style=flat-square)
![Updates](https://img.shields.io/badge/updates-7am_%26_7pm_EST-orange?style=flat-square)
![Free](https://img.shields.io/badge/price-free-success?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)

---

## 🚀 Why This Exists

Shopping for a mortgage sucks. You open 15 bank websites, enter your info on each one, wait for JavaScript to load, compare numbers in a spreadsheet, and do it all again tomorrow because rates changed.

**We fixed that.**

This MCP server scrapes live rates from 18 of the largest mortgage lenders in the US — twice daily at 7am and 7pm EST — and serves them through any AI assistant. Ask Claude, ChatGPT, Cursor, or any MCP-compatible client for rates, and get an instant, accurate answer.

No lead generation. No affiliate links. No selling your data. Just rates.

---

## ⚡ Quick Start

```bash
pip install mortgage-rates-mcp
```

Then add it to your AI client:

<details>
<summary>🟣 Claude Desktop</summary>

Edit `~/.config/Claude/claude_desktop_config.json`:
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
</details>

<details>
<summary>🟢 ChatGPT Desktop</summary>

Add to MCP server settings:
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
</details>

<details>
<summary>🔵 Cursor / Windsurf / VS Code</summary>

Add to `.cursor/mcp.json` (or equivalent):
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
</details>

Then just ask: *"What are today's best mortgage rates?"*

---

## 🛠️ 12 Tools — Everything a Broker Needs

| Tool | What You Can Ask |
|------|-----------------|
| 🏷️ `get_rates` | *"Show me all current rates"* |
| 🏆 `get_best_rate` | *"What's the best 30-year fixed right now?"* |
| ⚖️ `compare_lenders` | *"Compare Chase vs Wells Fargo vs Navy Federal"* |
| 📈 `get_rate_history` | *"How have rates moved this month?"* |
| 🏦 `get_lender_details` | *"What does PennyMac offer?"* |
| 💚 `get_system_status` | *"Is the system healthy?"* |
| 🧮 `calculate_payment` | *"Monthly payment on a $400K home, 20% down?"* |
| 🖼️ `generate_rate_sheet` | *"Make me a rate card I can text to my buyer"* |
| 🔔 `set_rate_alert` | *"Alert me when 30yr drops below 6%"* |
| 📊 `compare_scenarios` | *"30yr vs 15yr vs ARM — which is better?"* |
| 💰 `estimate_savings` | *"How much would I save switching from Chase to Navy Federal?"* |
| 🎯 `get_recommendation` | *"Best options for a $400K home with 750 credit?"* |

---

## 💬 Example Outputs

Here's what you get when you ask your AI assistant about mortgage rates:

### 🏆 "What's the best 30-year rate?"
```
30-Year Fixed: PennyMac at 5.625% (5.822% APR)
```

### ⚖️ "Compare Wells Fargo, PNC, and PennyMac"
```
PNC:         6.375% (6.425% APR)
Wells Fargo: 6.375% (6.529% APR)
PennyMac:    5.625% (5.822% APR)  ← BEST
```

### 🧮 "What's the monthly payment on a $450K home with 20% down?"
```
Home price:     $450,000
Down payment:   $90,000 (20%)
Loan amount:    $360,000
Rate:           6.375%
Monthly P&I:    $2,245.93
Total interest: $448,535
Total cost:     $808,535
```

### 🎯 "Best options for a $450K home with 740 credit?"
```
#1 PennyMac — VA 30-Year Fixed at 5.375%
   $2,015.90/mo | Lower than national average

#2 Wells Fargo — 15-Year Fixed at 5.500%
   $2,941.50/mo | 0.270% below average, very low fees

#3 PNC — 15-Year Fixed at 5.625%
   $2,965.43/mo | 0.145% below average, tight APR spread
```

### 💰 "How much would I save switching from PNC to PennyMac?"
```
PNC:     6.375% ($2,245.93/mo)
PennyMac: 5.625% ($2,072.36/mo)

Monthly savings:  $173.57
Annual savings:   $2,083
Total savings:    $62,485 over 30 years
```

---

## 🏦 17 Lenders + 2 National Benchmarks

We don't just aggregate — we go directly to each lender's source.

### 📡 Direct API Access (instant, most reliable)
| Lender | How We Get Data |
|--------|----------------|
| 🏛️ Freddie Mac | Weekly PMMS survey (national benchmark) |
| 📰 Mortgage News Daily | Real-time daily index (benchmark) |
| 🏦 Wells Fargo | Hidden internal JSON API |
| 🏦 PNC | MortgageHog Next.js JSON API |
| 🏦 PennyMac | Public REST JSON API |
| 🏦 Citizens Bank | Static JSON rate file |
| 🏦 Flagstar Bank | WalletHub structured data |

### 🌐 Stealth Browser Scraping
| Lender | Protection Level |
|--------|-----------------|
| 🏦 Bank of America | ✅ Easy |
| 🏦 Citi | ✅ Easy |
| 🏦 Navy Federal CU | ✅ Easy |
| 🏦 SoFi | ✅ Easy |
| 🏦 US Bank | ✅ Easy |
| 🏦 Guaranteed Rate | ✅ Easy |
| 🏦 Truist | ✅ Easy |
| 🏦 Mr. Cooper | ✅ Easy |
| 🏦 Chase | ⚡ Akamai (bypassed via AEM endpoint) |
| 🏦 Rocket Mortgage | ⚡ Akamai (bypassed via SSR extraction) |

---

## 🎯 Built for Realtors & Brokers

This isn't a developer toy. It's a tool that puts **real money-saving intelligence** in the hands of mortgage professionals:

- 📱 **Text-ready rate cards** — Generate a PNG rate comparison your client can read on their phone
- 💵 **Real dollar amounts** — "Navy Federal saves your client $141/month compared to Chase"
- 📉 **Trend tracking** — "Rates dropped 0.12% this week across all lenders"
- 🔔 **Rate alerts** — Get notified the moment rates cross your target threshold
- 🤖 **AI-powered recommendations** — "Based on your client's profile, here are the top 3 options and why"

---

## 🔒 Data Accuracy & Trust

Your clients are making the biggest financial decision of their lives. Our data has to be right.

| Check | What It Does |
|-------|-------------|
| ✅ Sanity bounds | Reject any rate outside 2.5%–14.0% |
| ✅ APR validation | APR must be ≥ base rate (catches extraction errors) |
| ✅ Benchmark cross-reference | Flag rates >1.5% from national average |
| ✅ Product consistency | 30yr must be > 15yr for same lender |
| ✅ Staleness detection | Flag unchanged rates after 5+ consecutive scrapes |
| ✅ Screenshot on failure | Capture failed pages for debugging |
| ✅ Last-known-good fallback | Serve stale data with clear timestamp when lender fails |

Every response includes a compliance disclaimer. See [DISCLAIMER.md](DISCLAIMER.md) for TILA/RESPA details.

---

## 🆓 Free & Open

- **Free API access** — no rate limits, no credit card required
- **Open source** — MIT licensed, inspect every line
- **No affiliate links** — we don't sell leads or earn commissions
- **No data selling** — your queries are your business

Get your API key instantly:
```bash
curl -X POST https://your-api-url.com/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "your_password"}'
```

---

## 🏗️ Self-Hosting

Run your own instance:

```bash
git clone https://github.com/seang1121/mortgage-rates-mcp.git
cd mortgage-rates-mcp
pip install -r requirements.txt
python -m patchright install chromium
cp .env.example .env
python scripts/create_database.py
python scripts/create_admin.py
python backend/app.py
```

Runs on port 5001. Scheduler starts automatically — rates scraped at 7am and 7pm EST.

---

## 📊 How We Compare

| Feature | This Server | RateAPI | Bankrate | NerdWallet |
|---------|------------|---------|----------|------------|
| **Lender types** | Banks + online + CU | Credit unions only | Paid listings | Paid listings |
| **Revenue model** | Free / open source | API subscriptions | Affiliate / lead gen | Affiliate / lead gen |
| **AI-native (MCP)** | ✅ 12 tools | ✅ 5 tools | ❌ | ❌ |
| **Rate history** | ✅ 90 days, AM/PM | ❌ | ❌ | ❌ |
| **Rate alerts** | ✅ Discord + email | Pro only ($49/mo) | ❌ | ❌ |
| **Payment calculator** | ✅ Built-in | ❌ | Separate tool | Separate tool |
| **Scenario comparison** | ✅ With breakeven | ❌ | ❌ | ❌ |
| **Rate sheet images** | ✅ Text-ready PNG | ❌ | ❌ | ❌ |
| **AI recommendations** | ✅ Ranked with explanations | ✅ Decisions API | ❌ | ❌ |
| **Data neutrality** | ✅ No pay-to-rank | ✅ | ❌ Paid placement | ❌ Paid placement |

---

## ⚖️ Disclaimer

Rates shown are publicly advertised rates scraped from lender websites and are **not personalized quotes**. Actual rates depend on credit score, loan amount, property type, down payment, and other factors. This is not financial advice. Contact lenders directly for official quotes.

See [DISCLAIMER.md](DISCLAIMER.md) for full legal details.

---

## 📄 License

MIT License — see [LICENSE](LICENSE).

Built by [seang1121](https://github.com/seang1121).
