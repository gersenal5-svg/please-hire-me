#!/usr/bin/env bash
# please-hire-me (approval fork) — APPLY phase. Submits ONLY the listings you approved in ./review.sh.
#
#   ./apply.sh                  submit every approved listing (headless, like the original run.sh)
#   ./apply.sh 2                submit at most 2 of them this run
#   ./apply.sh --checkpoint     opens Claude Code so you can watch; it stops before EVERY Submit click
#                               and waits for your yes. Use this until you trust the form-filling.
#
# The agent is handed the approved list and nothing else. A hook (.claude/hooks/approval-gate.sh) also
# blocks the browser from navigating anywhere that is not one of those postings.
set -euo pipefail
cd "$(dirname "$0")"

CHECKPOINT=0; CAP=""
for a in "$@"; do
  case "$a" in
    --checkpoint) CHECKPOINT=1 ;;
    ''|*[!0-9]*) echo "Usage: ./apply.sh [max_applications] [--checkpoint]" >&2; exit 2 ;;
    *) CAP="$a" ;;
  esac
done

N_APPROVED="$(python3 -c 'import json,sys;print(json.loads(sys.argv[1]).get("approved",0))' "$(python3 scripts/review.py count)")"
if [ "$N_APPROVED" -eq 0 ]; then
  echo "Nothing is approved yet. Run ./review.sh, approve the listings you want, then run ./apply.sh again."
  exit 0
fi

source scripts/_launch_common.sh

APPROVED_JSON="$(python3 scripts/review.py approved --json | python3 -c '
import json, sys
print(json.dumps([{k: x.get(k, "") for k in ("id", "company", "title", "url", "location", "comp", "flags")} for x in json.load(sys.stdin)], ensure_ascii=False, indent=1))')"
export MAX_OVERRIDE="${CAP:-$N_APPROVED}"
RULES="$(python3 scripts/run_rules.py apply)"

if [ "$CHECKPOINT" = "1" ]; then
  SUBMIT_RULE="CHECKPOINT MODE, the user is watching this session: for each listing, fill every field, verify it, write the log entry and the per-application doc, take a screenshot, then STOP BEFORE CLICKING SUBMIT. Show the user every question and answer and ask 'Submit this one? (yes/no)'. Submit only on an explicit yes. On no, close the tab, run python3 scripts/review.py mark <id> skipped --note 'declined at checkpoint', and move to the next."
else
  SUBMIT_RULE="The user already approved every listing below, so submit each one that still passes the checks without asking again."
fi

PROMPT="APPLY PHASE of the job application run in $(pwd). This is a fresh session: derive all state from repository files.

THE USER APPROVED EXACTLY THESE LISTINGS, AND YOU MAY APPLY ONLY TO THESE. Do not source, do not run any sweep, do not open any other posting, even one that looks better. A hook blocks navigation to any other site.
${APPROVED_JSON}

Read and follow: CLAUDE.md, config/settings.json, config/profile.json, config/answers.md, config/spec.md, config/documents.md, state/status.md, logs/applications-log.md.

RUN CONFIG (from config/settings.json, obey exactly): ${RULES}

${SUBMIT_RULE}

FOR EACH APPROVED LISTING, in order: re-run the CLAUDE.md duplicate rules and ./scripts/dupe_check.sh \"<Company>\" (things change between approval and now); confirm the posting is still live. Then fill and submit it per CLAUDE.md 'THE WORKING METHOD'. Afterwards record the outcome, always by id:
  submitted                       -> python3 scripts/review.py mark <id> submitted --note '<screenshot path>'
  blocked on a missing fact       -> python3 scripts/review.py mark <id> needs_human --note '<what is needed>'
  dead, duplicate, now ineligible -> python3 scripts/review.py mark <id> skipped --note '<reason>'
A listing you did not reach this run (the cap, or one-per-company-per-run) stays approved: do not mark it.

METHOD: use the connected real Chrome through the Claude-in-Chrome extension and fill every field with trusted computer-tool input. Use file_upload for the resume and transcript. At the start, call tabs_context_mcp and close ONLY leftover job-application tabs inside your own MCP tab group; NEVER close, read, or navigate any tab that is not listed in your group. Do the whole run in one reused tab. If the tab group drops mid-fill, abandon the half-filled form and restart that listing from a clean tab. Before exiting, close EVERY tab in your group with tabs_close_mcp and confirm tabs_context_mcp answers that no tab group exists.

END OF RUN: update the per-application docs, logs/applications-log.md (also mark any matching data/queue.md row), and add an APPLY status block at the top of state/status.md. If Chrome is disconnected, log it and exit without marking anything."

echo "Applying to up to $MAX_OVERRIDE of $N_APPROVED approved listing(s)$([ "$CHECKPOINT" = 1 ] && echo ', stopping before each submit')."
if [ "$CHECKPOINT" = "1" ]; then
  # You are in the session, so Claude Code asks you before each tool it has not been allowed yet.
  PHM_PHASE=apply "$CLAUDE_BIN" --chrome "$PROMPT"
else
  # Headless, same as the original run.sh: nobody is there to answer permission prompts. The approval
  # list in the prompt plus the approval-gate hook are what keep it on the listings you chose.
  PHM_PHASE=apply "$CLAUDE_BIN" -p --chrome --no-session-persistence --dangerously-skip-permissions "$PROMPT"
fi
echo
python3 scripts/review.py list | grep -E 'submitted|needs_human|skipped|approved' || true
