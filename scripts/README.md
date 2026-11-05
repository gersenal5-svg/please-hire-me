# scripts/

| File | What |
|---|---|
| `review.py` | The approval list (`state/review.json`). `./review.sh` runs its review page; the find phase calls `add`, the apply phase calls `approved` and `mark`. Only you can approve or reject. |
| `run_rules.py` | Turns `config/settings.json` into the rules sentence `find.sh` and `apply.sh` put in the prompt (`find` mode leaves out submit and document rules). |
| `_launch_common.sh` | Shared launcher preamble: config check, the `claude` binary, the interview-tracker gate, the run lock. |
| `schedule.sh` | Install, check, or remove the recurring FIND run (it never submits). Reads `schedule.frequency` from `config/settings.json`. Uses launchd on macOS, cron elsewhere. |
| `scheduled_run.sh` | What the scheduler calls. One bounded `./find.sh` run, everything appended to `logs/scheduled-run.log`. |
| `fetch_hn_hiring.sh` | Pull the current HN "Who is hiring?" thread as plain text, one posting per block. Best source of startups that never hit a job board. |
| `probe_boards.sh` | Re-verify every slug in `data/slug-candidates.txt` and rewrite `data/boards.md`. Run before a big sourcing session. |
| `render_boards.py` | Turns probed payloads into `data/boards.md`. Called by `probe_boards.sh`. |
| `app_docs.py` | Tailored resumes and cover letters, built with tectonic. `verify-conversion` proves a PDF-to-LaTeX transcription kept every word. `keywords` sorts a posting's terms into on-resume, fact-sheet-only, and gaps. `check-resume` rejects invented facts and bad escaping. `render-resume` fails on overflow, text past the margin, dropped text, and ATS-hostile ligatures. `lint-letter` and `render-letter` do the same for letters. Rules in `config/documents.md`. |
| `resume_server.py` | Legacy localhost helper for resume upload. Only needed if `file_upload` is unavailable. |
| *(your own)* | Set `integrations.post_run_script` in `config/settings.json` to a python3 script and it runs after every run. Nothing ships here by default. |
