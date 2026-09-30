from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import sys
import time
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import praw
import requests
from dotenv import load_dotenv


APP_VERSION = "0.1.0"
ALLOWED_IMAGE_HOSTS = {
    "i.redd.it",
    "preview.redd.it",
    "external-preview.redd.it",
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
MANIFEST_FIELDS = [
    "post_id",
    "title",
    "created_utc",
    "permalink",
    "image_url",
    "local_file",
    "sha256",
]


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only Reddit media organizer. "
            "Requires approved OAuth-based Reddit Data API access."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read post/media metadata but do not download media.",
    )
    parser.add_argument(
        "--cleanup-deleted",
        action="store_true",
        help=(
            "Remove manifest rows and local files for post IDs that are no longer "
            "returned by Reddit."
        ),
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate local configuration without contacting Reddit.",
    )
    return parser.parse_args()


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_config() -> dict:
    load_dotenv(repository_root() / ".env")

    config = {
        "client_id": os.getenv("REDDIT_CLIENT_ID", "").strip(),
        "client_secret": os.getenv("REDDIT_CLIENT_SECRET", "").strip(),
        "user_agent": os.getenv("REDDIT_USER_AGENT", "").strip(),
        "subreddit": os.getenv("TARGET_SUBREDDIT", "mannequincensor").strip(),
        "max_posts": int(os.getenv("MAX_POSTS", "100")),
        "sort": os.getenv("SORT", "new").strip().lower(),
        "download_delay": float(os.getenv("DOWNLOAD_DELAY_SECONDS", "0.75")),
        "output_dir": os.getenv("OUTPUT_DIR", "data").strip(),
    }

    if not config["subreddit"]:
        raise RuntimeError("TARGET_SUBREDDIT cannot be empty.")

    if config["max_posts"] < 1 or config["max_posts"] > 500:
        raise RuntimeError("MAX_POSTS must be between 1 and 500 in this review build.")

    if config["sort"] not in {"new", "hot"}:
        raise RuntimeError("SORT must be either 'new' or 'hot'.")

    if config["download_delay"] < 0.25:
        raise RuntimeError(
            "DOWNLOAD_DELAY_SECONDS must be at least 0.25 in this review build."
        )

    output = Path(config["output_dir"])
    if not output.is_absolute():
        output = repository_root() / output
    config["output_dir"] = output

    return config


def validate_local_config(config: dict, require_credentials: bool) -> None:
    if require_credentials:
        if not config["client_id"]:
            raise RuntimeError("REDDIT_CLIENT_ID is required.")
        if not config["client_secret"]:
            raise RuntimeError("REDDIT_CLIENT_SECRET is required.")

    if not config["user_agent"]:
        raise RuntimeError("REDDIT_USER_AGENT is required.")

    ua = config["user_agent"]
    if "YOUR_REDDIT_USERNAME" in ua:
        raise RuntimeError(
            "Replace YOUR_REDDIT_USERNAME in REDDIT_USER_AGENT with the Reddit "
            "account named in your API request."
        )

    if "by /u/" not in ua:
        raise RuntimeError(
            "REDDIT_USER_AGENT should be descriptive and include '(by /u/username)'."
        )


def create_reddit(config: dict) -> praw.Reddit:
    reddit = praw.Reddit(
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        user_agent=config["user_agent"],
        check_for_async=False,
    )
    reddit.read_only = True
    return reddit


def canonical_media_url(url: str | None) -> str | None:
    if not url:
        return None
    url = html.unescape(str(url)).strip()
    if not url.startswith(("https://", "http://")):
        return None

    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_IMAGE_HOSTS:
        return None

    return url


def looks_like_image(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.hostname in {"i.redd.it", "preview.redd.it", "external-preview.redd.it"}:
        return True
    return Path(parsed.path).suffix.lower() in IMAGE_EXTENSIONS


def add_unique(urls: list[str], candidate: str | None) -> None:
    url = canonical_media_url(candidate)
    if not url or not looks_like_image(url):
        return
    if url not in urls:
        urls.append(url)


def extract_reddit_hosted_images(submission) -> list[str]:
    urls: list[str] = []

    add_unique(urls, getattr(submission, "url", None))

    gallery_data = getattr(submission, "gallery_data", None)
    media_metadata = getattr(submission, "media_metadata", None)

    if isinstance(gallery_data, dict) and isinstance(media_metadata, dict):
        for item in gallery_data.get("items", []):
            media_id = item.get("media_id")
            if not media_id:
                continue
            metadata = media_metadata.get(media_id, {})
            source = metadata.get("s", {}) if isinstance(metadata, dict) else {}
            add_unique(urls, source.get("u"))
            add_unique(urls, source.get("gif"))

    preview = getattr(submission, "preview", None)
    if isinstance(preview, dict):
        for image in preview.get("images", []):
            if isinstance(image, dict):
                source = image.get("source", {})
                if isinstance(source, dict):
                    add_unique(urls, source.get("url"))

    return urls


def output_paths(config: dict) -> tuple[Path, Path, Path]:
    output_dir: Path = config["output_dir"]
    images_dir = output_dir / "images"
    manifest = output_dir / "manifest.csv"
    state = output_dir / "state.json"
    return images_dir, manifest, state


def ensure_output(config: dict) -> None:
    images_dir, manifest, state = output_paths(config)
    images_dir.mkdir(parents=True, exist_ok=True)

    if not manifest.exists():
        with manifest.open("w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS)
            writer.writeheader()

    if not state.exists():
        state.write_text(
            json.dumps({"seen_urls": [], "sha256": []}, indent=2),
            encoding="utf-8",
        )


def load_state(config: dict) -> tuple[set[str], set[str]]:
    _, _, state_path = output_paths(config)
    if not state_path.exists():
        return set(), set()

    data = json.loads(state_path.read_text(encoding="utf-8"))
    return set(data.get("seen_urls", [])), set(data.get("sha256", []))


def save_state(config: dict, seen_urls: set[str], hashes: set[str]) -> None:
    _, _, state_path = output_paths(config)
    tmp = state_path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(
            {
                "seen_urls": sorted(seen_urls),
                "sha256": sorted(hashes),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    tmp.replace(state_path)


def append_manifest(config: dict, row: dict) -> None:
    _, manifest_path, _ = output_paths(config)
    with manifest_path.open("a", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS)
        writer.writerow(row)


def choose_extension(content_type: str, url: str) -> str:
    ct = content_type.lower().split(";", 1)[0].strip()
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/avif": ".avif",
    }
    if ct in mapping:
        return mapping[ct]

    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return suffix

    return ".img"


def download_media(
    session: requests.Session,
    user_agent: str,
    url: str,
) -> tuple[bytes, str, str] | None:
    response = session.get(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        },
        timeout=60,
    )

    if response.status_code != 200:
        print(f"    HTTP {response.status_code}: {url}")
        return None

    content_type = response.headers.get("Content-Type", "")
    if not content_type.lower().startswith("image/"):
        print(f"    Skipping non-image response: {content_type}")
        return None

    data = response.content
    if not data:
        return None

    digest = hashlib.sha256(data).hexdigest()
    extension = choose_extension(content_type, url)
    return data, extension, digest


def iter_submissions(reddit: praw.Reddit, config: dict) -> Iterable:
    subreddit = reddit.subreddit(config["subreddit"])
    if config["sort"] == "new":
        return subreddit.new(limit=config["max_posts"])
    return subreddit.hot(limit=config["max_posts"])


def normal_run(reddit: praw.Reddit, config: dict, dry_run: bool) -> None:
    ensure_output(config)
    images_dir, _, _ = output_paths(config)
    seen_urls, hashes = load_state(config)

    session = requests.Session()

    print(
        f"Read-only scan: r/{config['subreddit']} | "
        f"sort={config['sort']} | max_posts={config['max_posts']}"
    )

    scanned = 0
    found = 0
    saved = 0

    for submission in iter_submissions(reddit, config):
        scanned += 1
        urls = extract_reddit_hosted_images(submission)
        if not urls:
            continue

        print(f"[{submission.id}] {submission.title[:100]}")

        for index, url in enumerate(urls, start=1):
            found += 1

            if url in seen_urls:
                print(f"    [{index}] already recorded")
                continue

            if dry_run:
                print(f"    [{index}] {url}")
                continue

            result = download_media(session, config["user_agent"], url)
            if result is None:
                continue

            data, extension, digest = result

            if digest in hashes:
                print(f"    [{index}] duplicate content")
                seen_urls.add(url)
                save_state(config, seen_urls, hashes)
                continue

            filename = f"{submission.id}_{index:02d}_{digest[:12]}{extension}"
            file_path = images_dir / filename
            file_path.write_bytes(data)

            permalink = f"https://www.reddit.com{submission.permalink}"

            append_manifest(
                config,
                {
                    "post_id": submission.id,
                    "title": submission.title,
                    "created_utc": submission.created_utc,
                    "permalink": permalink,
                    "image_url": url,
                    "local_file": str(file_path.relative_to(repository_root())),
                    "sha256": digest,
                },
            )

            seen_urls.add(url)
            hashes.add(digest)
            save_state(config, seen_urls, hashes)

            saved += 1
            print(f"    [{index}] saved: {filename}")

            time.sleep(config["download_delay"])

    print()
    print(f"Posts scanned: {scanned}")
    print(f"Image URLs found: {found}")
    print(f"New files saved: {saved}")


def read_manifest(config: dict) -> list[dict]:
    _, manifest_path, _ = output_paths(config)
    if not manifest_path.exists():
        return []

    with manifest_path.open("r", newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def write_manifest(config: dict, rows: list[dict]) -> None:
    _, manifest_path, _ = output_paths(config)
    with manifest_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def cleanup_deleted(reddit: praw.Reddit, config: dict) -> None:
    ensure_output(config)
    rows = read_manifest(config)
    if not rows:
        print("Manifest is empty; nothing to clean.")
        return

    post_ids = sorted({row["post_id"] for row in rows if row.get("post_id")})
    fullnames = [f"t3_{post_id}" for post_id in post_ids]

    returned_ids: set[str] = set()
    batch_size = 100

    for start in range(0, len(fullnames), batch_size):
        batch = fullnames[start : start + batch_size]
        for submission in reddit.info(fullnames=batch):
            returned_ids.add(submission.id)

    keep_rows: list[dict] = []
    removed_files = 0
    removed_rows = 0

    for row in rows:
        if row.get("post_id") in returned_ids:
            keep_rows.append(row)
            continue

        local_file = row.get("local_file", "")
        if local_file:
            path = repository_root() / local_file
            try:
                if path.exists() and path.is_file():
                    path.unlink()
                    removed_files += 1
            except OSError as exc:
                print(f"Could not remove {path}: {exc}")

        removed_rows += 1

    write_manifest(config, keep_rows)

    # Rebuild state from retained manifest rows.
    seen_urls = {row["image_url"] for row in keep_rows if row.get("image_url")}
    hashes = {row["sha256"] for row in keep_rows if row.get("sha256")}
    save_state(config, seen_urls, hashes)

    print(f"Removed manifest rows: {removed_rows}")
    print(f"Removed local files: {removed_files}")


def main() -> int:
    args = parse_args()

    try:
        config = load_config()

        if args.validate:
            validate_local_config(config, require_credentials=False)
            print("Local configuration is structurally valid.")
            print(f"Target subreddit: r/{config['subreddit']}")
            print(f"Max posts per run: {config['max_posts']}")
            print(f"Sort: {config['sort']}")
            return 0

        validate_local_config(config, require_credentials=True)
        reddit = create_reddit(config)

        if args.cleanup_deleted:
            cleanup_deleted(reddit, config)
        else:
            normal_run(reddit, config, dry_run=args.dry_run)

        return 0

    except KeyboardInterrupt:
        print("\nStopped by user.")
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
