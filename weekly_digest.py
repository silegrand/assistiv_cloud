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
try:
    import resend
    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False
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

# ── BUILD + SEND EMAIL ────────────────────────────────────────────────
def build_email_html(summary, digest_md):
    """Build a clean HTML email from the digest summary."""
    fep = summary.get("fep", {})
    agents = summary.get("agents", {})
    winter = summary.get("winter", {})
    rx = summary.get("prescribing", {})
    all_dists = fep.get("all_districts", [])
    week = summary.get("week", "")
    generated = summary.get("generated", "")

    critical_count = fep.get("critical_count", 0)
    high_count     = fep.get("high_count", 0)
    crisis         = fep.get("crisis_precursors", [])
    risers         = fep.get("risers", [])
    fallers        = fep.get("fallers", [])
    top_district   = fep.get("top_district", "—")
    top_fep        = fep.get("top_fep", 0)

    week_q     = agents.get("week_total", 0)
    week_ada   = agents.get("week_ada", 0)
    week_vera  = agents.get("week_vera", 0)
    week_up    = agents.get("week_up", 0)
    week_down  = agents.get("week_down", 0)
    flagged    = agents.get("flagged", 0)
    top_ada    = agents.get("top_ada", [])
    top_vera   = agents.get("top_vera", [])
    sat_pct    = round(week_up / (week_up + week_down) * 100) if (week_up + week_down) > 0 else None

    winter_top5  = winter.get("top_5", [])
    upcoming_dep = winter.get("upcoming_deployments", [])
    rx_outliers  = rx.get("outliers_150pct_plus", [])

    # Colours
    def fep_color(fep):
        if fep >= 70: return "#c04828"
        if fep >= 55: return "#8a6200"
        if fep >= 40: return "#1e40af"
        return "#166534"

    def risk_bg(risk):
        m = {"critical":("#fee2e2","#c04828"), "high":("#fef3c7","#92400e"),
             "moderate":("#dbeafe","#1e40af"), "low":("#dcfce7","#166534")}
        return m.get(risk, ("#f0f0f0","#333"))

    # Alert block
    if crisis:
        alert_html = "".join(
            f'<div style="background:#fee2e2;border-left:4px solid #c04828;padding:10px 14px;margin-bottom:8px;border-radius:0 4px 4px 0">'
            f'<strong style="color:#c04828">🔴 Crisis Precursor: {n}</strong> — FEP {next((d["fep"] for d in all_dists if d["name"]==n), "?")} — rising and in critical band</div>'
            for n in crisis
        )
    elif critical_count > 0:
        names = ", ".join(d["name"] for d in all_dists if d["risk"] == "critical")
        alert_html = f'<div style="background:#fff5f5;border-left:4px solid #c04828;padding:10px 14px;border-radius:0 4px 4px 0"><strong style="color:#c04828">Critical band:</strong> {names}</div>'
    else:
        alert_html = '<div style="background:#f0fdf4;border-left:4px solid #166534;padding:10px 14px;border-radius:0 4px 4px 0;color:#166534">✅ No crisis precursors flagged this week.</div>'

    # FEP table rows (top 6 by risk, rest collapsed)
    fep_rows = ""
    for i, d in enumerate(all_dists):
        bg, tc = risk_bg(d["risk"])
        delta = d.get("delta_week", 0)
        delta_str = f"+{delta}" if delta > 0 else ("—" if delta == 0 else str(delta))
        delta_color = "#c04828" if delta > 2 else "#166534" if delta < -2 else "#666"
        fep_rows += (
            f'<tr style="border-bottom:1px solid #e8e0d4">' 
            f'<td style="padding:6px 8px;font-size:12px;color:#666">{i+1}</td>'
            f'<td style="padding:6px 8px;font-size:13px;font-weight:500">{d["name"]}</td>'
            f'<td style="padding:6px 8px;font-size:14px;font-weight:700;color:{fep_color(d["fep"])}">{d["fep"]}</td>'
            f'<td style="padding:6px 8px"><span style="background:{bg};color:{tc};font-size:10px;font-weight:700;padding:2px 6px;border-radius:3px;text-transform:uppercase">{d["risk"]}</span></td>'
            f'<td style="padding:6px 8px;font-size:12px;font-weight:600;color:{delta_color}">{delta_str}</td>'
            f'</tr>'
        )

    # Winter rows
    winter_rows = ""
    for w in winter_top5[:5]:
        wvi = w.get("wvi", 0)
        wvi_c = "#c04828" if wvi >= 70 else "#8a6200" if wvi >= 55 else "#166534"
        winter_rows += (
            f'<tr style="border-bottom:1px solid #e8e0d4">'
            f'<td style="padding:6px 8px;font-size:13px;font-weight:500">{w["name"]}</td>'
            f'<td style="padding:6px 8px;font-size:14px;font-weight:700;color:{wvi_c}">{wvi}</td>'
            f'<td style="padding:6px 8px;font-size:11px;color:#666">{w.get("tier","—")}</td>'
            f'</tr>'
        )

    # Rx outlier rows
    rx_rows = "".join(
        f'<tr style="border-bottom:1px solid #e8e0d4">'
        f'<td style="padding:6px 8px;font-size:13px;font-weight:500">{o["district"]}</td>'
        f'<td style="padding:6px 8px;font-size:12px;color:#666">{o["signal"]}</td>'
        f'<td style="padding:6px 8px;font-size:13px;font-weight:700;color:#c04828">{o["ratio"]}× ▲▲</td>'
        f'</tr>'
        for o in rx_outliers[:6]
    ) or '<tr><td colspan="3" style="padding:8px;font-size:12px;color:#888">No signals ≥1.5× this week.</td></tr>'

    # Top ADA questions
    ada_qs = "".join(
        f'<li style="margin-bottom:5px;font-size:13px">'
        f'<span style="font-weight:600;color:#1a3a2a">({q["count"]}×)</span> {q["q"].capitalize()[:100]}</li>'
        for q in top_ada[:5]
    ) or '<li style="color:#888;font-size:13px">No questions this week.</li>'

    vera_qs = "".join(
        f'<li style="margin-bottom:5px;font-size:13px">'
        f'<span style="font-weight:600;color:#4c1d95">({q["count"]}×)</span> {q["q"].capitalize()[:100]}</li>'
        for q in top_vera[:4]
    ) or '<li style="color:#888;font-size:13px">No challenges this week.</li>'

    flagged_block = ""
    if flagged > 0:
        flagged_block = f'''
        <div style="background:#fff5f5;border:1px solid #fecaca;border-radius:6px;padding:12px 16px;margin-bottom:16px">
          <div style="font-weight:700;color:#c04828;margin-bottom:6px">👎 {flagged} response{"s" if flagged>1 else ""} flagged as unhelpful this week</div>
          <div style="font-size:12px;color:#666">Review the agent system prompts at 
            <a href="https://www.assistiv.cloud/logs/" style="color:#2d6b47">assistiv.cloud/logs</a>
          </div>
        </div>'''

    sat_block = ""
    if sat_pct is not None:
        sat_color = "#166534" if sat_pct >= 80 else "#8a6200" if sat_pct >= 60 else "#c04828"
        sat_block = f'<span style="color:{sat_color};font-weight:700">{sat_pct}% satisfaction</span> · '

    upcoming_block = ""
    if upcoming_dep:
        items = "".join(
            f'<li style="margin-bottom:4px;font-size:13px"><strong>{d["district"]}</strong> — {d["action"].replace("_"," ").title()}: <span style="color:#8a6200">{d["window"]}</span></li>'
            for d in upcoming_dep[:4]
        )
        upcoming_block = f'<div style="margin-top:12px"><div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:#5a6b62;margin-bottom:6px">Deployment windows opening soon</div><ul style="margin:0;padding-left:16px">{items}</ul></div>'

    html = f"""<!DOCTYPE html>
<html lang="en-GB">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Assistiv Weekly Report Card — {week}</title></head>
<body style="margin:0;padding:0;background:#f7f5f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
<div style="max-width:640px;margin:0 auto;padding:24px 16px">

  <!-- HEADER -->
  <div style="background:#1a3a2a;border-radius:10px 10px 0 0;padding:24px 28px;margin-bottom:0">
    <div style="font-size:10px;letter-spacing:0.16em;text-transform:uppercase;color:rgba(255,255,255,0.5);margin-bottom:6px">Weekly Intelligence Report Card</div>
    <div style="font-size:22px;font-weight:700;color:#ffffff;line-height:1.1">Assistiv Platform<br><span style="color:rgba(255,255,255,0.6);font-weight:400;font-size:18px">Kent &amp; Medway</span></div>
    <div style="font-size:11px;color:rgba(255,255,255,0.4);margin-top:8px">{week} · Generated {generated} · assistiv.cloud</div>
  </div>

  <!-- STAT STRIP -->
  <div style="background:#ffffff;padding:16px 28px;border-left:1px solid #d8e4dc;border-right:1px solid #d8e4dc;display:flex;gap:0">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="text-align:center;padding:8px 0;border-right:1px solid #e8e0d4">
        <div style="font-size:24px;font-weight:700;color:{"#c04828" if critical_count > 0 else "#1a3a2a"}">{critical_count}</div>
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#5a6b62">Critical</div>
      </td>
      <td style="text-align:center;padding:8px 0;border-right:1px solid #e8e0d4">
        <div style="font-size:24px;font-weight:700;color:#8a6200">{high_count}</div>
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#5a6b62">High risk</div>
      </td>
      <td style="text-align:center;padding:8px 0;border-right:1px solid #e8e0d4">
        <div style="font-size:24px;font-weight:700;color:{"#c04828" if risers else "#1a3a2a"}">{len(risers)}</div>
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#5a6b62">Rising ↑</div>
      </td>
      <td style="text-align:center;padding:8px 0;border-right:1px solid #e8e0d4">
        <div style="font-size:24px;font-weight:700;color:#1a3a2a">{week_q}</div>
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#5a6b62">Questions</div>
      </td>
      <td style="text-align:center;padding:8px 0">
        <div style="font-size:24px;font-weight:700;color:{"#166534" if sat_pct and sat_pct>=80 else "#8a6200" if sat_pct and sat_pct>=60 else "#1a3a2a"}">{f"{sat_pct}%" if sat_pct is not None else "—"}</div>
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#5a6b62">Satisfaction</div>
      </td>
    </tr></table>
  </div>

  <!-- MAIN CONTENT -->
  <div style="background:#ffffff;border:1px solid #d8e4dc;border-top:none;border-radius:0 0 10px 10px;padding:24px 28px">

    <!-- ALERTS -->
    <div style="margin-bottom:20px">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:#5a6b62;margin-bottom:8px">⚠ Alerts</div>
      {alert_html}
      {f'<div style="margin-top:8px;font-size:12px;color:#c04828">Rising this week: {", ".join(f"{n} (+{d} pts)" for n,_,d in [(r["name"],r["fep"],r["delta"]) for r in risers])}</div>' if risers else ""}
    </div>

    <!-- FEP TABLE -->
    <div style="margin-bottom:20px">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:#5a6b62;margin-bottom:8px">📊 FEP District Scores</div>
      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;border:1px solid #e8e0d4;border-radius:6px;overflow:hidden">
        <thead>
          <tr style="background:#f7f5f0">
            <th style="padding:6px 8px;text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#5a6b62;font-weight:600">#</th>
            <th style="padding:6px 8px;text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#5a6b62;font-weight:600">District</th>
            <th style="padding:6px 8px;text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#5a6b62;font-weight:600">FEP</th>
            <th style="padding:6px 8px;text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#5a6b62;font-weight:600">Risk</th>
            <th style="padding:6px 8px;text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#5a6b62;font-weight:600">Δ wk</th>
          </tr>
        </thead>
        <tbody>{fep_rows}</tbody>
      </table>
    </div>

    <!-- TWO COL: WINTER + PRESCRIBING -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px"><tr valign="top">
      <td width="50%" style="padding-right:10px">
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:#5a6b62;margin-bottom:8px">❄ Winter Top 5</div>
        <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;border:1px solid #e8e0d4;border-radius:6px;overflow:hidden">
          <thead><tr style="background:#f7f5f0">
            <th style="padding:5px 8px;text-align:left;font-size:10px;color:#5a6b62;font-weight:600">District</th>
            <th style="padding:5px 8px;text-align:left;font-size:10px;color:#5a6b62;font-weight:600">WVI</th>
            <th style="padding:5px 8px;text-align:left;font-size:10px;color:#5a6b62;font-weight:600">Tier</th>
          </tr></thead>
          <tbody>{winter_rows}</tbody>
        </table>
        {upcoming_block}
      </td>
      <td width="50%" style="padding-left:10px">
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:#5a6b62;margin-bottom:8px">💊 Prescribing Outliers</div>
        <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;border:1px solid #e8e0d4;border-radius:6px;overflow:hidden">
          <thead><tr style="background:#f7f5f0">
            <th style="padding:5px 8px;text-align:left;font-size:10px;color:#5a6b62;font-weight:600">District</th>
            <th style="padding:5px 8px;text-align:left;font-size:10px;color:#5a6b62;font-weight:600">Signal</th>
            <th style="padding:5px 8px;text-align:left;font-size:10px;color:#5a6b62;font-weight:600">Ratio</th>
          </tr></thead>
          <tbody>{rx_rows}</tbody>
        </table>
      </td>
    </tr></table>

    <!-- AGENT QUESTIONS -->
    <div style="margin-bottom:20px">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:#5a6b62;margin-bottom:8px">🤖 Agent Intelligence — {week_q} questions this week</div>
      {flagged_block}
      <div style="font-size:12px;color:#5a6b62;margin-bottom:8px">{sat_block}{week_ada} ADA · {week_vera} VERA · {week_up} 👍 {week_down} 👎</div>
      <table width="100%" cellpadding="0" cellspacing="0"><tr valign="top">
        <td width="50%" style="padding-right:8px">
          <div style="font-size:11px;font-weight:600;color:#1a3a2a;margin-bottom:6px">✦ Top ADA questions</div>
          <ul style="margin:0;padding-left:16px">{ada_qs}</ul>
        </td>
        <td width="50%" style="padding-left:8px">
          <div style="font-size:11px;font-weight:600;color:#4c1d95;margin-bottom:6px">⚖ Top VERA challenges</div>
          <ul style="margin:0;padding-left:16px">{vera_qs}</ul>
        </td>
      </tr></table>
    </div>

    <!-- LINKS -->
    <div style="border-top:1px solid #e8e0d4;padding-top:16px;margin-top:4px">
      <table cellpadding="0" cellspacing="0"><tr>
        <td style="padding-right:10px"><a href="https://www.assistiv.cloud/briefing/" style="display:inline-block;background:#1a3a2a;color:#ffffff;font-size:12px;font-weight:600;padding:8px 16px;border-radius:6px;text-decoration:none">Commissioner Briefing →</a></td>
        <td style="padding-right:10px"><a href="https://www.assistiv.cloud/logs/digest/" style="display:inline-block;background:#f7f5f0;border:1px solid #d8e4dc;color:#1a3a2a;font-size:12px;font-weight:600;padding:8px 16px;border-radius:6px;text-decoration:none">Full Report Card →</a></td>
        <td><a href="https://www.assistiv.cloud/logs/" style="display:inline-block;background:#f7f5f0;border:1px solid #d8e4dc;color:#1a3a2a;font-size:12px;font-weight:600;padding:8px 16px;border-radius:6px;text-decoration:none">Agent Logs →</a></td>
      </tr></table>
    </div>

  </div>

  <!-- FOOTER -->
  <div style="padding:16px 0;font-size:11px;color:#8a9e8a;text-align:center;line-height:1.7">
    Assistiv Systems Limited · Company No. 17082597 · Faversham, Kent<br>
    Population triage instrument only — not a clinical document.<br>
    <a href="https://www.assistiv.cloud" style="color:#2d6b47">assistiv.cloud</a>
  </div>

</div>
</body>
</html>"""
    return html


def send_email(subject, html_body):
    """Send digest email via Resend API."""
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print("  ⚠ RESEND_API_KEY not set — skipping email")
        return False

    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": "Assistiv Digest <digest@assistiv.cloud>",
                "to": ["simon@assistiv.co", "paul@assistiv.co"],
                "subject": subject,
                "html": html_body,
            },
            timeout=20,
        )
        if resp.ok:
            print(f"  ✓ Email sent — {resp.json().get('id','?')}")
            return True
        else:
            print(f"  ✗ Email failed: {resp.status_code} {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"  ✗ Email error: {e}")
        return False


# ── SEND ──────────────────────────────────────────────────────────────
print("\nBuilding and sending email digest...")
crisis_label = f"🔴 {len(crisis)} crisis precursor{'s' if len(crisis)>1 else ''}" if crisis else (
    f"🟠 {len(critical)} critical district{'s' if len(critical)>1 else ''}" if critical else "✅ No alerts"
)
subject = f"Assistiv Report Card {WEEK_NUM} — {crisis_label} · {len(week_entries)} agent questions"
email_html = build_email_html(summary, digest_md)
send_email(subject, email_html)


print(f"\n{'='*60}")
print(f"Digest complete — {WEEK_NUM}")
print(f"  Critical districts: {len(critical)}")
print(f"  Crisis precursors:  {len(crisis)}")
print(f"  Agent questions this week: {len(week_entries)}")
print(f"  Satisfaction: {len(week_up)}/{len(week_rated)} rated helpful")
print(f"{'='*60}\n")
