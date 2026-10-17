# Notro Windows code-signing readiness — October 13, 2026

Status: RESEARCHED / NOT SIGNED / NO SIGNING SUBSCRIPTION CREATED. This file
does not claim that any certificate, SmartScreen reputation, or identity
verification has been obtained.

## Current verified facts

- Product: writingdeveloper/Notro, MIT, actively maintained Windows utility.
- Main is **not protected** at inspection time (GitHub CLI authenticated
  branch-protection API returns HTTP 404, "Branch not protected").
  Do not switch branch protections or approval requirements without checking
  concurrent work sessions and confirming who will serve as reviewer.
- Published production version remains v2.10.3; v2.11.0 is a draft candidate.
- GitHub Actions builds EXE/Inno Setup and a SHA-256 file, and a manual QA run
  stores a three-day NOTRO-UNSIGNED-QA artifact. No production release tag
  was created for v2.11.0.
- Latest CI+unsigned QA build run for source e26122b:
  https://github.com/writingdeveloper/Notro/actions/runs/38499645717
- Downloaded installer tested **without executing it**:
  NotroSetup.exe: 17,091,762 bytes; ProductName Notro; FileVersion 2.11.0;
  SHA-256: 1b91f47abce7daf9d3f0a772cba065ba951f0885e22d5557241662ba9855ba9a.
  Manifest checksum matches; Authenticode is NotSigned.
- An unsigned SHA-256 checksum published alongside a binary validates transfer
  integrity relative to that manifest; it does NOT prove publisher identity.

## Signing providers

### First choice: SignPath Foundation (free OSS application)

Official policy: https://signpath.org/terms.html
Application information: https://signpath.org/apply.html

Notro broadly matches a number of documented prerequisites: MIT license,
public code, release history, project docs, code signing policy with role
assignments, declared network activity and an automated GitHub build.

It is NOT guaranteed to be accepted. SignPath explicitly requires a certain
verifiable reputation for downloadable executables and may reject low-profile
projects. No proprietary runtime components may be included except permitted
system libraries; confirm packaging and third-party notices before applying.
A trusted maintainer must manually approve signing requests, and team MFA,
review and verifiable source-to-binary provenance are required. REA remains an
OFFLINE research tool only and is not bundled; Notro does not patch or scan
Discord. Never represent certificate attribution as granted until accepted.

### Fallback: Microsoft Azure Artifact Signing Public Trust

Official quickstart: https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart
Signing choices: https://learn.microsoft.com/windows/apps/package-and-deploy/code-signing-options
Microsoft pricing: https://azure.microsoft.com/en-us/products/artifact-signing

Available for individual developers located in the USA or Canada. Requires an
Azure subscription, Public identity validation (legal name and billing identity
must match government ID) and certificate profile, completed by the account
holder. Basic plan pricing listed at USD $9.99/month. Initial SmartScreen
warnings can still occur until the signed publisher builds reputation;
a certificate is not a promise of immediate friction-free installation.

### Alternate: Microsoft Store MSIX

Microsoft documentation lists Store re-signing MSIX as a free path, but
requires separate packaging, policy and Store submission QA. Notro currently
uses Inno Setup and should not pretend its EXE is already Store-ready.

## Recommended order, with release gates

1. Keep user data and Discord account untouched; finish real drafted-message
   compatibility QA, GUI installer QA, user-facing unsigned disclosures.
2. Protect main with required CI and reviewed PR rules after coordinating with
   other worktrees and sessions; signing role ownership should be explicit.
3. Audit released installer dependencies, update third-party notices and ensure
   REA/Discord proprietary binaries are NOT bundled. Preserve build provenance
   and avoid building a trusted release from an unreviewed branch.
4. If broadening distribution, submit SignPath OSS application only through the
   maintainer-controlled account, complying with its reputation requirements.
5. If SignPath is not accepted, consider Azure Artifact Signing, requiring
   verified identity and approval of monthly spending. Do not activate paid
   resources, sign, or release automatically.
6. Sign the EXE and installer only after a verified identity/signing workflow
   exists. Validate Authenticode and timestamp, signed file hashes,
   Windows 10/11 install/uninstall behavior and SmartScreen separately.
7. Promote the candidate from Draft PR and Plane QA only after release gates.

## Integrity and security cautions

- Do not infer successful installation from compiling an Inno Setup package.
- Do not automatically install an unsigned QA artifact on the working PC.
- Do not bypass npm/pip security audits to produce a green build.
- Do not grant blanket third-party code-signing approval to an automated agent.
- Never claim ToS safety or native Discord Nitro entitlement for file attachments.
