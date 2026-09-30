# Reddit Data API Review Summary

## Application name

Reddit Media Organizer

## Applicant type

Personal developer / non-commercial use.

## Execution environment

Local Python application running on the applicant's personal Windows computer.

## Intended community

`r/mannequincensor`

## Purpose

The application helps the applicant organize and review publicly available Reddit-hosted image media for personal programming and image-processing practice.

It is not a public SaaS product, commercial product, moderation bot, messaging bot, or automated Reddit engagement tool.

## Why Devvit is not suitable

The workflow is centered on the user's local environment and filesystem. It needs to:

1. retrieve approved public post/media metadata through the Reddit Data API;
2. save selected Reddit-hosted media to a local folder;
3. maintain a local CSV manifest;
4. calculate local SHA-256 hashes for duplicate detection;
5. maintain local download state.

The application does not provide functionality inside Reddit and therefore does not need an in-Reddit UI.

## API behavior

The application is read-only.

It does not:

- submit posts;
- create comments;
- vote;
- send private messages or chats;
- perform moderation actions;
- follow or contact Redditors;
- create accounts;
- automate outreach;
- spoof User-Agent values;
- evade OAuth requirements;
- circumvent rate limits or access restrictions.

## Authentication

OAuth credentials issued for this application are loaded from a local `.env` file that is excluded from Git.

The User-Agent is explicit and descriptive:

```text
windows:reddit-media-organizer:v0.1.0 (by /u/YOUR_REDDIT_USERNAME)
```

## Data collected

The program minimizes stored metadata. It does not intentionally collect profile information, user IDs, messages, comments, voting history, or sensitive user attributes.

The local manifest contains:

- post ID;
- post title;
- creation time;
- permalink;
- Reddit-hosted media URL;
- local filename;
- SHA-256 file hash.

## Local media handling

Downloaded media is stored only on the applicant's local computer and `data/` is excluded from the Git repository.

The program restricts automatic media downloads to Reddit-controlled image hosts such as:

- `i.redd.it`
- `preview.redd.it`
- `external-preview.redd.it`

## Deleted-content cleanup

The application includes a cleanup mode:

```powershell
python .\src\reddit_media_organizer.py --cleanup-deleted
```

This re-checks stored post IDs using approved API access. Manifest entries and local files associated with posts that are no longer returned are removed.

## AI / ML

This repository does not contain functionality to train or fine-tune machine-learning or AI models on Reddit data.

Any materially different use would require review against Reddit's current policies and any additional approval required by Reddit.
