# Notro early-user growth strategy — research and beta activation, October 17 2026

**Status: NOT an authorization to post, advertise or publish a release.**
Current public latest is v2.10.3. Candidate v2.11.0 is an unmerged Draft PR,
and actual user Discord draft attachment/Windows UI acceptance remains NO-GO.
The user has explicitly excluded signing. All public download guidance must
truthfully disclose that the available installer is unsigned; do not advise
people to bypass OS protections.

## 1. The thing to sell: workflow, not an unsupported Nitro equivalent

**Best initial positioning (English):**
"A personal image, sticker and GIF picker for Discord desktop — search with
a shortcut, paste as an attachment, and prepare bigger images to fit."

**Korean:**
"Windows에서 내 이모지·스티커·GIF를 단축키로 찾아 이미지 첨부로 붙여넣고,
큰 스크린샷은 선택한 업로드 한도에 맞게 준비하는 도구."

Disclosures directly next to the hero:
- Images are **file attachments, never native inline Nitro emoji**.
- Not affiliated with or approved by Discord. Compatibility can change.
- Windows 10/11 only; installer currently unsigned and may prompt Windows.
- Does not inject into/modify Discord or require an account token.
- Optional auto-send/capture default OFF; avoid promising Terms compliance.

Do NOT use claims such as "free Nitro", "infinite emoji", "bypass premium",
"Discord cannot block", "guaranteed no ban", or "compress every file in
one click". Actual output quality and upload quotas vary.

## 2. Observed baseline (checked via GitHub API 2026-10-17)

Repository writingdeveloper/Notro:
- Stars: 0; forks: 0.
- Latest public v2.10.3 installer asset count: 35 downloads; its SHA file:
  14 downloads. These are **asset download counters**, not unique installers
  or successfully installed users.
- GitHub traffic API: 13 repo views, 8 unique visitors in the trailing
  reported two-week window. Not a marketing conversion/active use measure.
- Open public issues reported by issue list: none (PRs not included).
- writingdeveloper.blog/projects/notro live page still mentions "10MB" and
  "v2.0"; has not been updated to match the current published release.
- Portfolio Draft PR #36 and separate security Draft PR #33 both have failing
  GitHub checks as of inspection, so do not bypass the npm vulnerability gate.

**Interpretation:** low observable awareness, but NO product-market fit
evidence either way. Buyer/user research and first-task completion must
precede paid traffic or a wide community post.

## 3. Competitive substitution: comparison on jobs-to-be-done

| Alternative | Verified strength | Notro's credible distinction | Why a user might still prefer them |
| --- | --- | --- | --- |
| Discord native emoji/GIF chooser | Built into the chat app; keyboard access to normal emojis/stickers/GIF | Owned portable local image collection + external Windows hotkey | Native rendering, zero extra software; Notro emojis are attachments |
| Microsoft PowerToys Advanced Paste | Clipboard formats, paste as PNG file, optional audio/video transcodes | Dedicated searchable persistent personal media library | Broader Microsoft-supported toolbox |
| ShareX | Strong screen/video capture, automation and file sharing | Hotkey to favorite media collections, not a capture-suite substitute | Mature screenshot capture and editing tool |
| Vencord FakeNitro | In-client fake-emoji/sticker functions and Nitro-like visual behavior | Independent OS-level app, **no Discord patches or plugins** | More Discord-native visual experience, different risk trade-offs |
| EmojiPick (MrLouix) | Global emoji hotkey and fuzzy text lookup; optional local LLM matching | Custom media assets, packs, GIFs and Discord-sized output | Context-aware standard emoji suggestions |

Competitor references for factual comparison:
- https://learn.microsoft.com/windows/powertoys/advanced-paste
- https://github.com/ShareX/ShareX
- https://vencord.dev/plugins/FakeNitro
- https://github.com/MrLouix/emoji-picker
- https://www.reddit.com/r/discordapp/comments/1owbrfi/
- https://www.reddit.com/r/discordapp/comments/1vtamuj/

Never claim these tools all have the same functionality, or that all
competitor workflows are equally safe/policy-compliant. This matrix compares
observable documented functions only; no adoption figures were available.

## 4. Primary audience / priority and job test

### Segment A: Emoji and GIF-heavy Windows Discord users (priority 1)

Task: install, import three personally owned images, find one with
Ctrl+Shift+E, show an unsent image attachment draft, and find it again
without a mouse. Measure first task completion, confusion about attachment
versus native emoji, hotkey conflicts and return intent.

Rationale: repeatable daily workflow and searchable personal library,
not just a one-time file compression. Discord users have reported friction
with emoji UI and keyboard access in community posts; these are qualitative
signals, not market sizing:
https://www.reddit.com/r/discordapp/comments/1owbrfi/
https://www.reddit.com/r/discordapp/comments/1vtamuj/

### Segment B: Gamers sharing oversized images (priority 2)

Task: with rights-cleared 24MiB+ original screenshot, compare original and
Notro output dimensions/size, paste it into an unsent private draft, and
inspect perceptual quality. Do not fabricate or generalize a sample
compression ratio. Sample video compression only if actual executable
preview and encoded source footage have been visually reviewed.

### Segment C: Windows open-source / privacy-conscious users (priority 3)

Task: source audit, no account token, default-safe settings, JSON backup,
portable pack, transparent update endpoints, unsigned install friction.
Use this group to check trust and support burden, not to imply formal
policy approval.

**Hypothesis to test:** Segment A returns to the searchable library more
often than one-off Segment B. Must be measured; not a factual conclusion.

## 5. Distribution: permission-aware ordering (no posts yet)

### Tier 0: Owned surfaces and consented feedback

Improve Notro README and release notes to clearly show published vs draft
features; keep the rights-cleared native WebView2 demo. Finish portfolio
dependency security audit before deploying the corrected landing page.
Use personal/known opt-in beta testers; no unsolicited private DMs.

### Tier 1: Windows/open-source maker communities after beta gate

GitHub Topics, own development blog, an authentic technical changelog,
small Windows utility communities and dev forums where project showcases
are explicitly permitted. Check current moderator rules before posting.

Reddit r/discordapp moderator messages distinguish casual personal
bot/project sharing from aggressive promotion. Repeated advertising can be
removed. Do not use it as the first/high-volume outbound channel:
https://www.reddit.com/r/discordapp/comments/1v7segl/

### Tier 2: Product Hunt after repeatable value is validated

The official guide prioritizes working production products, crisp benefit,
authentic demo and an engaged maker answering feedback. Suggested potential
topics include Windows, Open Source and Productivity (confirm availability).
Actual Product Hunt tagline must be <=60 chars, short description <=260 chars.
Do NOT ask for upvotes or engineer vote rings:
https://help.producthunt.com/en/articles/17350772-launch-guide

### Tier 3: Hacker News only if the founder writes the post personally

Official HN rules say no generated text in HN posts, no generated/AI-edited
comments, and no automated posting; HN is not primarily an ad channel.
This repo may contain internal FAQ/research *notes*, but **do not post
assistant-generated text** to HN. When technically mature, the maintainer
can write their own narrative around interesting Windows clipboard
race conditions, native WebView2, privacy and verifiable release pipeline.
https://news.ycombinator.com/newsguidelines.html

## 6. Four gated experiments (examples, not forecasts)

**Experiment 0: safety/availability** (P0, before recruitment)
- Windows 10/11 real GUI installation, tray, default-off controls, and an
  actual Discord non-sending attachment draft pass.
- Portfolio has accurate text and a green dependency security audit.
- A version-matched unsigned candidate is accessible through a human-
  approved download with checksum and an honest Windows warning.
- If any step fails: hold outreach, fix Plane P0 first.

**Experiment 1: 5-10 consenting Windows users (0 paid ad spend)**
- 4-5 segment A, 2-3 segment B, 1-2 segment C.
- Each tester receives the same clean-room tasks and a test profile where
  feasible. Consent is explicit and reversible.
- Targets for *deciding what to improve*, not predicted results:
  >=8/10 installed without unsafe bypass, >=7/10 first successful manual
  draft file paste in 3 minutes, >=6/10 accurately understand attachment
  versus native emoji, no unintended send/data loss.
- Observe where they hesitate; record minutes and notes locally, not
  keystrokes/clipboard/chat messages.

**Experiment 2: A/B first claim, not two different apps**
- Group A short hero: "Your image library, one hotkey away."
- Group B short hero: "Prepare and paste Discord screenshots in seconds."
- Same demo, unsigned warning, download CTA and privacy notice.
- Only after comparable traffic exists can clicks/qualitative reaction
  justify choosing one. Do not derive statistical conclusions from <20
  visitors or count install assets as unique customers.

**Experiment 3: release content once beta pass**
- 10-20 second genuine native picker UI (already captured with owned art).
- Separate 10-20 second *actually tested* screenshot optimize/draft demo,
  then gameplay clip or portable media pack if tested.
- English landing first, Korean localized matching function and version.
- Manually review every public claim with real artifact/QA evidence.

## 7. Ethical, privacy-preserving measurement

Track only aggregate site sessions, CTA clicks and GitHub asset download
counters; baseline correctly says the latter are not installs.
For volunteers collect a simple **opt-in, local** scorecard:
OS/Discord version, case passed, time to first manual draft paste,
hotkey confidence, clarity about attachments and whether they would use
it again in 7 days. No account identifiers, copied private text, filename
lists, Discord IDs/messages or always-on clipboard telemetry.

Suggested cohort reporting: invited / consented / installed / first paste /
understood / voluntarily reused, each numerator and denominator visible.
Do not store sensitive data in public Plane issue descriptions. If fewer
than 5 testers respond, label evidence exploratory.

## 8. Proposed publication and support guardrails

- Candidate PR remains Draft until P0 human QA and dependent landing audit.
- Signing explicitly excluded; describe unsigned trust and actual hashes,
  never instruct disabling Defender or SmartScreen.
- Notro is independent, not endorsed by Discord, and is **not** a way to
  bypass paid entitlements or send native emojis without Nitro.
- Discord prohibits automating ordinary user accounts as self-bots outside
  supported bot APIs:
  https://support.discord.com/hc/en-us/articles/115002192352-Automated-User-Accounts-Self-Bots
  Therefore retain user-directed paste, auto-send off by default and review
  account-policy risk before any public messaging.
- No guerrilla spam, fake reviews, fabricated screenshots, Reddit mass posts,
  platform vote solicitation or AI-written HN submissions/comments.
- No release, login, ad buy or community post was made in this research stage.

## 9. Next development handoff

- Implemented AND VERIFIED on GitHub-hosted Windows runner 39075263021
  (source 77689d6): clipboard focus-before-mutate, newer-copy detection,
  Win32 SendInput acknowledgment and actual Ctrl+V delivery to a separately
  owned Tk foreground test window. No Discord attachment was made; that
  remains distinct P0 NOTRO-5.
- Still P0: real Discord unsent attachment on a dedicated safe test surface,
  real Windows 10/11 first run, audited bilingual portfolio landing, then
  real working v2.11.0 release with honest unsigned disclosure.
- Already Done: actual native WebView2 picker demo with original icons and
  hosted-runner CF_HDROP/Unicode clipboard primitives.


## Product Hunt effectiveness — updated October 17, 2026

Decision: DEFER Product Hunt as a primary acquisition channel for Notro.
It is not necessarily dead, but upvotes and launch-day traffic are unreliable
proxies for installed users or repeat use. Notro's public audience is small
and candidate v2.11.0 is not yet publicly downloadable.

### Recent founder experiences — not representative statistics

| Self-report / date | Observed result | Interpretation |
| --- | --- | --- |
| ProductHunters, Oct 9 2026 (Ranks Hawk) | #34, 46 votes, 17 comments, 20 site visits, no sales | Votes did not equal customer acquisition |
| r/SaaS, July 2 2026 | Unsolicited sales-agency emails, zero customers claimed | Spam/vendor-solicitation cost |
| r/digital_marketing, Jan 14 2026 | #1 day/week, ~4,500 visitors, 370 signups, ~10 teams actually using it at 2 weeks | Exceptional ranking CAN drive visits, not equivalent to durable adoption |
| r/SaaS, Oct 14 2026 | Free dev tool Top 5, thousands of visitors; later ~10 active users, 300 downloads | Free launch exposure may decay without repeat use |

These are individuals' potentially biased/unverified experiences, not a
representative sample, Notro forecasts or causal evidence:
- https://www.reddit.com/r/ProductHunters/comments/1x1g9fa/
- https://www.reddit.com/r/SaaS/comments/1ulbwia/
- https://www.reddit.com/r/digital_marketing/comments/1qcpxhp/
- https://www.reddit.com/r/SaaS/comments/1x5lwbe/

### Platform rules as of October 2026

Product Hunt started engagement-based POINTS rather than raw upvotes in
October 2025; authentic activity and comments matter, and ranking factors
are not fully disclosed:
https://help.producthunt.com/en/articles/10275873-what-are-points

Its March 2026 Featuring Guidelines emphasize live, useful, novel and
well-crafted products. Homepage featuring is editorial, never guaranteed:
https://help.producthunt.com/en/articles/9883485-product-hunt-featuring-guidelines

Official launch guide says quality preparation starts weeks before launch
and real audience engagement matters:
https://help.producthunt.com/en/articles/17350772-launch-guide

The official launch page says listing is free, maker self-hunting is
allowed, and founders must NOT directly ask for upvotes or coordinate
vote rings:
https://www.producthunt.com/launch

### Notro-specific channel decision and time budget

1. Now: zero ad spend and zero PH preparation; complete real installed
   Windows GUI/unsent Discord draft, audited bilingual portfolio landing,
   and consented 5-10 person beta. Fix failures as Plane P0s first.
2. After P0s: publish the actual version-matched unsigned product with
   checksum/known limitations and rights-cleared demos. Reach Windows
   and Discord utility users through permitted, authentic discussions and
   task-oriented own-site documentation.
3. If at least 5 volunteers complete the core workflow and at least
   2 independently express intent to reuse it, allocate at most 2-4
   developer hours for an optional FREE Product Hunt listing; otherwise
   skip until subsequent major updates. These are exploratory thresholds,
   not statistical proof.
4. Measure source-attributed visits if voluntary privacy-safe metrics
   become available, verified installed beta users, first unsent draft
   completion, understanding that emoji are attachments, and voluntary
   week-1 return. Stars, PH points and release downloads are not users.
5. If PH yields mostly agency solicitations with no verified installs
   or actionable feedback, do not invest more. Prioritize FAQ/how-to
   videos, long-tail Windows/Discord task SEO, own GitHub and approved
   community conversations instead.

Conclusion: Product Hunt is a later optional small discovery experiment,
not the main Notro product-market validation or launch strategy.
