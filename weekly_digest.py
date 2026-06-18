#!/usr/bin/env python3
"""
weekly_digest.py — Assistiv Systems Weekly Intelligence Digest
Generates a Markdown report card for assistiv.cloud and a JSON summary.
Committed to logs/digest-YYYY-WW.md and logs/digest-latest.json

Data sources (all read from repo or assistivagents):
  - kent-fep-data.json          (live FEP scores)
  - kent-fep-history.json       (12-day score movement)
  - kent-winter-data.json       (WVI + deployment windows)
  - kent-carers-data.json       (carer intensity)
  - kent-secamb-falls-data.json (falls by district)
  - logs/agent-questions.json   (ADA/VERA questions + ratings)
"""

import json, os, requests, datetime, glob, re
from collections import Counter
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────────────
REPO      = "silegrand/assistiv_cloud"
AGENTS_REPO = "silegrand/assistivagents"
RAW       = f"https://raw.githubusercontent.com/{REPO}/main"
RAW_AGENTS = f"https://raw.githubusercontent.com/{AGENTS_REPO}/main"
TODAY     = datetime.date.today()
WEEK_NUM  = TODAY.strftime("%Y-W%V")
WEEK_START = (TODAY - datetime.timedelta(days=TODAY.weekday())).isoformat()
WEEK_END   = (TODAY - datetime.timedelta(days=TODAY.weekday() - 6)).isoformat()

def fetch(url):
    try:
        r = requests.get(url, timeout=15)
        return r.json() if r.ok else None
    except Exception as e:
        print(f"  ✗ fetch failed: {url} — {e}")
        return None

def load_local(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return None

print(f"\n{'='*60}")
print(f"Assistiv Weekly Digest — {WEEK_NUM}")
print(f"{'='*60}\n")

# ── LOAD DATA ─────────────────────────────────────────────────────────
print("Loading data sources...")
fep_data     = fetch(f"{RAW_AGENTS}/kent-fep-data.json")
hist_data    = load_local("kent-fep-history.json") or fetch(f"{RAW}/kent-fep-history.json")
winter_data  = load_local("kent-winter-data.json")  or fetch(f"{RAW}/kent-winter-data.json")
carers_data  = load_local("kent-carers-data.json")   or fetch(f"{RAW}/kent-carers-data.json")
falls_data   = load_local("kent-secamb-falls-data.json") or fetch(f"{RAW}/kent-secamb-falls-data.json")
log_data     = load_local("logs/agent-questions.json") or fetch(f"{RAW}/logs/agent-questions.json")

districts    = fep_data.get("districts", []) if fep_data else []
hist_dists   = hist_data.get("districts", {}) if hist_data else {}
winter_dists = winter_data.get("districts", {}) if winter_data else {}

print(f"  FEP: {len(districts)} districts")
print(f"  History: {len(hist_dists)} districts")
print(f"  Log entries: {len(log_data) if log_data else 0}")

# ── FEP ANALYSIS ──────────────────────────────────────────────────────
print("\nAnalysing FEP scores...")

# Sort districts by FEP descending
sorted_dists = sorted(districts, key=lambda d: d.get("fep", 0), reverse=True)

critical = [d for d in sorted_dists if d.get("risk") == "critical"]
high     = [d for d in sorted_dists if d.get("risk") == "high"]

# Movement
risers  = []
fallers = []
for d in districts:
    h = hist_dists.get(d["name"], {})
    delta = h.get("delta_week", 0)
    if delta >= 3:
        risers.append((d["name"], d["fep"], delta))
    elif delta <= -3:
        fallers.append((d["name"], d["fep"], delta))

risers.sort(key=lambda x: -x[2])
fallers.sort(key=lambda x: x[2])

# Crisis precursors
crisis = [d for d in districts if d.get("crisis_precursor")]
recalibrated = [d for d in districts if d.get("kpho_recalibrated")]

print(f"  Critical: {len(critical)}, High: {len(high)}")
print(f"  Risers: {len(risers)}, Fallers: {len(fallers)}")

# ── PRESCRIBING OUTLIERS ──────────────────────────────────────────────
print("\nAnalysing prescribing...")
rx_outliers = []
RX_LABELS = {
    "antidepressants": "Antidepressants",
    "hypnotics": "Hypnotics",
    "bladder_antimusc": "Bladder antimusc.",
    "parkinsons": "Parkinson's drugs",
    "ace_arb": "ACE/ARBs",
    "bisphosphonates": "Bisphosphonates",
    "anxiolytics": "Anxiolytics",
    "anti_dementia": "Anti-dementia",
}
for d in districts:
    epd = d.get("epd_district", {})
    for key, label in RX_LABELS.items():
        v = epd.get(key, {})
        ratio = v.get("ratio", 0)
        if ratio >= 1.5:
            rx_outliers.append((d["name"], label, ratio))

rx_outliers.sort(key=lambda x: -x[2])
print(f"  Outliers (≥1.5×): {len(rx_outliers)}")

# ── WINTER ANALYSIS ───────────────────────────────────────────────────
print("\nAnalysing winter vulnerability...")
winter_sorted = sorted(
    [(name, d) for name, d in winter_dists.items()],
    key=lambda x: x[1].get("wvi_score", 0),
    reverse=True
)

# Deployment windows coming up (next 8 weeks)
upcoming_deployments = []
month_names = ["January","February","March","April","May","June",
               "July","August","September","October","November","December"]
next_2_months = [
    (TODAY + datetime.timedelta(days=30*i)).strftime("%B %Y")
    for i in range(3)
]
for name, d in winter_sorted[:5]:
    for action, window in d.get("deployment_windows", {}).items():
        if any(m in window for m in next_2_months):
            upcoming_deployments.append((name, action.replace("_", " ").title(), window))

# ── AGENT LOG ANALYSIS ────────────────────────────────────────────────
print("\nAnalysing agent logs...")
entries = log_data if isinstance(log_data, list) else []

# This week's entries
week_entries = [
    e for e in entries
    if e.get("ts", "") >= WEEK_START
]

ada_entries  = [e for e in week_entries if e.get("agent") == "ADA"]
vera_entries = [e for e in week_entries if e.get("agent") == "VERA"]
all_week_ada  = [e for e in entries if e.get("agent") == "ADA"]
all_week_vera = [e for e in entries if e.get("agent") == "VERA"]

# Top questions this week
ada_questions  = Counter(e.get("question","").strip().lower() for e in ada_entries if e.get("question"))
vera_questions = Counter(e.get("question","").strip().lower() for e in vera_entries if e.get("question"))

# Ratings
rated = [e for e in entries if e.get("rating")]
thumbs_up   = [e for e in rated if e.get("rating") == "up"]
thumbs_down = [e for e in rated if e.get("rating") == "down"]
week_rated  = [e for e in week_entries if e.get("rating")]
week_up     = [e for e in week_rated if e.get("rating") == "up"]
week_down   = [e for e in week_rated if e.get("rating") == "down"]

# Pages with most questions this week
page_counts = Counter(e.get("page","") for e in week_entries)

# Poor responses (thumbs down this week)
poor_responses = [e for e in week_entries if e.get("rating") == "down"]

print(f"  This week: {len(week_entries)} questions ({len(ada_entries)} ADA, {len(vera_entries)} VERA)")
print(f"  Ratings this week: {len(week_up)} 👍  {len(week_down)} 👎")
print(f"  All-time total: {len(entries)}")

# ── FALLS ANALYSIS ────────────────────────────────────────────────────
falls_dists = falls_data.get("districts", {}) if falls_data else {}
top_falls = sorted(
    [(name, d.get("rate_per_1000_pop75", 0)) for name, d in falls_dists.items()],
    key=lambda x: -x[1]
)[:3]

# ── DATA FRESHNESS ────────────────────────────────────────────────────
fep_generated = (fep_data or {}).get("meta", {}).get("generated", "Unknown")[:10]
hist_generated = (hist_data or {}).get("meta", {}).get("generated", "Unknown")

# ── BUILD MARKDOWN ────────────────────────────────────────────────────
print("\nBuilding digest markdown...")

total_pop75 = sum(d.get("pop75", 0) for d in districts)

lines = []
lines.append(f"# Assistiv Intelligence — Weekly Report Card")
lines.append(f"**{WEEK_NUM}** · Week ending {WEEK_END} · assistiv.cloud")
lines.append("")
lines.append("> Auto-generated by Assistiv Systems weekly pipeline. A population-level triage instrument — not a clinical document.")
lines.append("")

# ── SECTION 1: ALERTS ──────────────────────────────────────────────────
lines.append("---")
lines.append("")
lines.append("## ⚠ Alerts & Priority Signals")
lines.append("")

if crisis:
    for d in crisis:
        h = hist_dists.get(d["name"], {})
        delta = h.get("delta_week", 0)
        lines.append(f"🔴 **CRISIS PRECURSOR: {d['name']}** — FEP {d['fep']} ({d['risk']} risk), "
                     f"{'↑ +' + str(delta) + ' this week' if delta > 0 else 'stable'}")
elif critical:
    for d in critical:
        lines.append(f"🟠 **{d['name']}** remains in the critical band — FEP {d['fep']}")
else:
    lines.append("✅ No crisis precursors flagged this week.")

lines.append("")
if risers:
    lines.append("**Rising risk this week:**")
    for name, fep, delta in risers:
        lines.append(f"- {name}: FEP {fep} (↑ +{delta} pts)")
    lines.append("")
if fallers:
    lines.append("**Falling risk this week** *(may reflect data recalibration)*:")
    for name, fep, delta in fallers:
        lines.append(f"- {name}: FEP {fep} (↓ {delta} pts)")
    lines.append("")

# ── SECTION 2: FEP LEAGUE TABLE ────────────────────────────────────────
lines.append("---")
lines.append("")
lines.append("## 📊 FEP District Scores — Full League Table")
lines.append("")
lines.append(f"Kent & Medway population 75+: **{total_pop75:,}** · England average FEP = 50")
lines.append("")
lines.append("| Rank | District | FEP | Risk | Δ Week | Trend |")
lines.append("|------|----------|-----|------|--------|-------|")

for i, d in enumerate(sorted_dists, 1):
    h = hist_dists.get(d["name"], {})
    delta = h.get("delta_week", 0)
    trend = h.get("trend", "stable")
    delta_str = f"+{delta}" if delta > 0 else str(delta) if delta != 0 else "—"
    trend_icon = "↑" if trend == "rising" else "↓" if trend == "falling" else "→"
    risk_icon = "🔴" if d["risk"] == "critical" else "🟠" if d["risk"] == "high" else "🔵" if d["risk"] == "moderate" else "🟢"
    lines.append(f"| {i} | {d['name']} | **{d['fep']}** | {risk_icon} {d['risk']} | {delta_str} | {trend_icon} |")

lines.append("")

# ── SECTION 3: WINTER ──────────────────────────────────────────────────
lines.append("---")
lines.append("")
lines.append("## ❄ Winter Vulnerability")
lines.append("")
lines.append("**Top 5 districts by Winter Vulnerability Index (WVI):**")
lines.append("")
lines.append("| District | WVI | Tier | Historical peak |")
lines.append("|----------|-----|------|-----------------|")

for name, d in winter_sorted[:5]:
    wvi = round(d.get("wvi_score", 0))
    tier = d.get("wvi_tier", "—")
    peak_month = d.get("historical_peak_month", "—")
    peak_uplift = d.get("historical_peak_uplift_pct", "—")
    lines.append(f"| {name} | {wvi} | {tier} | {peak_month} (+{peak_uplift}%) |")

lines.append("")

if upcoming_deployments:
    lines.append("**Deployment windows opening in the next 8 weeks:**")
    lines.append("")
    for district, action, window in upcoming_deployments[:6]:
        lines.append(f"- **{district}** — {action}: *{window}*")
    lines.append("")

# ── SECTION 4: PRESCRIBING ─────────────────────────────────────────────
lines.append("---")
lines.append("")
lines.append("## 💊 Prescribing Outliers")
lines.append("")
lines.append("Signals ≥1.5× England average — highest concern level:")
lines.append("")
lines.append("| District | Signal | Ratio |")
lines.append("|----------|--------|-------|")

for name, label, ratio in rx_outliers[:8]:
    lines.append(f"| {name} | {label} | {ratio:.2f}× ▲▲ |")

if not rx_outliers:
    lines.append("| — | No signals ≥1.5× this week | — |")

lines.append("")

# ── SECTION 5: CARERS ──────────────────────────────────────────────────
lines.append("---")
lines.append("")
lines.append("## 👥 Carers Intensity — Heavy Care Band (50+ hrs/week)")
lines.append("")
carers_list = []
if carers_data:
    raw_list = carers_data.get("districts", carers_data)
    if isinstance(raw_list, list):
        carers_list = raw_list
    elif isinstance(raw_list, dict):
        carers_list = list(raw_list.values())

if carers_list:
    top_carers = sorted(
        [c for c in carers_list if isinstance(c, dict) and c.get("heavy_care_rate_per_1000")],
        key=lambda c: c.get("heavy_care_rate_per_1000", 0),
        reverse=True
    )[:5]
    lines.append("| District | Heavy carers | Rate/1,000 | Rank |")
    lines.append("|----------|-------------|------------|------|")
    for c in top_carers:
        rank = f"#{c.get('heavy_care_rank','—')}"
        lines.append(f"| {c['name']} | {c.get('carers_high_50plus',0):,} | {c.get('heavy_care_rate_per_1000','—')} | {rank} |")
    lines.append("")

# ── SECTION 6: FALLS ───────────────────────────────────────────────────
lines.append("---")
lines.append("")
lines.append("## 🚑 Falls — Top Districts by Rate")
lines.append("")
if top_falls:
    lines.append("| District | Rate per 1,000 pop 75+ |")
    lines.append("|----------|------------------------|")
    for name, rate in top_falls:
        lines.append(f"| {name} | {rate} |")
    lines.append("")

# ── SECTION 7: AGENT QUESTIONS ─────────────────────────────────────────
lines.append("---")
lines.append("")
lines.append("## 🤖 Agent Intelligence — ADA & VERA")
lines.append("")
lines.append(f"**This week:** {len(week_entries)} questions — "
             f"{len(ada_entries)} to ADA, {len(vera_entries)} to VERA")
lines.append("")
lines.append(f"**Ratings this week:** {len(week_up)} 👍 helpful · "
             f"{len(week_down)} 👎 not helpful")
if week_rated:
    satisfaction = round(len(week_up) / len(week_rated) * 100) if week_rated else 0
    lines.append(f"**Satisfaction rate:** {satisfaction}%")
lines.append("")

lines.append(f"**All-time totals:** {len(entries)} questions · "
             f"{len(thumbs_up)} 👍 · {len(thumbs_down)} 👎")
lines.append("")

if ada_questions:
    lines.append("**Top ADA questions this week:**")
    for q, c in ada_questions.most_common(5):
        q_display = q[:120] + "…" if len(q) > 120 else q
        lines.append(f"- ({c}×) {q_display.capitalize()}")
    lines.append("")

if vera_questions:
    lines.append("**Top VERA challenges this week:**")
    for q, c in vera_questions.most_common(5):
        q_display = q[:120] + "…" if len(q) > 120 else q
        lines.append(f"- ({c}×) {q_display.capitalize()}")
    lines.append("")

if page_counts:
    lines.append("**Most active pages this week:**")
    for page, count in page_counts.most_common(5):
        lines.append(f"- `{page}` — {count} questions")
    lines.append("")

if poor_responses:
    lines.append("**👎 Responses flagged for review this week:**")
    lines.append("")
    for e in poor_responses[:5]:
        q = (e.get("question","") or "")[:100]
        r = (e.get("response","") or "")[:150]
        agent = e.get("agent","?")
        lines.append(f"> **{agent}** was asked: *\"{q}\"*")
        if r:
            lines.append(f"> Response summary: *\"{r}…\"*")
        lines.append("> *(flagged as not helpful — review system prompt)*")
        lines.append("")

# ── SECTION 8: DATA FRESHNESS ──────────────────────────────────────────
lines.append("---")
lines.append("")
lines.append("## 📡 Data Freshness")
lines.append("")
lines.append("| Dataset | Last updated | Source |")
lines.append("|---------|-------------|--------|")
lines.append(f"| FEP scores | {fep_generated} | NHS Fingertips / KPHO daily pipeline |")
lines.append(f"| FEP history | {hist_generated or '—'} | Assistiv daily snapshots |")
lines.append(f"| Winter WVI | Seasonal model 2026–27 | Assistiv winter pipeline |")
lines.append(f"| Prescribing | Mar 2026 | NHSBSA EPD |")
lines.append(f"| Carers | 2021 | ONS Census 2021 via KPHO HSCM V1.6 |")
lines.append(f"| Falls | FOI period | SECAmb FOI |")
lines.append(f"| Agent logs | Live | Assistiv Worker / GitHub |")
lines.append("")

# ── FOOTER ─────────────────────────────────────────────────────────────
lines.append("---")
lines.append("")
lines.append(f"*Generated automatically {TODAY.isoformat()} by Assistiv Systems weekly pipeline. "
             f"All data OGL v3 (NHS/ONS sources) except SECAmb FOI. "
             f"Population triage instrument only — not a clinical document. "
             f"Assistiv Systems Limited, Company No. 17082597, Faversham, Kent.*")
lines.append("")
lines.append(f"[View live platform](https://www.assistiv.cloud) · "
             f"[Commissioner Briefing](https://www.assistiv.cloud/briefing/) · "
             f"[Agent Logs](https://www.assistiv.cloud/logs/)")

digest_md = "\n".join(lines)

# ── SAVE MARKDOWN ──────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
md_path = f"logs/digest-{WEEK_NUM}.md"
with open(md_path, "w") as f:
    f.write(digest_md)
print(f"\n✓ Digest saved: {md_path} ({len(digest_md):,} chars)")

# ── SAVE JSON SUMMARY ──────────────────────────────────────────────────
summary = {
    "week":        WEEK_NUM,
    "generated":   TODAY.isoformat(),
    "fep": {
        "critical_count": len(critical),
        "high_count":     len(high),
        "top_district":   sorted_dists[0]["name"] if sorted_dists else "—",
        "top_fep":        sorted_dists[0]["fep"]  if sorted_dists else 0,
        "risers":         [{"name": n, "fep": f, "delta": d} for n, f, d in risers],
        "fallers":        [{"name": n, "fep": f, "delta": d} for n, f, d in fallers],
        "crisis_precursors": [d["name"] for d in crisis],
        "all_districts":  [{"name": d["name"], "fep": d["fep"], "risk": d["risk"],
                             "delta_week": hist_dists.get(d["name"], {}).get("delta_week", 0)}
                           for d in sorted_dists],
    },
    "agents": {
        "week_total":    len(week_entries),
        "week_ada":      len(ada_entries),
        "week_vera":     len(vera_entries),
        "week_up":       len(week_up),
        "week_down":     len(week_down),
        "all_time":      len(entries),
        "top_ada":       [{"q": q, "count": c} for q, c in ada_questions.most_common(5)],
        "top_vera":      [{"q": q, "count": c} for q, c in vera_questions.most_common(5)],
        "flagged":       len(poor_responses),
    },
    "winter": {
        "top_5": [{"name": n, "wvi": round(d.get("wvi_score",0)), "tier": d.get("wvi_tier","—")}
                  for n, d in winter_sorted[:5]],
        "upcoming_deployments": [{"district": d, "action": a, "window": w}
                                  for d, a, w in upcoming_deployments[:6]],
    },
    "prescribing": {
        "outliers_150pct_plus": [{"district": n, "signal": s, "ratio": round(r, 2)}
                                  for n, s, r in rx_outliers[:8]],
    },
    "markdown_path": md_path,
}

with open("logs/digest-latest.json", "w") as f:
    json.dump(summary, f, indent=2)
print("✓ Summary saved: logs/digest-latest.json")

print(f"\n{'='*60}")
print(f"Digest complete — {WEEK_NUM}")
print(f"  Critical districts: {len(critical)}")
print(f"  Crisis precursors:  {len(crisis)}")
print(f"  Agent questions this week: {len(week_entries)}")
print(f"  Satisfaction: {len(week_up)}/{len(week_rated)} rated helpful")
print(f"{'='*60}\n")
