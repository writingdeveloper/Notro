# Notro v2.10.3 release hardening

## Goal

Ship the Discord asset-link compatibility fix as Notro 2.10.3 without
publishing a release whose privacy disclosure, runtime dependencies, or version
metadata disagree with the executable behavior.

## Release identity

- Bump `notro_app.__version__` and its regression test from 2.10.2 to 2.10.3.
- Add a dated 2.10.3 changelog entry describing support for Discord CDN and
  media-proxy emoji/sticker link variants and the stricter validation added by
  final review.
- The release tag is `v2.10.3`.
- Winget manifests are generated only after the GitHub Release is published and
  its installer checksum is known.

## Dependency contract

Raise the Pillow requirement from `pillow>=10.0` to `pillow>=11.3.0`. Notro now
accepts and content-sniffs AVIF renditions, and Pillow wheels only include native
AVIF support from 11.3.0 onward. The declared minimum must therefore support the
behavior exercised by the AVIF regression test.

## Privacy and network disclosure

Update `SECURITY.md` and the privacy section in all five READMEs. The disclosure
must list both Discord asset hosts:

- `cdn.discordapp.com`
- `media.discordapp.net`

Remove the outdated claim that Notro contacts exactly four endpoints. Describe
the two Discord hosts together as on-demand sources used only when a user
registers an emoji or sticker link. No arbitrary web image hosts are added.

## Release workflow gates

The tag-triggered release job must fail before packaging when the pushed tag
does not equal `v` plus `notro_app.__version__`. The comparison must run only for
tag events so manual workflow dispatch remains usable as a build smoke test.

The release job must run the complete pytest suite before building the EXE. A
failed version check or test suite prevents installer creation and release
draft creation.

The workflow continues to create a draft release. Publishing remains a separate
post-build gate because the built-in updater reads `releases/latest`; users must
not see 2.10.3 until the installer and checksum have been inspected.

## Verification and deployment

Before pushing:

1. Run the release-version regression test and complete test suite.
2. Verify the changelog, dependency floor, privacy disclosures, and workflow
   version gate with focused checks.
3. Confirm a clean worktree and no existing `v2.10.3` tag or release.

Deployment sequence:

1. Push `main` and wait for branch CI to succeed at the intended commit.
2. Create and push annotated tag `v2.10.3` at that verified commit.
3. Wait for the Release workflow to succeed.
4. Confirm the draft contains `NotroSetup.exe` and
   `NotroSetup.exe.sha256`.
5. Download both assets and independently verify that the installer SHA-256
   matches the checksum file.
6. Review the generated release notes and publish the draft.
7. Confirm `v2.10.3` becomes the latest published release and the public assets
   remain downloadable.

## Failure handling

- If branch CI fails, do not tag.
- If the release workflow fails, leave the tag and failed run intact for
  diagnosis; do not publish a partial release.
- If assets or checksum validation fail, keep the release as a draft and stop.
- If publication fails, report the draft URL and error without bypassing
  permissions.

## Follow-up improvements

The following are valuable but are not part of 2.10.3 release hardening:

1. Make URL/file registration transactional so failed downloads and metadata
   writes cannot leave orphaned files.
2. Reject undecodable image payloads instead of retaining a file based only on
   its claimed extension.
3. Stream picker assets in bounded chunks and add direct `AssetServer` tests to
   avoid loading large files fully into memory.

Do not broaden registration to arbitrary web image URLs, add a Lottie runtime,
or restructure the picker/library architecture for this patch release.
