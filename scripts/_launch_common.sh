# Shared by find.sh and apply.sh: config checks, the claude binary, the tracker gate, and the run lock.
# Sourced, not executed. Expects to run from the repo root.

for f in config/settings.json config/profile.json config/answers.md; do
  [ -f "$f" ] || { echo "ERROR: $f is missing. Run ./setup.sh first." >&2; exit 1; }
done

# launchd runs with a minimal PATH that lacks the user's shell setup, so resolve
# the claude binary explicitly. Prefer the stable ~/.local/bin symlink, then PATH.
# ~/.local/bin also holds the tectonic and pdftotext links that resume tailoring needs.
export PATH="$HOME/.local/bin:$PATH"
if [ -x "$HOME/.local/bin/claude" ]; then
  CLAUDE_BIN="$HOME/.local/bin/claude"
elif command -v claude >/dev/null 2>&1; then
  CLAUDE_BIN="$(command -v claude)"
else
  echo "ERROR: claude binary not found (checked ~/.local/bin/claude and PATH)." >&2
  exit 127
fi

# The user's interview tracker (run.interview_tracker_path) is a hard-skip source. If it is set but
# unreadable (iCloud evicted it, path moved), REFUSE TO RUN.
TRACKER_PATH="$(python3 -c 'import json;print(json.load(open("config/settings.json")).get("run",{}).get("interview_tracker_path",""))' 2>/dev/null || true)"
if [ -n "$TRACKER_PATH" ] && [ ! -r "$TRACKER_PATH" ]; then
  echo "ERROR: run.interview_tracker_path is set but not readable: $TRACKER_PATH" >&2
  echo "       Fix the path in config/settings.json (or download the file from iCloud) and rerun." >&2
  exit 1
fi

# One run at a time, find or apply: both write state/ and the logs.
LOCK_DIR=".hourly-run.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  stale_pid="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"
  if [ -n "$stale_pid" ] && kill -0 "$stale_pid" 2>/dev/null; then
    printf 'Another run (pid %s) is active. Try again when it finishes.\n' "$stale_pid"
    exit 0
  fi
  printf 'Removing stale lock (pid %s no longer running).\n' "${stale_pid:-unknown}"
  rm -rf "$LOCK_DIR"
  mkdir "$LOCK_DIR" || { printf 'Could not acquire lock.\n'; exit 0; }
fi
echo "$$" > "$LOCK_DIR/pid"
trap 'rm -rf "$LOCK_DIR" 2>/dev/null || true' EXIT
mkdir -p state logs
