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

This repository is intended to accompany a Reddit Data API access request. The application should only be used with authorized Reddit API access and credentials issued for this application.

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
