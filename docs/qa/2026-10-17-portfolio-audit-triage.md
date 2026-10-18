# Notro landing portfolio audit — isolated triage (2026-10-17)

Status: upstream security blocker OPEN; no CI/security bypass or release.

The public Notro page at https://writingdeveloper.blog/projects/notro
still says 10MB and v2.0. Portfolio metadata Draft PR #36 and the
separate portfolio dependency Draft PR #33 both fail full CI.
Other sessions own these repositories, worktrees, and pull requests.
This investigation did not modify those worktrees or live pages.

## Isolated reproduction

Investigated portfolio PR #33 at source commit 2a4973e in a new,
independent worktree, without touching any uncommitted portfolio changes.

- Node 22.16.0; npm 10.9.2.
- npm view braces version: newest available 3.0.3.
- npm view micromatch version: 4.0.8.
- npm view eslint-config-next version: 16.4.2.
- npm audit --json: five HIGH advisories (0 critical/moderate/low).
- Vulnerable developer dependency chain:
  eslint-config-next -> @next/eslint-plugin-next -> fast-glob ->
  micromatch -> braces.
- Lockfile braces 3.0.3 is affected by advisory
  https://github.com/advisories/GHSA-vfj7-8cjw-p6xm.
  npm reports all published braces versions up to 3.0.3 as vulnerable.
  A patched version was not available through npm at inspection.
- npm audit fix --force suggests DOWNGRADING eslint-config-next to
  14.2.35, not a verified Next.js 16-compatible remedy.
- PR #33 GitHub Actions:
  https://github.com/writingdeveloper/portfolio/actions/runs/38500626360
  Next.js build PASSED; production-only audit (--omit=dev) showed
  zero known vulnerabilities; **full dev+production audit FAILED**.
  This does not prove the portfolio or third-party dependencies have
  no other security flaws.

## Required safety policy

Do NOT disable, silence, omit dev, or lower the existing full audit merely
to make CI appear green. Do not downgrade Next lint config to v14 without
a complete Next/React/TypeScript lint migration, and do not conceal a
known vulnerable braces fork under a new package name.

Safe options are:
1. Wait for the published patched upstream braces version or an upstream
   path not pulling in the vulnerable package, then update the lockfile
   and re-run all CI/build checks.
2. If urgent, explicitly review and validate an alternative Next 16
   lint/toolchain dependency graph with equivalent accessibility, React,
   Next, TypeScript and formatting checks and no security advisories.
   That is portfolio-wide cross-session work and needs human coordination.
3. Keep the separate Notro landing PR #36 Draft until the portfolio
   security check genuinely passes. Independently verify deployed EN/KO
   metadata, claims and version-matched v2.10.3/v2.11.0 download CTA.

A clean production-only audit does NOT override the failing configured
full dependency audit. The Notro candidate remains unreleased and the
user explicitly opted out of installer signing.
