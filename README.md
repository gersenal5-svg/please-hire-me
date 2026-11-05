<div align="center">

# please-hire-me — approval fork

**An agent that finds real job openings, shows them to you, and applies only to the ones you approve.**

<sub>Fork of [igueu16/please-hire-me](https://github.com/igueu16/please-hire-me). The upstream agent finds and
submits in one autonomous run. This fork splits that into **find → you review → apply**, so nothing is
ever sent without your yes. See [What this fork changes](#what-this-fork-changes).</sub>

[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-black.svg)](CONTRIBUTING.md)
[![Runs on Claude Code](https://img.shields.io/badge/runs%20on-Claude%20Code-black.svg)](https://claude.com/claude-code)
[![macOS | Linux](https://img.shields.io/badge/macOS-%7C%20Linux-black.svg)](#quick-start)

You set it up once, in one conversation of about five minutes, and it writes your config from your
resume. After that it finds live openings, internships and new-grad roles alike, and puts them on a
review list. You approve the ones you want; then it fills the company's own Greenhouse / Lever / Ashby
form field by field in your real Chrome, and submits those. Every answer is logged before it clicks, every submit is screenshotted, and it never
invents a fact about you.

</div>

---

## TL;DR

1. **Set up once (about 5 minutes).** Open Claude Code in this folder and say "set me up". It reads your
   resume, asks one list of questions, and writes your private config: profile, answers and targets.
   None of that is ever committed.
2. **It finds roles.** Sweeps public company job boards (Greenhouse, Ashby, Lever, Workable), VC
   portfolio boards and LinkedIn's public search, then keeps only postings that pass your filters:
   title, location, pay floor, years of experience and your own quality bar.
3. **You approve.** `./review.sh` opens the list in your browser: company, role, pay, why it matched, and
   anything to watch for. Approve or reject each one. Nothing is applied to until you do.
4. **It applies on the company's own form, approved listings only.** For each one you approved it tailors a one-page resume to the posting
   (facts from your resume only), fills the real application in your Chrome with real clicks and
   keystrokes, logs every answer, submits, and screenshots the confirmation. It never invents a fact,
   never creates an account, and never uses Easy Apply.
5. **Workday portals:** you sign in, and the bundled Chrome extension fills the form. You click Submit.
6. **Recruiter outreach:** it sorts your applications into tiers, finds a recruiter or hiring manager at
   each company, and drafts a short email into your Gmail Drafts. Nothing sends until you approve the batch.

> **Recommended: connect [Apollo](https://www.apollo.io) for email outreach.** A short note to a
> recruiter often gets a reply when the application alone sits in a queue, and Apollo is how the
> agent finds the right person and their work email. Searching people is free; revealing an email
> costs one credit. Create an account, copy your API key, and store it in **your own Terminal**
> (never paste it into the chat):
> ```bash
> security add-generic-password -U -s apollo-api-key -a you -w
> ```
> Check it with `python3 scripts/apollo.py health`. Details under
> [Optional add-ons](#optional-add-ons-each-needs-one-step-from-you), item 6.

## Quick start

**You need:** [Claude Code](https://claude.com/claude-code) signed in · Chrome with the
[Claude in Chrome](https://claude.ai/chrome) extension on the same account · your resume as a PDF.

<details>
<summary>Setting up the Chrome extension</summary>

Three steps, all manual, none of them scriptable. Chrome requires a real user gesture to install an
extension and to grant it a site, which is the correct behaviour and not something this repo should
try to work around.

1. Install [Claude in Chrome](https://claude.ai/chrome).
2. Sign in with the **same Anthropic account** as your Claude Code session. A mismatch looks exactly
   like the extension not being installed.
3. Let it access the ATS domains when it asks. Access is granted per site.

Setup checks this for you before the first application and tells you which of the three is missing,
so you are not debugging it halfway through a filled form.

</details>

```bash
git clone https://github.com/igueu16/please-hire-me.git
cd please-hire-me
```

Open the repo in Claude Code and say *"set me up"*. Setup is one conversation, about five minutes,
and Claude does the typing:

1. It asks for your resume and reads it.
2. It shows you every value it pulled out so you can correct what is wrong.
3. It asks **one list** of the questions a resume cannot answer, all at once, with the default it
   will use for anything you skip. Work authorization, start date, what counts as a good job to you.
4. It drafts your answer templates from your real work and reads them back for you to approve.

Then it writes your three config files. It never invents a fact about you, and it does not open a
browser or apply to anything during setup.

<details>
<summary>Prefer a terminal wizard?</summary>

`./setup.sh` asks the questions every form asks and writes your config in about two minutes. It
leaves `config/answers.md` as a blank template for you to fill in yourself, which takes about
twenty minutes and is the step that decides whether the agent flies or stalls at every "why do you
want this role?". Letting Claude draft it from your resume is why the guided path is the default.

</details>

**Run it, in three steps:**

```bash
./find.sh                  # 1. find and vet new listings (10-20 min). Never submits anything.
./review.sh                # 2. a page opens in your browser: Approve or Reject each listing
./apply.sh                 # 3. submit ONLY the listings you approved
```

Variations:

```bash
./review.sh --cli          # review in the terminal instead (a = approve, r = reject, o = open the posting)
./apply.sh 2               # submit at most 2 of your approved listings this time
./apply.sh --checkpoint    # watch it work; it also stops before EVERY Submit click and waits for your yes
python3 scripts/review.py list -v      # everything it has found, with status
```

## What this fork changes

| | Upstream | This fork |
|---|---|---|
| Finding | `./run.sh` finds and submits in one run | `./find.sh` finds and vets, then stops |
| Your say | none after setup | every listing waits on your Approve in `./review.sh` |
| Submitting | whatever the agent judged good enough | only what you approved, via `./apply.sh` |
| Schedule | submits on its own every N hours | only finds; you get a macOS notification when listings are waiting |
| `./run.sh` | the autonomous run | an alias for `./find.sh`, so old habits can never auto-submit |

**How the gate is enforced, not just requested.** The approval list lives in `state/review.json`
(gitignored, like everything about you). Statuses: `pending` → you set `approved` or `rejected` →
`./apply.sh` sets `submitted`, `needs_human` or `skipped`. The agent can only mark listings you
approved, and it cannot approve anything itself. On top of the instructions in the prompt, a Claude
Code hook (`.claude/hooks/approval-gate.sh`) blocks the browser entirely during `./find.sh`, and
during `./apply.sh` blocks navigation to any site that is not one of your approved postings (on shared
job-board hosts like `jobs.ashbyhq.com`, the company slug must match too). A listing you rejected is
remembered and never shown again.

**Two levels of approval.** `./apply.sh` treats your Approve as the go-ahead and submits headless.
If you also want to read every filled-in answer before it goes, use `./apply.sh --checkpoint`.

---

## What you give it

A missing fact becomes a question for you, never a guess. Three files decide everything, and setup
writes all three for you:

| File | What goes in it | Where it comes from |
|---|---|---|
| `config/profile.json` | Name, contact, school, degree, graduation, GPA, visa status, links, resume path. | read off your resume, then you correct it |
| `config/answers.md` | Free-text templates, your fact sheet, presets for salary, start date, EEO. **The one that matters.** | drafted from your resume, then you approve it |
| `config/settings.json` | Cap per run, frequency, and what counts as a target: roles, locations, comp floor, skip list, your quality bar. | your answers to the question list |

Each has a `.example` twin showing exactly what belongs there. Your real files are gitignored, so
nothing about you leaves your machine. Edit any of them by hand later; the agent rereads them every
run.

## Settings

One file, `config/settings.json`. The launcher turns it into the instructions the agent must obey.

| Key | Does what |
|---|---|
| `run.max_applications_per_run` | Hard cap per run. Default 3. |
| `run.same_day_company_freeze` | Never open a second role at a company you applied to today. |
| `schedule.frequency` | `manual`, `hourly`, `every-2-hours`, `every-3-hours`, `every-6-hours`, `daily`, `weekdays`. |
| `targets.roles` | Titles to look for. |
| `targets.max_years_experience_required` | Anything above this is skipped as a hard mismatch. |
| `targets.locations` | Cities, plus `Remote (US)` if you want remote. |
| `targets.min_annual_comp_usd` | Compensation floor for **full-time** roles. |
| `targets.internship_min_hourly_usd` | Hourly floor for **internships**, which post hourly pay and would otherwise fail an annual floor. `0` means judge them on the quality bar alone. |
| `targets.prestige_note` | Your quality bar in plain English, used when a posting lists no salary. |
| `targets.skip_companies` | Never apply here. |
| `eligibility.needs_visa_sponsorship` | Skips non-sponsors, ITAR, and clearance roles. |
| `eligibility.graduation` | Skips postings whose graduation window excludes you. |
| `run.max_applications_per_company_lifetime` | Stop at this many applications to one company, ever. Default 2. |
| `run.interview_tracker_path` | Your interview note; every company in it is skipped. See add-ons. |
| `channels.signed_in_portals` | Portals where you are signed in and the agent may apply. See add-ons. |
| `broker.*` | Gmail account for the emailed-code add-on. |
| `documents.cover_letter` | Draft a cover letter when the form has a field for one. On by default. See below. |
| `documents.tailor_resume` | Upload a resume reordered and trimmed for each posting. On by default. See below. |
| `safety.*` | No accounts, no CAPTCHA solving, no fabricated facts, screenshot every submit. |
| `targets.title_include_regex` / `title_exclude_regex` | Override which titles the board sweep keeps. Empty keeps the software-engineering default; set them for product, ops, analytics or any other search. |
| `targets.linkedin_query` / `linkedin_title_regex` / `linkedin_locations` | Your own LinkedIn search for `scripts/linkedin_sweep.py` (a source only; the agent never signs in). |
| `outreach.*` / `outreach_senders` | Recruiter-email add-on: tracker file, which companies count as Tier A, sending inboxes. See add-ons. |
| `documents.export_dir` | Where tailored resumes are copied for applying by hand. Default `~/Desktop/custom resume`. |

### Cover letters and tailored resumes

Both are on unless you set them to `false` under `documents` in `config/settings.json`.

**Cover letters.** When a form has a cover-letter field, the agent drafts one of 150 to 250
words. Research since LLMs arrived shows that matching the posting's words no longer sets a letter
apart, so the letter is built from three other things:
- a specific detail from the company's own site, not a paraphrase of the posting
- one story from the "Stories" section of your `answers.md` that your resume doesn't tell
- what you'd want to work on first

Every claim traces to your files. `lint-letter` rejects em dashes, stock phrases recruiters flag as
machine-written, and unsourced numbers. It also warns when a sentence restates your resume or
echoes the posting. The letter goes into the form's box or upload, and a copy stays in
`applications/files/`. No field means no letter.

**Tailored resumes.** Setup converts your PDF into LaTeX using
[Jake's Resume](https://github.com/jakegut/resume), the template most software resumes on Overleaf
use. It checks the conversion word by word against your original. If you already keep a `.tex`,
point `resume_tailor_base` in `config/profile.json` at it instead. Per posting, the agent:

- sorts the posting's terms into what you have, what your fact sheet supports, and the gaps
- puts your most relevant work first
- rewrites bullets result-first with your real numbers, in the posting's vocabulary
- cuts what doesn't matter for that role
- builds a one-page PDF

It never adds a skill, a number, or a title. `check-resume` fails on any term or number that is in
neither your resume nor your fact sheet. `render-resume` fails on text past the margin, page
overflow, text dropped by a bad escape, and ligature glyphs that ATS parsers misread. Needs
`brew install tectonic poppler`, which setup offers to run.

Rules for both: [`config/documents.md`](config/documents.md).

Run the FIND step on a schedule (it never submits; it notifies you when there is something to review):

```bash
./scripts/schedule.sh install        # reads schedule.frequency
./scripts/schedule.sh status         # this checkout, plus every other one on the machine
./scripts/schedule.sh uninstall      # this checkout only
./scripts/schedule.sh uninstall-all  # every please-hire-me job on the machine
```

Each checkout gets its own scheduled job, keyed to its path, so two clones can run on
their own cadences without overwriting each other. `status` shows all of them and marks
which one you are in.

## Optional add-ons (each needs one step from you)

None of these is required. Each unlocks more applications, and each has a step only you can do,
because it involves an account, a password, or your own notes.

**1. Company portals that need an account** (Amazon, Nvidia and other Workday companies, Microsoft,
Apple, Two Sigma, Bloomberg, AMD, Qualcomm...). The agent never creates an account and never logs in.
You sign up or sign in once in Chrome, then add the portal's host to `channels.signed_in_portals`:

```json
"signed_in_portals": ["amazon.jobs", "nvidia.wd5.myworkdayjobs.com", "careers.twosigma.com"]
```

`scripts/portal_sweep.py` lists new postings on these portals every run. If a run finds you signed out,
it logs NEEDS HUMAN with the link instead of logging in. **Workday sessions expire within hours**, so
Workday applications work best in an interactive session right after you sign in. Portals that need
no account at all (Netflix, Millennium, Uber, Renaissance, D. E. Shaw) are applied to directly.

**2. Emailed verification codes.** Some Greenhouse forms email an 8-character code after you click
Submit. Without this add-on that application stops at NEEDS HUMAN. With it, `scripts/code_broker.py`
reads the code from Gmail and pastes it into the page; the agent never sees the code or your password.
It is used only for that post-submit check, never to log in anywhere. Setup, about two minutes:

1. Turn on 2-Step Verification on your Google account, then create an app password at
   <https://myaccount.google.com/apppasswords>.
2. In **your own Terminal** (not through Claude), store it in the macOS Keychain:
   ```bash
   security add-generic-password -s jobapply-gmail-imap -a you@gmail.com -w
   ```
   Paste the app password at `password data for new item:`, press Enter, paste it again at
   `retype password`, press Enter. Nothing shows while you paste; that is normal.
3. Fill the `broker` block in `config/settings.json` (`gmail_account`, and optionally
   `signup_email_pattern` like `you+{tag}@gmail.com`).
4. Check it: `python3 scripts/code_broker.py check` prints `{"status": "ok"}` or says what is missing.

Never paste the app password into a chat. `.claude/hooks/block-secret-read.sh` stops the agent's
shell from reading the Keychain or clipboard, as a guardrail.

**3. Your interview tracker.** If you track interviews in a note (Obsidian or any text file), set
`run.interview_tracker_path` to its path and write each company as a `[[wikilink]]`. Every company in
it becomes a hard skip, so a run never sends a second application to a company where you are mid-loop.

**4. Searching for something other than engineering.** The defaults target new-grad software roles.
For any other search (product, operations, analytics, design...), set `targets.roles`,
`targets.seniority`, `targets.min_annual_comp_usd` and `targets.prestige_note` as usual, then:

```json
"title_include_regex": "product manager|\\bapm\\b|product operations|product analyst",
"title_exclude_regex": "principal|\\bstaff\\b|director|head of|\\bvp\\b|intern",
"linkedin_query": "(\"associate product manager\" OR \"product operations\" OR \"product analyst\")"
```

The onboarding conversation fills these in for you if you tell it what you are looking for.

**5. Workday autofill extension** (`extension/workday-autofill/`). Workday portals need an account, so
the agent cannot apply there. This small Chrome extension does the typing once you are signed in:
contact info, every job from your resume, education, skills ranked by the posting, the Yes/No
questions your profile answers, and the voluntary EEO pages. It never clicks Submit and never ticks
a terms box. Questions it does not know are flagged, and the answer you give is remembered for the
next Workday form.

1. `python3 scripts/workday_ext.py build` writes your profile and base resume into the extension's
   `data/` folder (gitignored).
2. `chrome://extensions` → Developer mode → **Load unpacked** → pick `extension/workday-autofill`.
3. Per posting, optionally `python3 scripts/workday_ext.py add <workday job url>` to tailor a resume for
   it; the extension uploads that one on that posting. Reload the extension after `build` or `add`.
4. Sign in on the Workday portal, open the application, click the extension → **Autofill**. Review every
   page yourself and click Save and Continue / Submit.

Extra jobs that are not on your resume (a fellowship, a board seat) go in `profile.json` as
`extra_experience`, a list of `{company, title, location, start_month, start_year, current,
end_month, end_year, description}`.

**6. Recruiter outreach emails.** After applying, a short note to a recruiter or hiring manager at the
company. The agent drafts; **nothing sends until you approve the batch.**

- `scripts/tier_outreach.py` sorts applications into tiers: A (companies matching `outreach.tier_a_regex`,
  or pay at or above `outreach.tier_a_min_pay_usd`), B (solid fit), C (stretch, no outreach) and R
  (already rejected you, no outreach).
- `scripts/apollo.py` finds recruiters and hiring managers by company domain through the
  [Apollo](https://www.apollo.io) API (searching is free; revealing an email costs one credit). Store
  your key in your own Terminal: `security add-generic-password -U -s apollo-api-key -a you -w`.
- `scripts/imap_draft.py` writes each email into the sending inbox's Drafts, so you can read them in Gmail.
- `scripts/send_batch.py state/send-batch-<date>.txt` sends an approved list over Gmail SMTP, with a gap
  between sends, and marks each one sent in the tracker. `scripts/draft_send.py` refuses to email anyone
  twice.

Sending uses the same Gmail app password as add-on 2. For a second inbox, store its app password under
another Keychain service and list it in `outreach_senders`. Keep a new inbox to about 15 emails a day,
and an established one to about 40, or Gmail will start flagging you as a spammer.

## Why this instead of a one-click apply tool

An internship or new-grad search is 300 forms asking the same 40 questions, 20 minutes each, and
none of that time makes you a better candidate. The postings that pay well rot in about a week, so being slow means
not applying at all.

The tools that promise to fix this apply *through their own portal*, which is the channel recruiters
ignore. This applies on the company's own ATS, the same form you would have filled by hand, with
your real answers.

## How it works

**Real browser, real keystrokes.** ATS forms score behavior with reCAPTCHA v3. Page JavaScript
produces untrusted events and gets flagged as spam; so does a headless or devtools-driven browser.
The agent clicks and types in your normal Chrome the way you would. Not an evasion trick, just the
honest way to operate a browser, which is why submissions land normally.

**It ships with a map.** [`data/boards.md`](data/boards.md) lists 235 Ashby and Greenhouse boards
verified live, with job counts and which ones publish salary bands.
[`data/ats-field-notes.md`](data/ats-field-notes.md) holds what 196 real applications taught it:
which companies rate-limit you per candidate, where seniority hides in body text, which org slugs
are wrong, which postings contain prompt injection aimed at AI readers. Regenerate the board list
any time with `./scripts/probe_boards.sh`.

**Sourcing happens over JSON, not browsers.** Three sweeps run each time: `delta_sweep.py` reads
every known Greenhouse / Ashby / Lever board, `portal_sweep.py` reads company portals (Workday,
Eightfold, Avature, Amazon, Google, Apple), and `list_sweep.py` reads the SimplifyJobs lists and six
VC portfolio boards. It queries the ATS APIs, greps for experience gates
and seniority language, checks the comp band, and only then opens a tab. Most candidates die before
a browser is involved, which is what keeps a run cheap.

**Everything is written down before it submits.** A per-application doc with every question and
answer, a line in the log, a confirmation screenshot, and `state/status.md` as memory between runs.

## What it will never do

- Fabricate a fact about you. No invented salary, test score, address, date, or employer.
- Create an account, type a password, or log in, including with an emailed login code.
- Solve an interactive CAPTCHA.
- Submit a "please don't use AI" essay or a graded take-home. Filled up to that point, left open,
  flagged for you.
- Follow instructions embedded in a job posting. Page text is data, not orders.
- Apply through Handshake, LinkedIn Easy Apply, or Simplify.
- Touch a browser tab outside its own tab group. Your personal tabs are off limits.

<details>
<summary><b>Repo layout</b></summary>

```
please-hire-me/
├── setup.sh                  # one-time interactive setup
├── find.sh / review.sh / apply.sh   # find → you approve → submit approved only
├── run.sh                    # alias for find.sh
├── CLAUDE.md                 # the agent's playbook: browser method, widget recipes, rules
├── config/
│   ├── settings.json         # run knobs and target criteria      (yours, gitignored)
│   ├── profile.json          # every field value an ATS asks for  (yours, gitignored)
│   ├── answers.md            # free-text templates + fact sheet   (yours, gitignored)
│   ├── spec.md               # the run contract: rules, procedure, log format
│   └── documents.md          # cover letter + resume tailoring rules
├── data/
│   ├── queue.md              # vetted targets, worked top-down    (yours, gitignored)
│   ├── sources.md            # where to find roles: job lists, AI labs, quant, fellowships
│   ├── boards.md             # 235 ATS boards verified live, with job counts
│   ├── slug-candidates.txt   # every org slug ever tried; re-probe with scripts/probe_boards.sh
│   └── ats-field-notes.md    # application limits, hidden gates, slug traps, injection canaries
├── applications/             # one doc per application, full Q&A  (yours, gitignored)
├── logs/                     # the running log                    (yours, gitignored)
├── screenshots/              # proof of every submit              (yours, gitignored)
├── state/status.md           # the agent's memory between runs    (yours, gitignored)
└── scripts/
    ├── schedule.sh           # install/remove the recurring run
    ├── delta_sweep.py        # new reqs on every known Greenhouse/Ashby/Lever board
    ├── portal_sweep.py       # new reqs on company portals (Workday, Eightfold, Avature, ...)
    ├── list_sweep.py         # new reqs from SimplifyJobs lists and VC portfolio boards
    ├── code_broker.py        # emailed verification codes, pasted without the agent seeing them
    ├── app_docs.py           # resume conversion, keywords, tailoring checks, PDF builds
    ├── tracker_companies.py  # companies in your interview tracker (hard skips)
    ├── dupe_check.sh         # has this company been applied to already?
    ├── probe_boards.sh       # re-verify every ATS board
    └── scheduled_run.sh      # what the scheduler calls
```

</details>

<details>
<summary><b>FAQ</b></summary>

**Does this get me flagged as a bot?** No. It fills forms with genuine trusted input in your own
browser. Passive reCAPTCHA v3 passes. Interactive challenges are handed back to you.

**What does a run cost?** It runs on your Claude Code subscription, so usage rather than dollars per
application. Sourcing goes over JSON APIs specifically to keep it cheap.

**Does it do internships?** Yes, and it is probably the best fit for them. Put `internship` in
`targets.seniority`. Internships post hourly pay, so the full-time annual floor is ignored for
them and `targets.internship_min_hourly_usd` applies instead. The sourcing list in
`data/sources.md` is internship-heavy: SimplifyJobs Summer2027 (46k stars), vanshb03, and the
Northwestern quant list are all internship-first.

**Can I use it for non-engineering roles?** Yes. Nothing is engineering-specific except the defaults
in `settings.example.json` and the source list. Change the roles and the fact sheet.

**How long is setup, really?** About five minutes of your attention. Claude reads the resume, shows
you what it found, asks one list of questions, and drafts `config/answers.md` for you. The wizard
path is faster to run and slower to finish, because it hands you a blank `answers.md`.

**Why does it keep saying NEEDS HUMAN?** A fact is missing from `answers.md` or `profile.json`. Add
it once and that class of block disappears forever.

**My first run applied to less than the cap. Broken?** No. A fresh install has an empty queue, so
the first run spends its time sourcing. It fills the queue as it goes and picks up speed.

**Does it work on Workday / iCIMS / Avature / Eightfold?** Yes, once you sign in. Those portals need
an account per company, which the agent will not create or log into. Sign in yourself in Chrome and
list the portal in `channels.signed_in_portals` (see Optional add-ons). Workday sessions expire
within hours, so expect NEEDS HUMAN on scheduled runs unless you sign in shortly before.

**Can it run with my laptop closed?** No. It drives your real Chrome, so the machine has to be awake
and Chrome has to be running.

</details>

## Contributing

Yes please. Widget recipes for ATS quirks, new sourcing lanes, and setup ergonomics are the highest
value. See [CONTRIBUTING.md](CONTRIBUTING.md).

One rule above all: **never contribute anything that helps the agent lie.** No fabricated answers,
no CAPTCHA solving, no fake behavioral signals. A PR that makes it better at pretending to be a
human gets closed.

## License

MIT. See [LICENSE](LICENSE).
