# Assistiv Cloud — Population Frailty Intelligence

**Live platform → [assistiv.cloud](https://www.assistiv.cloud)**

Population-level frailty intelligence for NHS commissioners, PCN leads and community outreach teams across Kent & Medway. Identifies the *Missing Middle* — approximately 3.5 million people nationally living at home with emerging frailty, invisible to existing care pathways, and heading toward preventable crisis.

Built on open NHS data. No patient identifiers. No login required. Updated daily.

---

## What this repository is

This is the unified repository for `assistiv.cloud` — both the GitHub Pages deployment (static HTML tools) and the daily data pipeline (Python scripts, JSON outputs, history archive).

```
assistiv_cloud/
├── *.html                      ← Live tools, served directly by GitHub Pages
├── *-data.json                 ← JSON data feeds, updated by pipeline scripts
├── daily_refresh.py            ← Daily GitHub Actions pipeline (Fingertips + EPD)
├── inject_stats.py             ← Static fallback injection for crawlers / SEO
├── fetch_*.py                  ← Monthly data fetchers (corridor, HES, SHMI, GP, 111)
├── history/                    ← Daily FEP snapshot archive
└── backtest/                   ← Frozen predictions and scored outcomes
```

---

## The intelligence layer

### Frailty Emergence Probability (FEP)

A 22-signal composite score (0–100) for each of the 13 Kent & Medway districts. Updated daily via GitHub Actions. Signals span:

- **NHS Fingertips outcomes** — falls admissions, hip fractures, winter mortality, loneliness, dementia diagnosis, social isolation (district-level where published, ICB-level fallback)
- **NHSBSA EPD prescribing** — 11 signals including hypnotics, antidepressants, bisphosphonates, anti-dementia drugs, anxiolytics
- **Synthetic demographic proxies** — over-75s living alone (Census 2021), IMD deprivation (MHCLG 2025), care home gap
- **KPHO clinical recalibration** — GP-recorded Clinical Frailty Scale scores blended at 40% to correct model divergences (notably Dartford +30 pts, Maidstone −16 pts vs proxy-only FEP)
- **SECAmb FOI signal** — 10,720 ambulance falls callouts (65+, 2025) at 7% weight

FEP methodology v5.2. Full documentation at [assistiv.cloud/methodology](https://www.assistiv.cloud/methodology/).

---

## Tools

All tools are standalone HTML files, deployable with zero build step.

### Find — geographic intelligence

| Tool | Path | Data sources |
|---|---|---|
| **Frailty Heat Map** | `/frailty-heat-map/` | FEP scores, ONS boundaries, discharge sitrep, 111 demand, economic model |
| **FEP Configurator** | `/frailty-emergence-probability-calculator/` | 21 adjustable signal weights, Ada AI explainer |
| **Kent Falls Hotspot Map** | `/kent-falls-map/` | SECAmb FOI 2025, NHS Fingertips hip fractures |
| **Rural Access Vulnerability (RAVI)** | `/rural-access-vulnerability/` | IMD geographic barriers, ONS rural classification, Census 2021, Ofcom broadband |
| **NHS Pressure Intelligence Map** | `/nhs-pressure-map/` | Corridor care sitrep, HES, SHMI, GP registration |
| **Winter Readiness Intelligence** | `/winter-readiness/` | Winter Vulnerability Index (5 components), NICE intervention windows |

### Understand — who holds them up

| Tool | Path | Data sources |
|---|---|---|
| **Carers Intensity Map** | `/kent-carers-map/` | Census 2021 TS039 — unpaid care hours by district |
| **FEP × Carer Burden Quadrant** | `/cbi-fep-map/` | CBI (5 signals) × FEP dual-axis intelligence |

### Reach — outreach and action

| Tool | Path | Data sources |
|---|---|---|
| **Reachable Neighbourhoods** | `/reachable-neighbourhoods/` | 17 named neighbourhoods ranked by deprivation, solo living, prescribing velocity |
| **Community Outreach Map** | `/community-touchpoints/` | 195 Kent venues (11 types), AI-generated outreach ideas via Anthropic API |
| **Voice-First Frailty Screen** | [assistiv.tools](https://www.assistiv.tools) | PRISMA-7, FRAIL Scale — external domain |

### Intelligence briefings

| Tool | Path | Notes |
|---|---|---|
| **Commissioner Briefing** | `/briefing/` | Live daily read, monthly movement, recalibration flags |
| **FEP Trend History** | `/history/` | Date-comparison tool across full daily archive |
| **Backtest Monitor** | `/backtest-monitor/` | Validation tracking — pending post-June Fingertips outcomes |
| **Methodology** | `/methodology/` | Full signal documentation, weights, sources, honest caveats |

---

## Data architecture

All JSON data files live in this repository. The daily pipeline reads from and writes to the same repo.

```
silegrand/assistiv_cloud
├── kent-fep-data.json               ← FEP scores — written daily by pipeline
├── kent-fep-history.json            ← Delta summary
├── kent-hscm-data.json              ← KPHO clinical frailty recalibration
├── kent-ravi-data.json              ← RAVI LSOA scores
├── kent-winter-data.json            ← Winter Vulnerability Index
├── kent-corridor-data.json          ← NHS corridor care (sitrep)
├── kent-hes-data.json               ← HES emergency admissions
├── kent-shmi-data.json              ← SHMI mortality ratios
├── kent-gp-reg-data.json            ← GP registration 75+ population
├── kent-111-data.json               ← NHS 111 demand
├── kent-discharge-data.json         ← Discharge delay sitrep
├── kent-cbi-data.json               ← Carer Burden Index signals
├── kent-carers-data.json            ← Census unpaid carer hours
├── kent-secamb-falls-data.json      ← SECAmb FOI callout data
├── kent-districts.geojson           ← District boundaries (static)
├── community-touchpoints-data.json  ← 195 community venues, 13 districts
├── history/
│   └── kent-fep-YYYY-MM-DD.json     ← Daily FEP snapshot archive
└── backtest/
    ├── ledger.json                  ← Frozen predictions
    └── scorecard-latest.json        ← Most recent scored outcome
```

**Single source of truth for all data:** this repository. All tools fetch JSON directly from `raw.githubusercontent.com/silegrand/assistiv_cloud/main/`.

---

## Daily pipeline

The GitHub Actions workflow (`.github/workflows/`) runs at 06:00 UTC daily:

1. `daily_refresh.py` — fetches latest NHS Fingertips indicators at LAD and ICB level, recalculates district FEP scores using last committed EPD data, commits `kent-fep-data.json` and a dated history snapshot
2. `inject_stats.py` — bakes current live values into `index.html` and `nhs-pressure-map.html` as static fallback text for search engines and AI crawlers

EPD prescribing data (18m+ rows) is **not** re-fetched daily — it is updated manually when NHSBSA publish a new monthly release. See `MONTHLY_MAINTENANCE.md` for the manual update checklist.

---

## Data sources and licensing

All data is open and published under the Open Government Licence v3.0 (OGL v3) unless noted.

| Source | Data | Licence |
|---|---|---|
| NHS Fingertips / OHID PHOF | Outcomes indicators (falls, hip fractures, loneliness, dementia, winter mortality, social isolation) | OGL v3 |
| NHSBSA EPD | Monthly prescribing (18m+ rows) | OGL v3 |
| ONS Census 2021 | Over-75s living alone, unpaid carer hours, rural classification | OGL v3 |
| MHCLG IMD 2025 | Deprivation index, geographic barriers sub-domain | OGL v3 |
| NHS England Discharge Sitrep | Corridor care, delayed discharge | OGL v3 |
| NHS England HES | Emergency admissions 65+ | OGL v3 |
| NHS Digital SHMI | Standardised mortality ratios | OGL v3 |
| NHS Digital GP Registration | Practice-level population 75+ | OGL v3 |
| KPHO Health and Social Care Maps | GP-recorded Clinical Frailty Scale (quarterly) | Shared with permission |
| SECAmb FOI response | 10,720 ambulance falls callouts 65+ (2025) | FOI disclosure |
| Ofcom Connected Nations | Broadband coverage at premises level | OGL v3 |
| DWP Stat Xplore | Prepayment meter data, fuel poverty proxy | OGL v3 |

**No patient identifiers are used or derived at any stage.** All outputs are aggregated to district (LAD) or LSOA level. This platform is not a medical device.

---

## Cloudflare Worker proxy

AI agents (Ada, VERA) and the Community Outreach Map use a Cloudflare Worker (`assistiv-proxy`) to proxy Anthropic API calls server-side. The API key never reaches the browser. Allowed origins are explicitly allowlisted.

Worker endpoint: `assistiv-proxy.simongeorgelegrand.workers.dev`

---

## Governance

Full governance and data assurance documentation: [assistiv.co/governance.html](https://www.assistiv.co/governance.html)

Key positions:
- Population intelligence only — outputs end in a question for a clinician, never a diagnosis
- No patient identifiers at any stage of the pipeline
- All data sources are open, approved and cited in-tool
- FEP scores are modelled, not clinically validated — stated explicitly on every relevant page
- June 2026 recalibration event (Thanet 61→77, Maidstone 60→37, Swale →31) was a model update, not a real-world change — flagged in the briefing and history tools

---

## Advisory board

- **Professor Ann Netten** — ASCOT creator, University of Kent. Confirmed methodological originality.
- **Professor John Jerrim** — Quantitative social statistics, UCL.
- **Professor Tim Legrand** — Government policy, University of Adelaide.
- **Mark Greenfield** — Nursing and ageing, retired lecturer.

---

## Related repositories

| Repo | Purpose |
|---|---|
| [`silegrand/assistiv_co`](https://github.com/silegrand/assistiv_co) | assistiv.co — parent brand, governance, investor pages |
| [`silegrand/assistiv_tools`](https://github.com/silegrand/assistiv_tools) | assistiv.tools — community frailty screening (PRISMA-7, FRAIL Scale) |
| [`silegrand/assistiv_services`](https://github.com/silegrand/assistiv_services) | assistiv.services — preventative care platform |

---

## Intellectual property

Proprietary sensing technology underpins the Model B sensor platform, which is distinct from this population intelligence layer. Details available under NDA to serious partners and investors.

© 2026 Assistiv Systems Limited. Registered in England and Wales. Company number 17082597.

Population intelligence data and tooling released under OGL v3 where derived from OGL sources. Platform code and methodology: all rights reserved.
