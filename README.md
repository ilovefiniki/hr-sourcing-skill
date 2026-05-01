# HR Sourcing Skill for Claude Code

A `/sourcing` slash command for Claude Code that automates IT candidate sourcing in the DACH region. Claude orchestrates a LinkedIn search via Apify, analyzes profiles with AI, and stores results in Airtable — all running locally with no backend or deployment required.

## How It Works

```
/sourcing skill  →  sourcing-skill/server.py (localhost:8765)
                 →  Apify harvestapi/linkedin-profile-search
                 →  Airtable (candidate storage)
```

When you run `/sourcing`, Claude starts a local web server, opens a search form in your browser, runs the sourcing pipeline, and displays results in a new browser window. Progress details are shown in the Claude Code terminal.

## Setup

### 1. Get the project

Clone or download this repository to a local folder on your machine.

### 2. Open in Claude Code

Launch Claude Code and open the project folder.

### 3. Add your credentials

Create `sourcing-skill/.env` with your API keys:

```env
APIFY_API_KEY=your_apify_personal_api_token

# Optional — only needed to save candidates to Airtable
AIRTABLE_TOKEN=your_airtable_personal_access_token
AIRTABLE_BASE_ID=appXXXXXXXXXX
```

| Variable | Required | Where to get it |
|---|---|---|
| `APIFY_API_KEY` | Yes | [Apify console](https://console.apify.com) → Settings → API & Integrations |
| `AIRTABLE_TOKEN` | Optional | [Airtable](https://airtable.com) → Account → Developer hub → Personal access tokens |
| `AIRTABLE_BASE_ID` | Optional | Your Airtable base URL: `airtable.com/appXXXXXXXXXX/...` |

### 4. Run

Open a Claude Code session in the project folder and type:

```
/sourcing
```

A search form will open in your browser. Fill it in and submit — sourcing progress will appear in the Claude Code terminal, and results will open in a new browser window when complete.

## Requirements

- [Claude Code CLI](https://claude.ai/code)
- Python 3 (`python3 --version` to check; on Mac install via `xcode-select --install`)
- Apify account with credits for the `harvestapi/linkedin-profile-search` actor
- Airtable account with a base configured for candidate storage

## Project Structure

```
.claude/commands/sourcing.md   ← the /sourcing skill definition
sourcing-skill/
  server.py                    ← local HTTP server (form + save endpoints)
  form.html                    ← search form UI
  results_template.html        ← results page template
  results/                     ← generated results (gitignored)
  .env                         ← credentials (gitignored)
```
