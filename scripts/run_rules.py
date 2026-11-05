#!/usr/bin/env python3
"""Turn config/settings.json into the sentences the agent must obey this run.

    python3 scripts/run_rules.py find    # targeting + eligibility only (the finder never submits)
    python3 scripts/run_rules.py apply   # everything, including the submit cap and document rules
MAX_OVERRIDE in the environment overrides run.max_applications_per_run. Shared by find.sh and apply.sh.
"""
import os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json, os, sys
s = json.load(open('config/settings.json'))
run, t, el = s.get('run', {}), s.get('targets', {}), s.get('eligibility', {})
ch, sf, docs = s.get('channels', {}), s.get('safety', {}), s.get('documents', {})
out = []
MODE = sys.argv[1] if len(sys.argv) > 1 else 'apply'
APPLY = MODE == 'apply'
mx = os.environ.get('MAX_OVERRIDE') or run.get('max_applications_per_run', 3)
if APPLY:
    out.append(f"Submit at most {mx} new applications this run, then exit.")
if APPLY and run.get('dry_run'):
    out.append("DRY RUN IS ON: fill every field, verify it, screenshot it, write the log entry and "
               "the per-application doc marked DRY RUN, then close the tab WITHOUT clicking submit. "
               "Do not submit anything this run under any circumstance.")
if APPLY and run.get('one_application_per_company_per_run', True):
    out.append("One application per company per run.")
if APPLY and run.get('same_day_company_freeze', True):
    out.append("Never open a second req at a company that already received an application today; "
               "check the Date applied line in the matching applications/*.md file.")
if t.get('roles'):
    out.append("Target roles: " + ", ".join(t['roles']) + ".")
if t.get('seniority'):
    out.append("Seniority in scope: " + ", ".join(t['seniority']) + ".")
if t.get('max_years_experience_required') is not None:
    out.append(f"Skip any posting requiring more than {t['max_years_experience_required']} "
               "year(s) of professional experience; that is a hard eligibility mismatch, not a "
               "needs-human block.")
if t.get('locations'):
    out.append("Locations in scope: " + ", ".join(t['locations']) + ".")
if t.get('min_annual_comp_usd'):
    line = f"For FULL-TIME roles, apply only when credible annual compensation is at least ${t['min_annual_comp_usd']:,}"
    if t.get('prioritize_above_usd'):
        line += f", prioritizing roles above ${t['prioritize_above_usd']:,}"
    out.append(line + ".")
if 'internship' in [x.lower() for x in t.get('seniority', [])]:
    hourly = t.get('internship_min_hourly_usd') or 0
    if hourly:
        out.append(f"INTERNSHIPS are in scope and are judged separately: require at least ${hourly}/hour "
                   "(annualize a monthly or weekly stipend to compare). NEVER skip an internship for "
                   "failing the full-time annual floor; that floor does not apply to internships.")
    else:
        out.append("INTERNSHIPS are in scope and the full-time annual compensation floor does NOT apply "
                   "to them. Internships post hourly or monthly pay; judge them on the quality bar "
                   "below, not on an annual number, and never skip one for lacking an annual band.")
if t.get('count_equity_toward_comp') is False:
    out.append("Do not count equity with a vesting cliff toward the compensation floor.")
if t.get('prestige_note'):
    out.append("Quality bar, in the user's own words: " + t['prestige_note'])
if t.get('priority_companies'):
    out.append("Prioritize these companies when they have an eligible opening: "
               + ", ".join(t['priority_companies']) + ".")
if t.get('skip_companies'):
    out.append("NEVER apply to: " + ", ".join(t['skip_companies']) + ".")
tp = run.get('interview_tracker_path')
if tp:
    import subprocess, sys
    r = subprocess.run([sys.executable, 'scripts/tracker_companies.py'], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(r.stderr.strip() or 'interview tracker unreadable')
    cos = [c for c in r.stdout.splitlines() if c.strip()]
    out.append("INTERVIEW TRACKER (the user's own file, read at launch): the user has an OA, an interview, "
               "an open recruiter thread, or a rejection at EVERY one of these companies, so each is a HARD "
               "SKIP that overrides the queue, the lifetime counter, and any fresh posting: "
               + ", ".join(cos) + ". Match on the first word of the name (\"Acme Tech\" covers "
               "Acme Technologies LLC). Before opening ANY tab run ./scripts/dupe_check.sh \"<Company>\" "
               "and treat exit 3 as a hard skip.")
for n in t.get('skip_notes', []):
    out.append(n)
if el.get('needs_visa_sponsorship'):
    out.append("The user needs visa sponsorship. Skip employers that state they do not sponsor, and "
               "skip US-citizen, US-person, security-clearance, and ITAR roles.")
if el.get('us_person_only_roles_ok') is False and not el.get('needs_visa_sponsorship'):
    out.append("Skip US-person-only, clearance, and ITAR roles.")
if el.get('graduation'):
    out.append(f"Graduation is {el['graduation']}. Never misstate it to fit a posting's window; if a "
               "posting hard-requires a window that excludes it, skip the posting.")
if el.get('earliest_start') or el.get('latest_start'):
    out.append(f"Start window: {el.get('earliest_start','')} to {el.get('latest_start','')}.")
if ch.get('allowed_ats'):
    out.append("Apply only on: " + ", ".join(ch['allowed_ats']) + ".")
if ch.get('blocked_aggregators'):
    out.append("Never apply through: " + ", ".join(ch['blocked_aggregators']) + ".")
if sf.get('never_create_accounts', True):
    out.append("Never create accounts or enter passwords.")
if sf.get('never_solve_interactive_captcha', True):
    out.append("Never solve interactive CAPTCHA challenges; log NEEDS HUMAN instead. Passive "
               "reCAPTCHA v3 with no challenge is fine to submit through with trusted input.")
if sf.get('never_fabricate_a_fact', True):
    out.append("Never fabricate a fact. A required answer with no preset in config/answers.md or "
               "config/profile.json is NEEDS HUMAN, not a guess.")
if APPLY and sf.get('screenshot_every_submit', True):
    out.append("Save a confirmation screenshot as JPG directly under screenshots/ after each submit. "
               "Never record or export GIFs and never touch ~/Downloads.")
if APPLY and sf.get('require_log_before_submit', True):
    out.append("Before clicking submit, append the full question-and-answer log to "
               "logs/applications-log.md and write applications/<company>-<role>.md with every "
               "question, every answer, the URL, and today's date.")
if not APPLY:
    pass
elif docs.get('cover_letter', True):
    out.append("COVER LETTERS ARE ON: when a form has a cover-letter field (text box or upload, required or "
               "optional), draft one from the fact sheet following config/documents.md and run "
               "scripts/app_docs.py lint-letter until it prints OK. No field, no letter. Never draft one "
               "where the form forbids AI.")
else:
    out.append("Cover letters are OFF: draft none; leave optional cover-letter fields blank.")
if not APPLY:
    pass
elif docs.get('tailor_resume', True):
    out.append("RESUME TAILORING IS ON: per application, follow config/documents.md: save the posting, run "
               "scripts/app_docs.py keywords, tailor a copy of profile.json resume_tailor_base, pass "
               "check-resume --jd and render-resume, look at the PDF, and upload it. Never add a fact. "
               "If resume_tailor_base is missing, upload the default resume.")
else:
    out.append("Resume tailoring is OFF: upload the default resume from profile.json unchanged.")
print(" ".join(out))
