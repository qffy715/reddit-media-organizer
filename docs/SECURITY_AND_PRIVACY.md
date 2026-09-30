# Security and Privacy Notes

## Secrets

OAuth credentials belong in `.env`. The `.env` file is excluded by `.gitignore`.

Do not store or publish:

- Reddit account passwords;
- OAuth access/refresh tokens;
- browser cookies;
- client secrets;
- session data.

## Data minimization

The program does not intentionally store:

- Reddit usernames;
- Reddit user IDs;
- profile URLs;
- avatars;
- private messages;
- comments;
- voting history;
- inferred personal attributes.

Only metadata required for local media organization is retained.

## No redistribution through Git

The `data/` directory is ignored by Git. Downloaded Reddit media must not be committed to this repository.

## Deleted content

Use the cleanup command regularly when retaining Reddit-derived content locally:

```powershell
python .\src\reddit_media_organizer.py --cleanup-deleted
```

The cleanup routine removes local files and manifest records for post IDs that are no longer returned by Reddit.
