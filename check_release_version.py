from __future__ import annotations

import argparse

from notro_app import __version__


def expected_tag() -> str:
    return f"v{__version__}"


def validate_tag(tag: str) -> None:
    expected = expected_tag()
    if tag != expected:
        raise ValueError(f"release tag {tag!r} does not match app version; expected {expected}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tag")
    args = parser.parse_args()
    try:
        validate_tag(args.tag)
    except ValueError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
