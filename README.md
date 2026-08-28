# Smart Portfolio — المحفظة الذكية

> **"حلّل أكثر... قرّر بنفسك."**

AI-Powered Personal Investment Management Platform

---

## Overview

Smart Portfolio is a personal investment assistant that helps long-term investors:

- Manage their portfolio with a multi-installment strategy
- Analyze companies (Financial · Technical · Sharia · Expert Ratings)
- Monitor the market and important corporate events
- Track goals and performance
- Get AI-powered insights — while **always** keeping the final decision with the investor

**Smart Portfolio never executes trades. It only provides decision support.**

---

## Architecture

```
Frontend (React + TypeScript)
        ↓
Backend (Python + FastAPI)
        ↓
  Business Logic  ←→  AI Agents (Gemini)
        ↓
  PostgreSQL DB
        ↓
External Services (Yahoo Finance · Sahmak · Telegram)
```

---

## Tech Stack

| Layer       | Technology                     |
|-------------|-------------------------------|
| Frontend    | React 18, TypeScript, Tailwind |
| Backend     | Python 3.12, FastAPI           |
| Database    | PostgreSQL 16                  |
| ORM         | SQLAlchemy (async)             |
| AI          | Gemini (configurable)          |
| Market Data | Yahoo Finance + Sahmak         |
| Notifications | Telegram Bot               |
| Deployment  | Docker + Nginx on AWS EC2      |

**Official typeface:** Thmanyah Serif Display — the site's only Arabic/base font, embedded
locally as `@font-face` in `frontend/src/assets/fonts/` (not a CDN/Google Fonts
dependency). Declared in `frontend/src/styles/globals.css` (`body` rule) and
`frontend/tailwind.config.js` (`fontFamily.sans` / `fontFamily.arabic`) — every
element in the app inherits it from there. Do not introduce another typeface
as a default; if a new component sets its own `font-family`, it must reference
`'Thmanyah Serif Display'`, not Cairo/Tajawal/Inter or a system stack.

---

## Quick Start

### 1. Clone & Configure

```bash
git clone <repo>
cd smart-portfolio
cp .env.example .env
# Edit .env — fill in your API keys
```

### 2. Launch with Docker

```bash
docker-compose up -d
```

### 3. Access

- **App:**   http://localhost
- **API:**   http://localhost/api/v1
- **Docs:**  http://localhost/api/docs

---

## Project Structure

```
smart-portfolio/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/     # All REST endpoints
│   │   ├── agents/               # AI Agents (Finance, Technical, Market, ...)
│   │   ├── engine/
│   │   │   ├── calculation/      # Single Source of Truth for all math
│   │   │   └── evaluation/       # Multi-agent result consolidation
│   │   ├── models/               # SQLAlchemy models
│   │   ├── services/             # Business logic
│   │   └── scheduler/            # Background jobs
│   └── main.py
├── frontend/
│   └── src/
│       ├── pages/                # Dashboard, Portfolio, Market, AI, ...
│       ├── components/           # Reusable UI components
│       └── services/api.ts       # Typed API client
├── config/
│   ├── ai/models.json
│   ├── api/providers.json
│   └── portfolio/strategy.json
├── scripts/
│   ├── backup.py
│   └── update_market.py
└── docker-compose.yml
```

---

## AI Agents

| Agent | Responsibility |
|-------|----------------|
| Finance Agent | Financial quality: earnings, cash flow, debt, sustainability |
| Technical Agent | Price trend, support/resistance, entry zones |
| Market Agent | News, events, financial results, corporate actions |
| Portfolio Agent | Diversification, weights, income, goal progress |
| Risk Agent | Concentration, sector, debt, earnings risk |
| Cash Agent | Liquidity, deferred cash, reinvestment readiness |
| Goal Agent | Capital & income target tracking |
| Installment Agent | Price proximity alerts for installment execution |
| Alternative Agent | Alternative companies when quality drops |
| Notification Agent | Smart event filtering and dispatching |
| Reporting Agent | Structured report assembly |

**AI Coordinator** orchestrates all agents in parallel.  
**Evaluation Engine** consolidates results, detects conflicts, and produces a unified evaluation.

---

## Golden Rule

```
المستثمر هو صاحب القرار النهائي دائمًا.
The investor always holds the final decision.
```

The system never:
- Executes buy orders
- Executes sell orders
- Modifies portfolio weights automatically
- Makes binding recommendations

---

## API Endpoints

Base: `/api/v1/`

| Prefix | Description |
|--------|-------------|
| `/portfolio` | Portfolio summary, ROI, income, health |
| `/companies` | CRUD for portfolio companies |
| `/holdings` | Current positions and metrics |
| `/transactions` | All financial operations |
| `/installments` | Installment plan management |
| `/cash` | Cash and liquidity management |
| `/dividends` | Dividend records and reinvestment |
| `/bonus` | Bonus share records |
| `/goals` | Investment goals tracking |
| `/market` | News, events, financial results |
| `/ai` | AI analysis, evaluation, opportunities |
| `/notifications` | Alert management |
| `/reports` | Report generation and archive |
| `/settings` | All system configuration |
| `/backups` | Backup and restore |
| `/health` | System health check |

Interactive docs: `http://localhost/api/docs`

---

## Environment Variables

See `.env.example` for all configuration options.  
Key variables:

```env
AI_PROVIDER=gemini
AI_API_KEY=your_key
TELEGRAM_BOT_TOKEN=your_token
PRIMARY_MARKET_PROVIDER=yahoo_finance
```

---

## Deployment (AWS EC2)

```bash
# On Ubuntu server
sudo apt update && sudo apt install -y docker.io docker-compose
git clone <repo> smart-portfolio
cd smart-portfolio
cp .env.example .env && nano .env
docker-compose up -d
```

---

## Backup

```bash
# Create backup
python scripts/backup.py

# Restore
python scripts/backup.py restore backups/manual/sp_full_20260101_120000.tar.gz
```

---

## Version

**1.0.0** — Initial Release 2026

---

*Smart Portfolio — حلّل أكثر... قرّر بنفسك.*
