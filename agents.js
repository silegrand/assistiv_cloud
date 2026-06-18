/*
 * agents.js — Shared ADA + VERA agent widget
 * Assistiv Systems · assistiv.cloud
 *
 * Usage: in each page, before this script tag, set:
 *   <script>
 *     window.PAGE_CONTEXT = {
 *       title: 'Page name',
 *       description: 'What this page shows',
 *       adaStarters: ['Question 1', 'Question 2', 'Question 3', 'Question 4'],
 *       veraStarters: ['Challenge 1', 'Challenge 2', 'Challenge 3', 'Challenge 4'],
 *     };
 *   </script>
 *   <script src="/agents.js"></script>
 */

(function() {

// ── CSS ────────────────────────────────────────────────────────────────
const css = `
/* ── agent button colour overrides per page ── */
:root {
  --agent-ada-bg: var(--forest, #1a3a2a);
  --agent-ada-accent: var(--sage, #2D5A4E);
  --agent-ada-pale: #eaf3ee;
  --agent-ada-dot: var(--sage, #2D5A4E);
  --agent-ada-msg-bg: #eaf3ee;
  --agent-ada-msg-text: #1a2e1e;
}

.agent-btn {
  position:fixed;bottom:1.5rem;z-index:9000;
  width:52px;height:52px;border-radius:50%;
  border:1px solid rgba(0,0,0,0.1);cursor:pointer;
  box-shadow:0 4px 18px rgba(0,0,0,0.18);
  display:flex;align-items:center;justify-content:center;
  flex-direction:column;gap:2px;
  transition:transform .18s,box-shadow .18s;
  font-family:system-ui,sans-serif;
}
.agent-btn:hover{transform:scale(1.07);box-shadow:0 6px 24px rgba(0,0,0,0.25);}
.agent-icon{font-size:16px;line-height:1;}
.agent-lbl{font-size:9px;letter-spacing:.1em;font-weight:700;}

#ada-btn  { right:1.5rem; background:#fff; }
#ada-btn  .agent-lbl { color:#2D5A4E; }
#ada-btn  .agent-icon { color:#2D5A4E; }
#vera-btn { right:5rem;   background:#fff; }
#vera-btn .agent-lbl { color:#7c3aed; }
#vera-btn .agent-icon { color:#7c3aed; }

.agent-panel {
  position:fixed;bottom:5rem;z-index:9000;
  width:360px;max-width:calc(100vw - 2rem);
  height:520px;max-height:calc(100vh - 7rem);
  background:#ffffff;border:1px solid #ddd8ce;
  border-radius:14px;box-shadow:0 12px 40px rgba(0,0,0,0.18);
  display:none;flex-direction:column;overflow:hidden;
  font-family:system-ui,sans-serif;
}
.agent-panel.open{display:flex;animation:agentIn .22s ease;}
@keyframes agentIn{from{opacity:0;transform:translateY(12px) scale(.97);}to{opacity:1;transform:translateY(0) scale(1);}}

#ada-panel  { right:1.5rem; }
#vera-panel { right:1.5rem; }

.agent-hdr { padding:.75rem 1rem;display:flex;align-items:center;gap:.6rem;flex-shrink:0; }
#ada-panel  .agent-hdr { background:#1a3a2a; }
#vera-panel .agent-hdr { background:#4c1d95; }

.agent-av { width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;background:rgba(255,255,255,.18); }
.agent-hdr-name { font-size:13px;font-weight:600;color:#fff; }
.agent-hdr-sub  { font-size:10px;color:rgba(255,255,255,.6); }
.agent-close    { background:none;border:none;color:rgba(255,255,255,.7);cursor:pointer;font-size:18px;margin-left:auto;padding:0 4px; }

.agent-msgs { flex:1;overflow-y:auto;padding:.75rem 1rem;display:flex;flex-direction:column;gap:.6rem; }
.agent-m { max-width:88%;padding:.55rem .8rem;border-radius:10px;font-size:12.5px;line-height:1.55;animation:mIn .18s ease; }
@keyframes mIn{from{opacity:0;transform:translateY(4px);}to{opacity:1;transform:translateY(0);}}
.agent-m.usr  { background:#1a3a2a;color:#fff;align-self:flex-end;border-radius:10px 10px 2px 10px; }
.agent-m.ada  { background:#eaf3ee;color:#1a2e1e;align-self:flex-start; }
.agent-m.ada strong { color:#1a3a2a; }
.agent-m.vera { background:#f5f3ff;color:#3b0764;align-self:flex-start;border-left:2px solid #7c3aed; }
.agent-m.vera strong { color:#6d28d9; }

.agent-starts { padding:0 1rem .75rem;display:flex;flex-direction:column;gap:.4rem;flex-shrink:0; }
.agent-start  { background:none;border:1px solid #ddd;border-radius:8px;padding:.45rem .75rem;text-align:left;cursor:pointer;font-size:11.5px;color:#555;transition:all .12s; }
#ada-panel  .agent-start:hover { background:#eaf3ee;border-color:#2D5A4E; }
#vera-panel .agent-start:hover { background:#f5f3ff;border-color:#7c3aed;color:#3b0764; }

.agent-think { display:flex;gap:4px;padding:.55rem .8rem;border-radius:10px;align-self:flex-start; }
#ada-panel  .agent-think { background:#eaf3ee; }
#vera-panel .agent-think { background:#f5f3ff; }
.agent-dot { width:6px;height:6px;border-radius:50%;animation:adot 1.2s infinite; }
#ada-panel  .agent-dot { background:#2D5A4E; }
#vera-panel .agent-dot { background:#7c3aed; }
.agent-dot:nth-child(2){animation-delay:.2s;}.agent-dot:nth-child(3){animation-delay:.4s;}
@keyframes adot{0%,80%,100%{opacity:.2;transform:scale(.8);}40%{opacity:1;transform:scale(1);}}

.agent-inp-row { display:flex;gap:.5rem;padding:.6rem 1rem;border-top:1px solid #e8e0d4;flex-shrink:0; }
.agent-inp { flex:1;border:1px solid #ddd;border-radius:8px;padding:.45rem .7rem;font-size:12.5px;font-family:inherit;background:#f7f4ee;color:#1a2e1e;outline:none; }
#ada-inp:focus  { border-color:#2D5A4E; }
#vera-inp:focus { border-color:#7c3aed; }
.agent-snd { color:#fff;border:none;border-radius:8px;padding:.45rem .75rem;cursor:pointer;font-size:13px; }
#ada-snd  { background:#1a3a2a; }
#ada-snd:hover  { background:#2D5A4E; }
#vera-snd { background:#6d28d9; }
#vera-snd:hover { background:#4c1d95; }
.agent-snd:disabled { opacity:.4;cursor:default; }
`;

// Inject CSS
const styleEl = document.createElement('style');
styleEl.textContent = css;
document.head.appendChild(styleEl);

// ── HTML ───────────────────────────────────────────────────────────────
const html = `
<button id="ada-btn" class="agent-btn" title="Ask Ada">
  <span class="agent-icon">✦</span>
  <span class="agent-lbl">ADA</span>
</button>
<button id="vera-btn" class="agent-btn" title="Challenge with VERA">
  <span class="agent-icon">⚖</span>
  <span class="agent-lbl">VERA</span>
</button>

<div id="ada-panel" class="agent-panel" role="dialog" aria-label="Ada intelligence assistant">
  <div class="agent-hdr">
    <div class="agent-av">✦</div>
    <div><div class="agent-hdr-name">Ada</div><div class="agent-hdr-sub">Assistiv Intelligence · explainer</div></div>
    <button class="agent-close" id="ada-close">×</button>
  </div>
  <div class="agent-msgs" id="ada-msgs"></div>
  <div class="agent-starts" id="ada-starts"></div>
  <div class="agent-inp-row">
    <input id="ada-inp" class="agent-inp" type="text" placeholder="Ask Ada…">
    <button id="ada-snd" class="agent-snd">↑</button>
  </div>
</div>

<div id="vera-panel" class="agent-panel" role="dialog" aria-label="VERA red team challenger">
  <div class="agent-hdr">
    <div class="agent-av">⚖</div>
    <div><div class="agent-hdr-name">VERA</div><div class="agent-hdr-sub">Validation · Evidence · Rigour · Assumptions</div></div>
    <button class="agent-close" id="vera-close">×</button>
  </div>
  <div class="agent-msgs" id="vera-msgs"></div>
  <div class="agent-starts" id="vera-starts"></div>
  <div class="agent-inp-row">
    <input id="vera-inp" class="agent-inp" type="text" placeholder="Challenge a finding…">
    <button id="vera-snd" class="agent-snd">↑</button>
  </div>
</div>
`;

document.body.insertAdjacentHTML('beforeend', html);

// ── CONFIG ─────────────────────────────────────────────────────────────
const ctx = window.PAGE_CONTEXT || {};
const pageTitle       = ctx.title       || document.title || 'Assistiv Intelligence';
const pageDescription = ctx.description || 'An Assistiv population intelligence tool for Kent and Medway.';
const adaStarters     = ctx.adaStarters  || [
  'What does this page show?',
  'Who is the intended audience for this tool?',
  'How should a commissioner use this data?',
  'What are the key findings here?',
];
const veraStarters    = ctx.veraStarters || [
  'What are the main limitations of this data?',
  'How reliable are these figures?',
  'What would a peer reviewer challenge here?',
  'Should a commissioner act on this alone?',
];

const AGENT_WORKER   = 'https://assistiv-proxy.simongeorgelegrand.workers.dev';
const AGENT_LOG_URL  = 'https://assistiv-proxy.simongeorgelegrand.workers.dev/log';

// Session ID — anonymous, resets each page load, used only to group
// questions from the same visit in the logs
const SESSION_ID = Math.random().toString(36).slice(2, 10);

function logQuestion(agent, question) {
  // Fire-and-forget — never blocks the agent response, never surfaces errors to user
  const ctx = window.PAGE_CONTEXT || {};
  const district = ctx.title?.match(/^(.+?) ·/)?.[1] || '';
  fetch(AGENT_LOG_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      _type:    'log',
      agent,
      question: question.slice(0, 500),
      page:     window.location.pathname,
      district: district.slice(0, 60),
      session:  SESSION_ID,
    }),
  }).catch(() => {}); // silent fail
}
const AGENT_JSON   = 'https://raw.githubusercontent.com/silegrand/assistivagents/main/kent-fep-data.json';

let agentLiveData = null;
fetch(AGENT_JSON + '?t=' + Date.now(), {cache:'no-store'})
  .then(r => r.json()).then(d => { agentLiveData = d; })
  .catch(() => {});

function agentCtx() {
  const lines = [`PAGE: ${pageTitle}`, `CONTEXT: ${pageDescription}`];
  // Try to pull whatever district/metric is visible on the page
  const selectors = [
    '.district-name', '.d-name', '.fep-val', '.ravi-val',
    '.brand-title', '[data-district]', '.metric-val'
  ];
  selectors.forEach(sel => {
    const el = document.querySelector(sel);
    if (el?.textContent?.trim()) lines.push(`VISIBLE: ${el.textContent.trim()}`);
  });
  if (agentLiveData?.districts) {
    lines.push('\nLIVE FEP SCORES (Kent & Medway):');
    agentLiveData.districts.forEach(d => lines.push(`  ${d.name}: FEP ${d.fep} (${d.risk})`));
  }
  return lines.join('\n');
}

async function agentCall(msgs, systemPrompt) {
  const r = await fetch(AGENT_WORKER, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({
      model: 'claude-haiku-4-5-20251001',
      max_tokens: 700,
      system: systemPrompt + '\n\n---\nLIVE CONTEXT:\n' + agentCtx(),
      messages: msgs,
    }),
  });
  const data = await r.json();
  return data?.content?.[0]?.text || 'Could not get a response — please try again.';
}

// ── ADA ────────────────────────────────────────────────────────────────
const ADA_SYS = `You are Ada, an AI assistant built by Assistiv Systems. You help commissioners, clinical teams, and carers understand Assistiv's population intelligence tools for Kent and Medway.

TONE: Plain English. Warm but precise. No clinical jargon unless the person uses it first.

THE PLATFORM: Assistiv builds frailty and population intelligence for the 'Missing Middle' — older adults managing at home but vulnerable to crisis. Tools include: FEP (Frailty Early Prediction, 0-100, England avg=50), RAVI (Rural Access Vulnerability Index), CBI (Carer Burden Index), NHS Pressure Map, Winter Readiness Intelligence, Carers Intensity Map, Kent Falls Hotspot Map, and the Carer Companion concept.

FEP BANDS: Low <40, Moderate 40-54, High 55-69, Critical 70+. 22 signals including NHS Fingertips, NHSBSA prescribing, SECAmb FOI falls data.

KENT CONTEXT: Thanet, Folkestone & Hythe, Dover — coastal east Kent, higher deprivation, older demographics. Sevenoaks, Tunbridge Wells — lowest FEP but hidden rural LSOA hotspots.

You have live FEP data and page context injected below. Use it confidently.

DO NOT give individual clinical advice. When VERA is mentioned, acknowledge it positively.`;

let adaOpen=false, adaHist=[], adaStartsShown=true, adaBusy=false;

document.getElementById('ada-btn').addEventListener('click', adaToggle);
document.getElementById('ada-close').addEventListener('click', adaToggle);
document.getElementById('ada-snd').addEventListener('click', adaSend);
document.getElementById('ada-inp').addEventListener('keydown', e => { if(e.key==='Enter') adaSend(); });

function adaToggle() {
  adaOpen = !adaOpen;
  document.getElementById('ada-panel').classList.toggle('open', adaOpen);
  if (adaOpen && adaHist.length === 0) adaGreet();
  if (adaOpen) { veraOpen=false; document.getElementById('vera-panel').classList.remove('open'); }
}

function adaGreet() {
  adaAdd('ada', `Hi, I'm <strong>Ada</strong> — I explain what this tool is showing and what it means for communities in Kent and Medway.<br><small style="color:#7aab90;margin-top:4px;display:block">Tip: VERA (⚖) will challenge the findings for balance.</small>`);
  renderAdaStarters();
}

function renderAdaStarters() {
  if (!adaStartsShown) return;
  document.getElementById('ada-starts').innerHTML =
    adaStarters.map(s => `<button class="agent-start" data-ada-start="${s.replace(/"/g,'&quot;')}">${s}</button>`).join('');
  document.querySelectorAll('[data-ada-start]').forEach(btn => {
    btn.addEventListener('click', () => { adaStartsShown=false; document.getElementById('ada-starts').innerHTML=''; adaSendText(btn.dataset.adaStart); });
  });
}

function adaSend() {
  const v = document.getElementById('ada-inp').value.trim();
  if (!v || adaBusy) return;
  document.getElementById('ada-inp').value = '';
  adaStartsShown = false; document.getElementById('ada-starts').innerHTML = '';
  adaSendText(v);
}

async function adaSendText(text) {
  if (adaBusy) return;
  adaBusy = true;
  adaAdd('usr', text);
  adaHist.push({role:'user', content:text});
  logQuestion('ADA', text);
  const th = agentThink('ada-msgs', 'ada');
  document.getElementById('ada-snd').disabled = true;
  try {
    const reply = await agentCall(adaHist, ADA_SYS);
    th.remove(); adaAdd('ada', reply);
    adaHist.push({role:'assistant', content:reply});
    if (adaHist.length > 20) adaHist = adaHist.slice(-20);
  } catch(e) { th.remove(); adaAdd('ada', 'Connection issue — please try again.'); }
  adaBusy = false;
  document.getElementById('ada-snd').disabled = false;
}

function adaAdd(role, html) {
  const el = document.createElement('div');
  el.className = `agent-m ${role === 'usr' ? 'usr' : 'ada'}`;
  el.innerHTML = html;
  document.getElementById('ada-msgs').appendChild(el);
  document.getElementById('ada-msgs').scrollTop = 9999;
}

// ── VERA ───────────────────────────────────────────────────────────────
const VERA_SYS = `You are VERA — Validation, Evidence, Rigour, Assumptions. You are the red team agent for Assistiv Systems. Your job is to surface honest, calibrated challenges to the data, methodology, and findings — so users develop appropriately critical thinking.

TONE: Rigorous but constructive. A thoughtful peer reviewer, not a hostile critic. Identify weaknesses, then acknowledge what remains useful. Never dismissive. Never nihilistic.

KNOWN METHODOLOGICAL LIMITATIONS:

1. FEP MODEL NOT YET VALIDATED against actual Kent frailty prevalence data — clinical face validity only, no empirical confirmation yet.
2. THREE DEMOGRAPHIC PROXY SIGNALS (over-75s alone, IMD, care home gap) are modelled district estimates, not directly observed.
3. RAVI: Three of five signals currently use England national averages as LSOA fallback — district discrimination driven primarily by geographic barriers and rural classification.
4. CBI: Four of five signals are county-level (Kent-wide), not district-level. District discrimination comes almost entirely from Census 2021 intensive carer rates.
5. 111 COST ESTIMATES: SECAmb contract data covers Kent, Medway AND Sussex combined — Kent share is 40% population-weighted estimate.
6. DISCHARGE DATA: Trust-level, not district-level. Cannot be attributed to specific districts.
7. ECONOMIC MODEL: Preventability fractions from national systematic reviews, not Kent-specific. ±30% uncertainty range is honest but precision is overstated.
8. PRESCRIBING PROXIES: Reflect GP surgery populations, not older adults specifically.
9. CARERS MAP: Census 2021 directly counts unpaid care hours — but Census undercounts carers, especially spouses who don't self-identify.
10. FALLS DATA: SECAmb FOI covers ambulance-attended falls — a subset of all falls, biased toward severity and geography of coverage.

WHAT YOU SHOULD NOT DO:
- Repeat challenges already acknowledged in the conversation
- Challenge everything at once — pick the most relevant limitation
- Say the tool is useless — it is genuinely useful as a triage instrument
- Be unkind or dismissive
Always end with what the finding IS still useful for, despite the limitation.

When Ada is mentioned, acknowledge it positively.`;

let veraOpen=false, veraHist=[], veraStartsShown=true, veraBusy=false;

document.getElementById('vera-btn').addEventListener('click', veraToggle);
document.getElementById('vera-close').addEventListener('click', veraToggle);
document.getElementById('vera-snd').addEventListener('click', veraSend);
document.getElementById('vera-inp').addEventListener('keydown', e => { if(e.key==='Enter') veraSend(); });

function veraToggle() {
  veraOpen = !veraOpen;
  document.getElementById('vera-panel').classList.toggle('open', veraOpen);
  if (veraOpen && veraHist.length === 0) veraGreet();
  if (veraOpen) { adaOpen=false; document.getElementById('ada-panel').classList.remove('open'); }
}

function veraGreet() {
  veraAdd('vera', `I'm <strong>VERA</strong> — Validation, Evidence, Rigour, Assumptions. I challenge the findings and surface the methodology's limitations.<br><br>I'm not here to dismiss the work — I'm here to make sure you use it with appropriate caution.<br><small style="color:#7c3aed;margin-top:4px;display:block">Use Ada (✦) for explanations, VERA for challenge.</small>`);
  renderVeraStarters();
}

function renderVeraStarters() {
  if (!veraStartsShown) return;
  document.getElementById('vera-starts').innerHTML =
    veraStarters.map(s => `<button class="agent-start" data-vera-start="${s.replace(/"/g,'&quot;')}">${s}</button>`).join('');
  document.querySelectorAll('[data-vera-start]').forEach(btn => {
    btn.addEventListener('click', () => { veraStartsShown=false; document.getElementById('vera-starts').innerHTML=''; veraSendText(btn.dataset.veraStart); });
  });
}

function veraSend() {
  const v = document.getElementById('vera-inp').value.trim();
  if (!v || veraBusy) return;
  document.getElementById('vera-inp').value = '';
  veraStartsShown = false; document.getElementById('vera-starts').innerHTML = '';
  veraSendText(v);
}

async function veraSendText(text) {
  if (veraBusy) return;
  veraBusy = true;
  veraAdd('usr', text);
  veraHist.push({role:'user', content:text});
  logQuestion('VERA', text);
  const th = agentThink('vera-msgs', 'vera');
  document.getElementById('vera-snd').disabled = true;
  try {
    const reply = await agentCall(veraHist, VERA_SYS);
    th.remove(); veraAdd('vera', reply);
    veraHist.push({role:'assistant', content:reply});
    if (veraHist.length > 20) veraHist = veraHist.slice(-20);
  } catch(e) { th.remove(); veraAdd('vera', 'Connection issue — please try again.'); }
  veraBusy = false;
  document.getElementById('vera-snd').disabled = false;
}

function veraAdd(role, html) {
  const el = document.createElement('div');
  el.className = `agent-m ${role === 'usr' ? 'usr' : 'vera'}`;
  el.innerHTML = html;
  document.getElementById('vera-msgs').appendChild(el);
  document.getElementById('vera-msgs').scrollTop = 9999;
}

// ── SHARED ─────────────────────────────────────────────────────────────
function agentThink(containerId, type) {
  const el = document.createElement('div');
  el.className = 'agent-think';
  el.innerHTML = '<div class="agent-dot"></div><div class="agent-dot"></div><div class="agent-dot"></div>';
  document.getElementById(containerId).appendChild(el);
  document.getElementById(containerId).scrollTop = 9999;
  return el;
}

})();
