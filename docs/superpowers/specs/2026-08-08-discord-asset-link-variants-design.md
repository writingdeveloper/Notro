# Discord asset link variants

## Goal

Notro must accept the Discord CDN and media-proxy link variants that Discord
produces for emoji and stickers. General web image URLs remain out of scope.

## Accepted inputs

- Hosts: `cdn.discordapp.com`, `media.discordapp.net`
- Paths: `/emojis/{numeric-id}.{extension}` and
  `/stickers/{numeric-id}.{extension}`
- Image extensions: PNG, GIF, WebP, JPG/JPEG, and AVIF, case-insensitively
- Discord resize, quality, and format query parameters may be present
- Existing custom-emoji tags (`<:name:id>` and `<a:name:id>`) remain supported

Direct Lottie `.json` sticker assets remain unsupported because Notro does not
include a Lottie renderer. They continue to produce the existing specific
Lottie error rather than the generic invalid-link error.

## URL handling

Parsing will extract a validated Discord asset URL instead of reconstructing
every accepted input as a `cdn.discordapp.com` URL. This matters for media-proxy
renditions such as `.webp`: the media URL is valid, while the same extension at
the CDN origin may return 404.

Registration will download the validated input rendition first. Existing
content sniffing remains authoritative, so a response whose bytes differ from
its URL extension is stored with the correct extension. Existing animated
APNG/WebP conversion to GIF also remains unchanged.

The stored source URL will be the validated Discord URL used for the successful
download. Query parameters are retained when they are required for that media
rendition. Existing canonical behavior remains for custom-emoji tags, which do
not contain a source URL.

## Security and errors

Only the two explicitly allowed Discord hosts and the two asset path families
are accepted. Lookalike domains, unrelated Discord paths, malformed IDs,
extensionless paths, and general web URLs remain rejected.

- Direct `.json` sticker link: existing Lottie-specific error
- Structurally invalid or unsupported Discord link: existing invalid-link error
- Valid Discord link whose download fails: existing download error

## Tests

Regression tests will cover:

- Sticker media links using WebP, JPG/JPEG, AVIF, PNG, and GIF
- Emoji CDN/media links across supported image extensions
- Query strings and mixed-case extensions
- Preservation and use of a media-proxy URL during registration
- Existing custom-emoji tags and canonical CDN links
- Rejection of lookalike hosts, unrelated paths, malformed IDs, unknown
  extensions, and ordinary web URLs
- Direct Lottie `.json` links retaining their specific error

The focused fetch tests and the complete test suite must pass before the change
is considered complete.
