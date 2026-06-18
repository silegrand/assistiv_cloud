/* ============================================================
   ASSISTIV SYSTEMS — Anthropic API Proxy + Question Logger
   Cloudflare Worker · v1.2

   Environment variables (set in Cloudflare dashboard):
   - ANTHROPIC_API_KEY  : your key from console.anthropic.com
   - GITHUB_LOG_TOKEN   : classic PAT with repo scope
                          (secret name: GITHUB_LOG_TOKEN)

   Endpoints:
   POST /          → proxies Anthropic API calls (Ada / VERA)
   POST /log       → appends a question entry to
                     silegrand/assistiv_cloud logs/agent-questions.json
   ============================================================ */

const ALLOWED_ORIGINS = [
  'https://www.assistiv.cloud',
  'https://assistiv.cloud',
  'https://www.assistiv.co',
  'https://assistiv.co',
  'https://www.assistiv.tools',
  'https://assistiv.tools',
  'https://www.assistiv.services',
  'https://assistiv.services',
  'https://www.assistiv.health',
  'https://assistiv.health',
  'https://silegrand.github.io',
  'https://www.resiliencetools.xyz',
  'http://localhost',
  'http://127.0.0.1',
];

const MAX_TOKENS_LIMIT = 1000;
const LOG_REPO         = 'silegrand/assistiv_cloud';
const LOG_FILE         = 'logs/agent-questions.json';
const LOG_BRANCH       = 'main';
const GITHUB_API       = `https://api.github.com/repos/${LOG_REPO}/contents/${LOG_FILE}`;
const MAX_LOG_ENTRIES  = 2000;   // cap to keep the file manageable

export default {
  async fetch(request, env) {

    const origin = request.headers.get('Origin') || '';
    const originAllowed = ALLOWED_ORIGINS.some(
      o => origin === o || origin.startsWith(o + '/')
    );
    const url = new URL(request.url);

    // ── CORS preflight ──────────────────────────────────────────────
    if (request.method === 'OPTIONS') {
      return corsResponse(null, 204, originAllowed ? origin : '');
    }

    // ── Only allow POST ─────────────────────────────────────────────
    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    // ── Origin check ────────────────────────────────────────────────
    if (!originAllowed) {
      console.log(`Blocked origin: ${origin}`);
      return new Response('Forbidden', { status: 403 });
    }

    // ── Route: /log ─────────────────────────────────────────────────
    // Check pathname first, then fall back to checking the body _type field
    // (workers.dev subdomains reliably preserve pathnames, but belt-and-braces)
    if (url.pathname === '/log' || url.pathname.endsWith('/log')) {
      return handleLog(request, env, origin);
    }

    // ── Route: / (default) — Anthropic proxy ────────────────────────
    // Clone body to allow double-read: peek at _type before deciding route
    const bodyText = await request.text();
    let bodyParsed;
    try { bodyParsed = JSON.parse(bodyText); } catch { bodyParsed = {}; }

    if (bodyParsed._type === 'log') {
      // Reconstruct a readable request for handleLog
      const fakeReq = new Request(request.url, {
        method: 'POST',
        headers: request.headers,
        body: bodyText,
      });
      return handleLog(fakeReq, env, origin);
    }

    // Reconstruct for proxy (body was consumed above)
    const proxyReq = new Request(request.url, {
      method: 'POST',
      headers: request.headers,
      body: bodyText,
    });
    return handleProxy(proxyReq, env, origin);
  }
};

// ── ANTHROPIC PROXY ──────────────────────────────────────────────────────────
async function handleProxy(request, env, origin) {
  if (!env.ANTHROPIC_API_KEY) {
    return corsResponse(
      JSON.stringify({ error: 'API key not configured' }),
      500, origin, 'application/json'
    );
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return corsResponse(
      JSON.stringify({ error: 'Invalid JSON body' }),
      400, origin, 'application/json'
    );
  }

  if (!body.max_tokens || body.max_tokens > MAX_TOKENS_LIMIT) {
    body.max_tokens = MAX_TOKENS_LIMIT;
  }
  if (!body.model) {
    body.model = 'claude-haiku-4-5-20251001';
  }

  try {
    const anthropicResp = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type':      'application/json',
        'x-api-key':         env.ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify(body),
    });

    const data = await anthropicResp.json();

    if (!anthropicResp.ok) {
      console.error('Anthropic error:', anthropicResp.status, data);
      return corsResponse(
        JSON.stringify({
          error:  data?.error?.message || 'Anthropic API error',
          status: anthropicResp.status,
        }),
        anthropicResp.status, origin, 'application/json'
      );
    }

    return corsResponse(JSON.stringify(data), 200, origin, 'application/json');

  } catch (err) {
    console.error('Worker fetch error:', err);
    return corsResponse(
      JSON.stringify({ error: 'Worker error — please try again' }),
      500, origin, 'application/json'
    );
  }
}

// ── QUESTION LOGGER ──────────────────────────────────────────────────────────
async function handleLog(request, env, origin) {
  if (!env.GITHUB_LOG_TOKEN) {
    // Silently succeed if token not yet configured — don't break the agent UX
    return corsResponse(JSON.stringify({ ok: true, note: 'logging not configured' }),
      200, origin, 'application/json');
  }

  let entry;
  try {
    entry = await request.json();
  } catch {
    return corsResponse(JSON.stringify({ error: 'Invalid JSON' }), 400, origin, 'application/json');
  }

  // Sanitise — only store what we need, cap question length
  const record = {
    ts:       new Date().toISOString(),
    agent:    String(entry.agent    || '').slice(0, 10),
    question: String(entry.question || '').slice(0, 500),
    page:     String(entry.page     || '').slice(0, 200),
    district: String(entry.district || '').slice(0, 60),
    session:  String(entry.session  || '').slice(0, 16),
  };

  const ghHeaders = {
    'Authorization': `token ${env.GITHUB_LOG_TOKEN}`,
    'Accept':        'application/vnd.github.v3+json',
    'Content-Type':  'application/json',
    'User-Agent':    'assistiv-worker',
  };

  try {
    // 1. Fetch current file (need its SHA to update it)
    const getResp = await fetch(
      `${GITHUB_API}?ref=${LOG_BRANCH}&t=${Date.now()}`,
      { headers: ghHeaders }
    );

    let entries = [];
    let sha     = null;

    if (getResp.status === 200) {
      const fileData = await getResp.json();
      sha = fileData.sha;
      try {
        const decoded = JSON.parse(atob(fileData.content.replace(/\n/g, '')));
        entries = Array.isArray(decoded) ? decoded : [];
      } catch { entries = []; }
    }
    // 404 = file doesn't exist yet — that's fine, we'll create it

    // 2. Append new record, cap at MAX_LOG_ENTRIES
    entries.push(record);
    if (entries.length > MAX_LOG_ENTRIES) {
      entries = entries.slice(-MAX_LOG_ENTRIES);
    }

    // 3. Commit back
    const payload = {
      message: `log: agent question — ${record.agent} on ${record.page.split('/').filter(Boolean).pop() || 'home'} [${record.ts.slice(0,10)}]`,
      content: btoa(unescape(encodeURIComponent(JSON.stringify(entries, null, 2)))),
      branch:  LOG_BRANCH,
    };
    if (sha) payload.sha = sha;

    const putResp = await fetch(GITHUB_API, {
      method:  'PUT',
      headers: ghHeaders,
      body:    JSON.stringify(payload),
    });

    if (!putResp.ok) {
      const err = await putResp.text();
      console.error('GitHub write error:', putResp.status, err);
      return corsResponse(
        JSON.stringify({ ok: false, error: `GitHub ${putResp.status}` }),
        500, origin, 'application/json'
      );
    }

    return corsResponse(JSON.stringify({ ok: true }), 200, origin, 'application/json');

  } catch (err) {
    console.error('Log handler error:', err);
    // Fail silently from the user's perspective
    return corsResponse(JSON.stringify({ ok: true, note: 'log write failed silently' }),
      200, origin, 'application/json');
  }
}

// ── CORS helper ──────────────────────────────────────────────────────────────
function corsResponse(body, status, origin, contentType = 'text/plain') {
  const headers = {
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age':       '86400',
    'Vary':                         'Origin',
  };
  if (origin)      headers['Access-Control-Allow-Origin'] = origin;
  if (contentType) headers['Content-Type'] = contentType;
  return new Response(body, { status, headers });
}
