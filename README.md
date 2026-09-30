# Reddit Media Organizer

A small, local, read-only Python utility for organizing publicly available Reddit post metadata and Reddit-hosted media for personal, non-commercial programming and image-processing practice.

## Scope

This project is intentionally narrow:

- Uses Reddit's Data API through OAuth credentials.
- Runs locally on a personal Windows computer.
- Reads posts only from a subreddit explicitly configured by the user.
- Downloads only Reddit-hosted image media exposed by the API.
- Stores minimal metadata required to maintain a local manifest and avoid duplicate downloads.
- Does **not** post, comment, vote, send messages, moderate communities, or contact users.
- Does **not** attempt to bypass Reddit access controls, rate limits, authentication, or anti-abuse systems.
- Does **not** include code for training or fine-tuning machine-learning/AI models on Reddit data.

This repository is intended to accompany a Reddit Data API access request. API access should only be used after Reddit approval and with credentials issued for this application.

## Why Devvit is not a fit

The application is a local Python utility rather than an in-Reddit application. Its workflow requires:

- access to the user's local filesystem;
- local image files;
- a local CSV manifest;
- local SHA-256 duplicate detection;
- a local Python environment.

It does not provide an in-Reddit user experience.

## Data minimization

The program intentionally does not store Reddit usernames, profile data, user IDs, comments, messages, votes, or other account-level information.

The manifest stores only:

- post ID;
- title;
- creation time;
- permalink;
- media URL;
- local filename;
- SHA-256 hash.

A cleanup command is included to remove locally stored files and manifest rows for posts that are no longer returned by Reddit.

## Setup

### 1. Create a virtual environment

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 2. Configure credentials

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and provide the OAuth credentials issued for this application.

Use a truthful, descriptive User-Agent. Reddit's documented format is similar to:

```text
windows:reddit-media-organizer:v0.1.0 (by /u/ComplaintDirect6349)
```

Never commit `.env`, OAuth secrets, access tokens, browser cookies, or passwords.

### 3. Validate configuration without contacting Reddit

```powershell
python .\src\reddit_media_organizer.py --validate
```

### 4. Run after API access has been approved

```powershell
python .\src\reddit_media_organizer.py
```

For a non-downloading preview:

```powershell
python .\src\reddit_media_organizer.py --dry-run
```

### 5. Cleanup content no longer returned by Reddit

```powershell
python .\src\reddit_media_organizer.py --cleanup-deleted
```

## Configuration

The default `.env.example` is deliberately conservative for API review.

```text
TARGET_SUBREDDIT=mannequincensor
MAX_POSTS=100
SORT=new
DOWNLOAD_DELAY_SECONDS=0.75
```

`MAX_POSTS` limits each run. The tool is not designed to circumvent platform access limits or perform unapproved bulk exports.

## Output

By default:

```text
data/
├── images/
├── manifest.csv
└── state.json
```

`data/` is excluded from Git so downloaded Reddit content is not redistributed through this repository.

## Important policy note

This project is designed around authenticated, approved, read-only API access. The repository itself does not grant permission to access or reuse Reddit content. Users are responsible for complying with Reddit's current Developer Terms, Data API Terms, Responsible Builder Policy, applicable content rights, and any other relevant rules.

If your intended use changes — for example, model training, commercial use, redistribution, or broader data collection — obtain any additional approval required before changing how the application is used.

## License

The source code in this repository is licensed under the MIT License. That license does **not** grant rights to Reddit content or third-party media.
