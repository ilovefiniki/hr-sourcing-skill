# HR Sourcing Skill — Project Instructions

## What This Is

A Claude Code skill (`/sourcing`) for IT candidate sourcing in the DACH region. It runs entirely locally — no backend, no deployment. Claude acts as the automation brain, orchestrating Apify (LinkedIn search), AI analysis, and Airtable storage through a local Python server.

## Architecture

```
/sourcing skill  →  sourcing-skill/server.py (localhost:8765)
                 →  Apify harvestapi/linkedin-profile-search
                 →  Airtable (candidate storage)
```

## How to Run

1. Add credentials to `sourcing-skill/.env` (see below)
2. Open this project in Claude Code
3. Type `/sourcing`

## Environment Variables

Stored in `sourcing-skill/.env` (not committed).

| Variable | Description |
|---|---|
| `APIFY_API_KEY` | Apify personal API token |
| `AIRTABLE_TOKEN` | Airtable personal access token |
| `AIRTABLE_BASE_ID` | Airtable base ID (appXXXXXXXXXX) |

## Project Structure

```
.claude/commands/sourcing.md   ← the /sourcing skill
sourcing-skill/
  server.py                    ← local HTTP server (form + save endpoint)
  form.html                    ← search form UI
  results_template.html        ← results page template
  results/                     ← generated results (gitignored)
  .env                         ← credentials (gitignored)
netlify-frontend/              ← archived v1 (React/Vite/Netlify + n8n)
```

## Requirements

- Claude Code CLI
- Python 3 (`python3 --version` to check)
- Apify account with credits for `harvestapi/linkedin-profile-search`
- Airtable account with a base set up for candidates
