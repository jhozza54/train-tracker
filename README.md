# How Often Is My Train Late

Tracks three GWR commuter legs (Weston Milton, Bath Spa, Bristol Temple
Meads) and shows total minutes lost, on-time rate, cancellations, and
today's status on a small departure-board-style dashboard.

## 1. Get an RTT API token

1. Go to https://api-portal.rtt.io/ and sign in (create an RTT unified
   login account if you don't have one — free).
2. Request an API token for personal, non-commercial use.
3. Copy the token it gives you — this is what the tracker authenticates
   with (sent as a Bearer token).

Note: free tokens usually have a historical lookback limit (commonly ~14
days) — check `/api/info` once you have a token if you want the exact
number. That doesn't affect anything going forward: the tracker starts
logging from the day you switch it on, and "since tracking began" grows
from there.

## 2. Create the GitHub repo

1. Create a new **public** GitHub repository (public is required for free
   GitHub Pages, unless you're on a paid plan).
2. Push everything in this folder to it.
3. In the repo, go to **Settings → Secrets and variables → Actions → New
   repository secret**, name it `RTT_API_TOKEN`, and paste your token.

## 3. Turn on GitHub Pages

1. **Settings → Pages**.
2. Source: "Deploy from a branch", branch `main`, folder `/ (root)`.
3. Save — your dashboard will be live at
   `https://<your-username>.github.io/<repo-name>/` within a minute or two.

## 4. Turn on the tracker

The workflow in `.github/workflows/track.yml` runs automatically every
weekday evening (20:00 UTC) and commits the day's results to
`data/history.json`. You can also trigger it manually any time from the
**Actions** tab → "Track train punctuality" → **Run workflow**, which is
the fastest way to check it's working before waiting for the schedule.

## 5. Point your own domain at it (optional)

If you want `howoftenismytrainlate.com` (or similar) instead of the
github.io URL:
1. In your domain registrar, add a `CNAME` record pointing the subdomain
   (or an `A` record set for the apex domain) at GitHub Pages.
2. In **Settings → Pages → Custom domain**, enter your domain and save.

GitHub's own docs walk through the exact DNS records:
https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site

## Changing the trains being tracked

Edit the `LEGS` list at the top of `scripts/track.py` (station CRS codes,
scheduled times, search window) and the matching `LEGS` array near the top
of the `<script>` block in `index.html`.
