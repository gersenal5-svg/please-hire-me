#!/usr/bin/env python3
"""The approval gate: every listing the finder vets lands here, and nothing is applied to until you approve it.

State lives in state/review.json (gitignored). Statuses:
    pending      found and vetted by ./find.sh, waiting on you
    approved     you said yes; the next ./apply.sh may submit it
    rejected     you said no; never shown again, never applied to
    submitted    ./apply.sh submitted it (screenshot + applications/ doc exist)
    needs_human  ./apply.sh tried and hit something only you can supply
    skipped      ./apply.sh found it dead / ineligible at apply time
    by_hand      a portal the agent cannot apply on; shown so you can apply yourself

You:
    python3 scripts/review.py                  # open the review page in your browser (default)
    python3 scripts/review.py cli              # same, in the terminal: a/r/s/o per listing
    python3 scripts/review.py list [--status pending]
    python3 scripts/review.py approve ID [ID ...]   |  reject ID [ID ...]  |  reset ID [ID ...]

The agent (find phase):
    python3 scripts/review.py add --company C --title T --url U [--location L] [--comp X] [--ats A]
                                  [--why W] [--flags F] [--source S] [--by-hand]
        -> prints "ADDED <id>" or "DUPLICATE <id> <status>"; a duplicate is never re-queued.
The agent (apply phase):
    python3 scripts/review.py approved --json  # the only listings it may touch
    python3 scripts/review.py mark ID submitted|needs_human|skipped [--note N]
    python3 scripts/review.py hosts            # hostnames of approved listings (used by the browser hook)
"""
import argparse, datetime, hashlib, html, json, os, re, socket, subprocess, sys, tempfile, threading, urllib.parse, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(R, 'state', 'review.json')
STATUSES = ('pending', 'approved', 'rejected', 'submitted', 'needs_human', 'skipped', 'by_hand')
USER_SETTABLE = ('approved', 'rejected', 'pending')
AGENT_SETTABLE = ('submitted', 'needs_human', 'skipped')


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec='seconds')


def norm_url(u):
    """Same posting, same key: drop scheme, www, query noise (utm, gh_src, source), fragment, trailing slash."""
    p = urllib.parse.urlsplit(u.strip())
    host = p.netloc.lower().removeprefix('www.')
    keep = [(k, v) for k, v in urllib.parse.parse_qsl(p.query)
            if not re.match(r'(utm_|gh_src|source|src|ref|lever-source|lever-origin)', k, re.I)]
    q = urllib.parse.urlencode(sorted(keep))
    return f"{host}{p.path.rstrip('/')}" + (f'?{q}' if q else '')


def lid(u):
    return hashlib.sha1(norm_url(u).encode()).hexdigest()[:8]


def load():
    try:
        with open(DB) as f:
            d = json.load(f)
        return d if isinstance(d, dict) and isinstance(d.get('listings'), list) else {'listings': []}
    except FileNotFoundError:
        return {'listings': []}


def save(d):
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(DB), prefix='.review-', suffix='.json')
    with os.fdopen(fd, 'w') as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.write('\n')
    os.replace(tmp, DB)  # atomic: the review page and the agent never see a half-written file


def find(d, i):
    for x in d['listings']:
        if x['id'] == i:
            return x
    sys.exit(f'no listing with id {i}')


def set_status(ids, status, note=None, who='you'):
    d = load()
    for i in ids:
        x = find(d, i)
        if who == 'you' and x['status'] in AGENT_SETTABLE:
            print(f'{i}: already {x["status"]}, left alone'); continue
        if who == 'you' and x['status'] == 'by_hand' and status == 'approved':
            print(f'{i}: {x["company"]} is a by-hand portal (the agent has no account there). Apply yourself: {x["url"]}'); continue
        if who == 'agent' and x['status'] != 'approved':
            sys.exit(f'{i}: status is {x["status"]}, not approved. The agent may only mark listings you approved.')
        x['status'] = status
        x['updated'] = now()
        if note:
            x['note'] = note
        x.setdefault('history', []).append({'at': x['updated'], 'by': who, 'status': status, **({'note': note} if note else {})})
        print(f'{i}  {status:<11} {x["company"]} | {x["title"]}')
    save(d)


# ── agent: find phase ────────────────────────────────────────────────────────

def cmd_add(a):
    if not re.match(r'https?://', a.url):
        sys.exit('url must be http(s)')
    d = load()
    i = lid(a.url)
    for x in d['listings']:
        if x['id'] == i:
            print(f'DUPLICATE {i} {x["status"]}'); return
    d['listings'].append({
        'id': i, 'status': 'by_hand' if a.by_hand else 'pending',
        'company': a.company.strip(), 'title': a.title.strip(), 'url': a.url.strip(),
        'location': a.location, 'comp': a.comp, 'ats': a.ats, 'why': a.why, 'flags': a.flags,
        'source': a.source, 'found': now(), 'updated': now(),
    })
    save(d)
    print(f'ADDED {i}')


# ── agent: apply phase ───────────────────────────────────────────────────────

def approved():
    return [x for x in load()['listings'] if x['status'] == 'approved']


def cmd_hosts(_):
    hs = sorted({urllib.parse.urlsplit(x['url']).hostname or '' for x in approved()} - {''})
    print('\n'.join(hs))


# ── you: list / approve / reject ─────────────────────────────────────────────

def row(x):
    bits = [x['company'], x['title']]
    if x.get('location'): bits.append(x['location'])
    if x.get('comp'): bits.append(x['comp'])
    return f'{x["id"]}  {x["status"]:<11} ' + ' | '.join(bits)


def cmd_list(a):
    xs = load()['listings']
    if a.status:
        xs = [x for x in xs if x['status'] == a.status]
    if a.json:
        print(json.dumps(xs, indent=2, ensure_ascii=False)); return
    for x in xs:
        print(row(x))
        if a.verbose:
            if x.get('why'): print(f'          why:   {x["why"]}')
            if x.get('flags'): print(f'          flags: {x["flags"]}')
            print(f'          {x["url"]}')
    if not xs:
        print('(nothing)')


def counts():
    c = {}
    for x in load()['listings']:
        c[x['status']] = c.get(x['status'], 0) + 1
    return c


def cmd_cli(_):
    xs = [x for x in load()['listings'] if x['status'] == 'pending']
    if not xs:
        print('Nothing waiting for review. Run ./find.sh to look for new listings.'); return
    print(f'{len(xs)} listing(s) to review.  a = approve   r = reject   s = decide later   o = open in browser   q = quit\n')
    for n, x in enumerate(xs, 1):
        print(f'── {n}/{len(xs)} ' + '─' * 60)
        print(f'  {x["company"]}  —  {x["title"]}')
        for k in ('location', 'comp', 'ats', 'why', 'flags', 'source'):
            if x.get(k): print(f'  {k + ":":<10}{x[k]}')
        print(f'  {"link:":<10}{x["url"]}')
        while True:
            try:
                c = input('  [a/r/s/o/q] > ').strip().lower()[:1]
            except EOFError:
                c = 'q'
            if c == 'o':
                webbrowser.open(x['url']); continue
            if c in ('a', 'r'):
                set_status([x['id']], 'approved' if c == 'a' else 'rejected'); break
            if c == 's':
                break
            if c == 'q':
                print(f'\nStopped. Approved so far: {counts().get("approved", 0)}. Run ./apply.sh to submit them.'); return
    print(f'\nDone. Approved and waiting: {counts().get("approved", 0)}. Run ./apply.sh to submit them.')


# ── you: the review page ─────────────────────────────────────────────────────

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Listings to review</title>
<style>
:root{--bg:#f7f7f5;--card:#fff;--ink:#1a1a1a;--mute:#6b6b6b;--line:#e4e4e0;--ok:#1f7a4d;--no:#a33;--acc:#1f4fd1;--chip:#efefeb}
@media (prefers-color-scheme:dark){:root{--bg:#141414;--card:#1d1d1d;--ink:#ececec;--mute:#9a9a9a;--line:#2e2e2e;--ok:#4cc38a;--no:#e06c6c;--acc:#7aa2ff;--chip:#2a2a2a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif}
main{max-width:860px;margin:0 auto;padding:28px 16px 80px}
h1{font-size:22px;margin:0 0 4px}.sub{color:var(--mute);margin:0 0 20px}
nav{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:18px}
nav button{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:5px 12px;cursor:pointer;font:inherit;font-size:13px}
nav button.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin-bottom:10px}
.top{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}
.co{font-weight:600}.ti{font-size:16px}
.meta{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}.meta span{background:var(--chip);border-radius:6px;padding:1px 8px;font-size:13px}
.why{color:var(--mute);font-size:14px;margin:4px 0 0}.flags{color:var(--no);font-size:14px;margin:4px 0 0}
.acts{display:flex;gap:6px;flex-shrink:0}
.acts button,.acts a{font:inherit;font-size:13px;border-radius:7px;padding:6px 12px;cursor:pointer;border:1px solid var(--line);background:var(--card);color:var(--ink);text-decoration:none;white-space:nowrap}
.acts .yes{background:var(--ok);border-color:var(--ok);color:#fff}.acts .nono{color:var(--no)}
.st{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--mute)}
.empty{color:var(--mute);padding:40px 0;text-align:center}
.bar{position:fixed;left:0;right:0;bottom:0;background:var(--card);border-top:1px solid var(--line);padding:12px 16px;text-align:center;font-size:14px}
code{background:var(--chip);padding:1px 6px;border-radius:5px}
@media (max-width:620px){.top{flex-direction:column}.acts{flex-wrap:wrap}}
</style></head><body><main>
<h1>Listings to review</h1><p class="sub">Nothing is submitted until you approve it and run <code>./apply.sh</code>.</p>
<nav id="tabs"></nav><div id="list"></div></main><div class="bar" id="bar"></div>
<script>
const TABS=[["pending","Waiting on you"],["approved","Approved"],["by_hand","Apply by hand"],["submitted","Submitted"],["needs_human","Needs you"],["rejected","Rejected"],["skipped","Skipped"]];
let tab="pending",data=[];
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
async function load(){data=(await (await fetch("api/listings")).json()).listings;render()}
async function act(id,status){await fetch("api/set",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({id,status})});load()}
function render(){
 const n=s=>data.filter(x=>x.status===s).length;
 document.getElementById("tabs").innerHTML=TABS.map(([k,l])=>`<button class="${k===tab?"on":""}" onclick="tab='${k}';render()">${l} · ${n(k)}</button>`).join("");
 const xs=data.filter(x=>x.status===tab);
 document.getElementById("list").innerHTML=xs.length?xs.map(x=>`<div class="card"><div class="top"><div>
  <div class="co">${esc(x.company)}</div><div class="ti">${esc(x.title)}</div>
  <div class="meta">${["location","comp","ats","source"].filter(k=>x[k]).map(k=>`<span>${esc(x[k])}</span>`).join("")}</div>
  ${x.why?`<p class="why">${esc(x.why)}</p>`:""}${x.flags?`<p class="flags">⚠ ${esc(x.flags)}</p>`:""}${x.note?`<p class="why"><b>Note:</b> ${esc(x.note)}</p>`:""}
 </div><div class="acts"><a href="${esc(x.url)}" target="_blank" rel="noopener noreferrer">Open posting</a>
  ${x.status==="pending"?`<button class="yes" onclick="act('${x.id}','approved')">Approve</button><button class="nono" onclick="act('${x.id}','rejected')">Reject</button>`:""}
  ${["approved","rejected"].includes(x.status)?`<button onclick="act('${x.id}','pending')">Undo</button>`:""}
 </div></div></div>`).join(""):`<div class="empty">Nothing here.</div>`;
 const a=n("approved");
 document.getElementById("bar").innerHTML=a?`<b>${a}</b> approved. In Terminal, run <code>./apply.sh</code> to submit ${a===1?"it":"them"}.`:`${n("pending")} waiting on you. Approve the ones you want, then run <code>./apply.sh</code>.`;
}
load();
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    token = ''

    def log_message(self, *a):
        pass

    def _ok(self, body, ctype='application/json'):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(200)
        self.send_header('content-type', ctype + '; charset=utf-8')
        self.send_header('cache-control', 'no-store')
        self.end_headers()
        self.wfile.write(b)

    def _authed(self):
        return self.path.startswith(f'/{self.token}/')

    def do_GET(self):
        if not self._authed():
            self.send_error(404); return
        sub = self.path[len(self.token) + 2:]
        if sub in ('', 'index.html'):
            self._ok(PAGE, 'text/html')
        elif sub == 'api/listings':
            self._ok(json.dumps(load()))
        else:
            self.send_error(404)

    def do_POST(self):
        if not self._authed() or self.path[len(self.token) + 2:] != 'api/set':
            self.send_error(404); return
        try:
            b = json.loads(self.rfile.read(int(self.headers.get('content-length', 0)) or 0))
            if b.get('status') not in USER_SETTABLE:
                raise ValueError
            set_status([str(b['id'])], b['status'])
            self._ok('{"ok":true}')
        except (ValueError, KeyError, SystemExit):
            self.send_error(400)


def cmd_serve(a):
    import secrets
    H.token = secrets.token_urlsafe(12)  # the page is only reachable with this path, so other local pages cannot drive it
    srv = ThreadingHTTPServer(('127.0.0.1', a.port), H)
    url = f'http://127.0.0.1:{srv.server_address[1]}/{H.token}/'
    c = counts()
    print(f'{c.get("pending", 0)} waiting on you, {c.get("approved", 0)} approved.')
    print(f'Review page: {url}')
    print('Leave this window open while you review. Press Ctrl+C when done, then run ./apply.sh.', flush=True)
    if not a.no_open:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        c = counts()
        print(f'\nClosed. {c.get("approved", 0)} approved and waiting. Run ./apply.sh to submit them.')


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest='cmd')
    sv = s.add_parser('serve'); sv.add_argument('--port', type=int, default=0); sv.add_argument('--no-open', action='store_true')
    s.add_parser('cli')
    ls = s.add_parser('list'); ls.add_argument('--status', choices=STATUSES); ls.add_argument('--json', action='store_true'); ls.add_argument('-v', '--verbose', action='store_true')
    for n in ('approve', 'reject', 'reset'):
        s.add_parser(n).add_argument('ids', nargs='+')
    ad = s.add_parser('add')
    for f in ('company', 'title', 'url'):
        ad.add_argument('--' + f, required=True)
    for f in ('location', 'comp', 'ats', 'why', 'flags', 'source'):
        ad.add_argument('--' + f, default='')
    ad.add_argument('--by-hand', action='store_true')
    ap = s.add_parser('approved'); ap.add_argument('--json', action='store_true')
    mk = s.add_parser('mark'); mk.add_argument('id'); mk.add_argument('status', choices=AGENT_SETTABLE); mk.add_argument('--note')
    s.add_parser('hosts')
    s.add_parser('count')
    a = p.parse_args()

    if a.cmd in (None, 'serve'):
        if a.cmd is None:
            a.port, a.no_open = 0, False
        cmd_serve(a)
    elif a.cmd == 'cli': cmd_cli(a)
    elif a.cmd == 'list': cmd_list(a)
    elif a.cmd == 'approve': set_status(a.ids, 'approved')
    elif a.cmd == 'reject': set_status(a.ids, 'rejected')
    elif a.cmd == 'reset': set_status(a.ids, 'pending')
    elif a.cmd == 'add': cmd_add(a)
    elif a.cmd == 'approved':
        xs = approved()
        print(json.dumps(xs, indent=2, ensure_ascii=False) if a.json else '\n'.join(row(x) + '\n          ' + x['url'] for x in xs) or '(none approved)')
    elif a.cmd == 'mark': set_status([a.id], a.status, a.note, who='agent')
    elif a.cmd == 'hosts': cmd_hosts(a)
    elif a.cmd == 'count': print(json.dumps(counts()))


if __name__ == '__main__':
    main()
