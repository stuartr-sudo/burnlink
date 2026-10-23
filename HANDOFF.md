# BurnLink handoff

## State (23 Oct 2026)

- `main` in this repo is the Atelier Bristle paint-brush storefront (commits 6c82521, 39d8556). It overwrote BurnLink's `main.py` and deleted `templates/drop.html`. The last BurnLink commit is 71d5d79.
- Branch `stripe-drop` (this checkout) starts from 71d5d79 and adds a second drop type for collecting Stripe keys.
- Live sites: https://burnlink-drop.fly.dev runs this branch (Fly app `burnlink-drop`, org Carter personal, region syd, volume `burnlink_data` 1GB, deployed 23 Oct 2026). https://burnlink.fly.dev still runs the old card-only build under a different Fly account that the flyctl login on this Mac (stuart.vial@gmail.com) cannot see.

## What changed on stripe-drop

- `main.py`: `POST /api/drops` takes JSON `{kind, config, ttl_hours}`. `kind` is `card` or `stripe`. `config` is creator settings (who is asking, live/test/both, webhook URL, event list, note) encrypted in the browser with the link key; the server stores ciphertext only. `ttl_hours` is 1 to 168, default 24. `GET /api/drops/{id}` returns `kind`, `config` and `expires_at`. Old records without `expires_at` still expire 24 hours after creation.
- `templates/drop.html`: landing page offers Card details or Stripe keys + webhook. The Stripe drop page shows a checklist, five numbered steps with direct Stripe Dashboard links (API keys, webhook event destination, signing secret) and the webhook URL with a copy button, then validated inputs (prefix checks for `pk_`, `sk_`/`rk_`, `whsec_` in the chosen mode). The recipient view shows each key with a copy button plus a ready `.env` block, then BURN.

## Verified

- Local run from this worktree: create Stripe drop, open link, validation error on wrong-mode key, submit, reload shows decrypted keys and `.env` block, burn returns 404. Card flow still works. Store file holds no plaintext.
- Local server config: `.claude/launch.json` entry `burnlink-stripe` (port 9998, scratch venv and data dir).

## Next

1. Redeploy with `fly deploy --ha=false -a burnlink-drop` from this directory.
2. Decide whether to retire the old `burnlink` app or point it at this build.
3. Decide whether `main` should be restored to BurnLink and the storefront moved to its own repo.
