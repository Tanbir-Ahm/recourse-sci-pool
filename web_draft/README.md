# web_draft: the new front end, kept as a git bundle until its own repository exists

`recourse-web.bundle` holds the whole history of the project `recourse-web` (the Next.js front end, FOLLOW_UPS 2cf). It is here only because the repository `Tanbir-Ahm/recourse-web` did not exist yet (2026-10-23).
To use it: `git clone recourse-web.bundle recourse-web` (then `npm install`; tests: `npx vitest run`; browser tests need a checkout of the Recourse repository: `RECOURSE_REPO=/path/to/recourse npx playwright test`).
When the owner has created the EMPTY private repository and added it to the session: push the bundle's `main` branch there, check it, then delete this folder.
No secrets are in it (settings are read from environment variables; `.env.example` lists the names).
