#!/bin/bash
# PreToolUse guard for the browser: enforces the approval gate in code, not just in the prompt.
#
#   PHM_PHASE=find   (./find.sh)   every Claude-in-Chrome tool is blocked. The finder only reads public
#                                  board APIs from the shell; it never opens an application form.
#   PHM_PHASE=apply  (./apply.sh)  `navigate` is allowed only to hosts of listings YOU approved in
#                                  state/review.json (plus their subdomains). Anything else is blocked.
#   unset            (an interactive session you opened yourself) no extra rule; you are watching.
#
# Policy, not a sandbox: it stops the agent from wandering onto a posting you never approved.
input=$(cat)
phase="${PHM_PHASE:-}"
[ -z "$phase" ] && exit 0

tool=$(printf '%s' "$input" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("tool_name",""))' 2>/dev/null)
case "$tool" in mcp__claude-in-chrome__*) ;; *) exit 0 ;; esac

if [ "$phase" = "find" ]; then
  echo "Blocked by approval-gate: this is the FIND phase. Do not open a browser. Vet listings from the shell and record them with scripts/review.py add." >&2
  exit 2
fi

if [ "$phase" = "apply" ]; then
  # Only navigation chooses where the agent goes. Clicks/typing on a page it reached legitimately are fine.
  case "$tool" in mcp__claude-in-chrome__navigate|mcp__claude-in-chrome__browser_batch) ;; *) exit 0 ;; esac
  root="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
  printf '%s' "$input" | python3 -I -c '
import json, sys, urllib.parse
root = sys.argv[1]
data = json.load(sys.stdin)
ti = data.get("tool_input") or {}
urls = []
def walk(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "url" and isinstance(v, str): urls.append(v)
            else: walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(ti)
try:
    ls = json.load(open(root + "/state/review.json")).get("listings", [])
except Exception:
    ls = []
# Shared ATS hosts serve every company, so on those the company slug must match too:
# approving one Ashby posting must not open every Ashby board.
SHARED = {"jobs.ashbyhq.com", "boards.greenhouse.io", "job-boards.greenhouse.io", "jobs.lever.co",
          "apply.workable.com", "jobs.smartrecruiters.com", "careers.smartrecruiters.com"}
def key(u):
    p = urllib.parse.urlsplit(u if "://" in u else "https://" + u)
    h = (p.hostname or "").lower()
    seg = p.path.strip("/").split("/")[0].lower() if p.path.strip("/") else ""
    if seg == "embed":
        seg = (urllib.parse.parse_qs(p.query).get("for") or [""])[0].lower()
    return h, seg
ok = {key(x["url"]) for x in ls if x.get("status") == "approved"}
GH = {"boards.greenhouse.io", "job-boards.greenhouse.io"}  # Greenhouse redirects between these two
def same_shared(h, ah):
    return h == ah or (h in GH and ah in GH)
def allowed(u):
    if u.startswith(("about:", "chrome:")) or u in ("back", "forward"): return True
    h, seg = key(u)
    for ah, aseg in ok:
        if h in SHARED or ah in SHARED:
            if same_shared(h, ah) and seg == aseg: return True
        elif h == ah or h.endswith("." + ah) or (ah.endswith("." + h) and h.count(".") >= 1):
            return True  # the company own careers domain and its subdomains (apply.x.com, x.wd5.myworkdayjobs.com)
    return False
bad = [u for u in urls if not allowed(u)]
if bad:
    sys.stderr.write("Blocked by approval-gate: " + ", ".join(bad) + " is not the host of any listing the user approved. "
                     "Approved: " + (", ".join(sorted(h + ("/" + g if h in SHARED else "") for h, g in ok)) or "none") + ". Apply only to approved listings.\n")
    sys.exit(2)
' "$root"
  rc=$?
  # Any failure (bad JSON, a crash) blocks. Exit 1 would let the call through, so fail closed with 2.
  [ "$rc" -eq 0 ] && exit 0
  [ "$rc" -eq 2 ] || echo "Blocked by approval-gate: could not verify this navigation against state/review.json." >&2
  exit 2
fi
exit 0
