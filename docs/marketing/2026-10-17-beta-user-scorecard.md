# Notro beta: consenting user interview / task scorecard

This is a private planning template, NOT live telemetry, email marketing,
sensitive-user collection, or permission to contact a stranger. A founder or
trusted test coordinator must obtain opt-in consent *before* testing. Offer
the option to stop and delete these notes. Keep responses local and avoid
posting raw notes to public issues/Plane.

## Privacy rules

- Give each volunteer a neutral ID such as T01; never paste their Discord ID,
  email, account handle, IP, chat messages, clipboard text or private paths.
- Use owned/dummy sample media in a dedicated test chat draft. Do NOT send the
  draft, run auto-send, or expose personal conversations during observation.
- Make any screen recording optional, **separate from task participation**.
  Never record unrelated windows or faces without explicit consent.
- Explain that unsigned Windows installers may trigger warnings; do not ask
  people to weaken OS security controls to finish a test.
- Store screenshots/logs privately, redact filenames/paths and delete when
  no longer needed. Report only aggregated, consented findings.

## Test environment

Volunteer ID: [not a name]
Test date: [YYYY-MM-DD]
Windows: [10/11 version]
Discord: [desktop version if separately volunteered]
Notro: [exact installed version/commit]
Source: [personal invite / GitHub issue / opt-in request / other]
Agreed to anonymous product feedback: [Yes/No]
Agreed to capture own-window product UI: [Yes/No]
Observed by: [role, not full name]

## Task 1 — clear proposition, first successful file paste

Read the Notro README/landing page once, without coaching.
Ask the user to summarize in their own words what the emoji becomes.
Pass only if they say it becomes an **image attachment**, not a native
Discord inline emoji or Nitro entitlement.

Expected sequence: verify owned example image; open own Notro picker;
select search result via shortcut; preview the file in an **unsent** draft.
Record time from the initial open to observable draft preview, excluding
account setup. Never click Send.

T1 install [PASS/FAIL/BLOCKED]  Time to install [minutes]
T1 understands attachment [PASS/FAIL]  Time to first unsent paste [seconds]
T1 hotkey works [PASS/FAIL]  Clipboard content unexpectedly lost [Yes/No]
T1 screenshot source remains unchanged [Yes/No]
Observed hesitation/technical blocker (redacted):

## Task 2 — primary user workflow (choose one)

A. Personal media: add three owned images, assign name/keyword, search from
hotkey, switch tabs, confirm repeat lookup.

B. Screenshot sharing: use an owned 24MB+ generated test image, compare before/
after dimensions/byte counts, review visible quality, open unsent attachment.
Never invent compression ratio.

C. Windows/open-source safety: inspect default OFF settings, pack ZIP privacy,
backup JSON paths opt-in, uninstall and the unsigned installer warning.

T2 type [A/B/C]  Completion [PASS/FAIL/BLOCKED]
T2 understood product limitation [PASS/FAIL]
T2 pain points (redacted):

## Follow-up after 7 days (voluntary; not behavioral tracking)

Would the volunteer use Notro again? [Yes/No/Undecided]
If yes, for which exact repeat task? [free text, no private account details]
Uninstall friction or trust concern? [free text, redacted]
One feature to improve before launch? [free text, redacted]
Volunteer's request to delete the feedback notes? [Yes/No]

## Minimum aggregate outcomes after 5–10 consenting testers

| Metric | Numerator | Denominator | Interpretation |
| --- | --- | --- | --- |
| Safe install completion | TBD | TBD | Shows onboarding friction, NOT download interest |
| Successful first unsent draft | TBD | TBD | Distinguish observed pass from unit tests |
| First paste within 3 minutes | TBD | TBD | Workflow activation experiment |
| Correctly explains attachments | TBD | TBD | Tests positioning clarity |
| Clipboard preserved/no wrong send | TBD | TBD | Safety P0, zero incidents tolerated |
| Would voluntarily reuse after 7 days | TBD | TBD | Early quality signal, not retention telemetry |
| Reports actionable bugs | TBD | TBD | Reproduction improvement |

Sample thresholds (not forecasts): 8/10 installs without bypassing security,
7/10 correct first file draft <=3m, 6/10 correctly know it is an attachment,
zero unintended messages, and zero clipboard data losses. Failure should
create a private redacted Plane issue and pause public release, not be hidden
to improve marketing conversion.

Never treat GitHub download counter, star or page view as an active user
count. No emails or analytics services are integrated in this template.

## Product questions asked neutrally

- What were you trying to do before seeing Notro?
- Where did you expect the selected image to appear?
- Which step took the most effort, and why?
- How would you normally do it without Notro?
- Was the unsigned Windows installer warning acceptable? Why / why not?
- What would have to improve for you to use this every week?

Avoid "Did you love this?" or leading comparisons that name a competitor
before a tester describes their own routine.
