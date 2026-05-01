# /sourcing — HR Sourcing Automation

Run this skill to start a new candidate sourcing search. Follow each step in order.

---

## STEP 1 — Environment Setup

**Check Python is available:**

```bash
python3 --version 2>/dev/null || echo "PYTHON_MISSING"
```

If the output is `PYTHON_MISSING`, stop and tell the user:
"Python 3 is required but not found. On Mac: open Terminal and run `xcode-select --install`, then try again. Or download from https://python.org."

Read the file `sourcing-skill/.env` and load every non-comment line as an environment variable for this session. Then confirm the required key is present:

```bash
grep -v '^#' sourcing-skill/.env | grep -E 'APIFY_API_KEY' | grep -v '=$'
```

If `APIFY_API_KEY` is missing or empty, stop and tell the user: "Missing key in sourcing-skill/.env: APIFY_API_KEY. Please add it before running /sourcing."

Airtable keys (`AIRTABLE_TOKEN`, `AIRTABLE_BASE_ID`) are optional — only needed if you want to save candidates to Airtable at the end. If they are absent, sourcing and results will work fine but the Save to Airtable button will return an error.

---

## STEP 2 — Start the Server

Kill anything already on port 8765, then start the server in the background:

```bash
lsof -ti:8765 | xargs kill -9 2>/dev/null; true
cd sourcing-skill && python3 server.py &
sleep 1
curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/
```

If the last command returns `200`, the server is up. If not, retry once after 2 seconds. If still failing, stop and report the error.

---

## STEP 3 — Open the Form

```bash
open http://localhost:8765
```

Tell the user: "Form is open at http://localhost:8765 — fill it in and click Start Sourcing."

---

## STEP 4 — Wait for Submission

Poll every 5 seconds for `sourcing-skill/submission.json`. Do not proceed until it exists.

```bash
while [ ! -f sourcing-skill/submission.json ]; do sleep 5; done
echo "Submission received"
```

Once it exists, read it with the Read tool: `sourcing-skill/submission.json`

Extract these variables from the JSON:
- `job_title`, `company_name`, `company_website`, `job_description`, `work_model`, `job_location`
- `search_tier` (string: "1", "2", or "3")
- `manual_companies` (string, may be empty)
- `max_results` (string: "25", "50", "75", or "100"; default to "25" if missing)

Generate mandate ID:
```bash
SLUG=$(echo "COMPANY_NAME_HERE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed -E 's/-+/-/g' | sed 's/^-\|-$//g')
MANDATE_ID="${SLUG}-$(date +%s)"
echo $MANDATE_ID
```

Delete submission.json so it doesn't trigger again on the next run:
```bash
rm sourcing-skill/submission.json
```

Tell the user: "Starting automation for mandate `$MANDATE_ID`..."

---

## STEP 5 — Node 1: Job Analysis

YOU are performing this analysis directly. Apply the following framework to the job details from the submission:

```
You are a senior IT headhunter with 30 years of experience placing technology professionals in the DACH region.

Analyse the job description below and extract structured recruiting intelligence.
Your output will be used directly to identify source companies and generate LinkedIn search parameters — so the search keywords section must be precise and complete.

JOB TITLE: [job_title]
COMPANY: [company_name]
WORK MODEL: [work_model]
LOCATION: [job_location]

JOB DESCRIPTION:
[job_description]

Answer the following:

REQUIREMENTS CLASSIFICATION
- Must-haves (hard filters / knock-out criteria): list each explicitly and specifically
- Nice-to-haves (differentiators, not deal-breakers): list each one
- Implicit requirements (inferred from role context, company stage, and typical team structure)

ROLE FOCUS
- Primary technical focus (be precise)
- Seniority: Junior / Mid / Senior / Staff / Principal / Lead / Manager / Director

WORK MODEL & LOCATION CONSTRAINT
- Confirm: [work_model]
- If Hybrid: days per week in office? (extract from JD or infer)
- Geographic radius for candidates:
  - Hybrid → ~50 km of [job_location]
  - On-site → strict 50 km radius
  - Remote → look for candidates located in Germany

PRIMARY SEARCH KEYWORDS
- 6–8 LinkedIn job title variants this candidate currently holds
- 6–8 core technical skills or tools
- 2–3 industry or domain terms

OUTPUT FORMAT
1. Up to 8 job title variants as list
2. Up to 2 Must-Haves as list (most crucial)
3. Up to 2 Nice-to-Haves as list (most crucial)
4. Up to 2 industry or domain terms as list (most crucial)
```

Save the full output as NODE1_TEXT in your working context. Tell the user: "✓ Job analysis complete."

---

## STEP 6 — Node 2: Donor Companies (CONDITIONAL)

**Skip this step entirely if `search_tier` is "2" or "3".**

**If `search_tier` is "1" and `manual_companies` is not empty:**
- Split `manual_companies` by newlines and commas
- Slugify each name: lowercase, replace spaces and non-alphanumeric chars with hyphens, collapse double-hyphens, trim leading/trailing hyphens
- Set DONOR_SLUGS to the resulting array
- Set DONOR_SLUGS_RAW to the slugs joined by `, `
- Tell the user: "✓ Using manual companies: [DONOR_SLUGS_RAW]"
- Skip to Step 7

**If `search_tier` is "1" and `manual_companies` is empty — perform Node 2a then 2b:**

### Node 2a — First 5 donor companies

Use web search. Apply this framework:

```
You are a senior IT headhunter with deep knowledge of the DACH technology talent market.

Identify the FIRST 5 best donor companies for this search mandate.
Donor companies = organisations from which the ideal candidate is most likely to come,
based on tech stack overlap, company stage, culture fit, and career path alignment.

JOB ANALYSIS:
[NODE1_TEXT]

ROLE: [job_title]
COMPANY: [company_name]
LOCATION: [job_location]

LOCATION CONSTRAINT — apply strictly:
- HYBRID or ON-SITE: donors must have offices, engineering teams, or a known employee base within ~50 km of [job_location].
- FULLY REMOTE: no geographic constraint — best companies across Germany, Austria and beyond.

Use web search to verify each company is real, active, and a strong fit today. Use at most 4 searches — be selective.

SELECTION CRITERIA:
- Strong tech stack overlap with the target role
- Company stage is higher than the hiring company
- Known talent exporters in DACH for this profile type
- Companies where the candidate's likely frustrations are present (= movable candidates)
- Do NOT include: [company_name], its subsidiaries, or direct parent.

CRITICAL — FOR EACH COMPANY YOU MUST FIND THE LINKEDIN SLUG:
The slug is the last segment of the LinkedIn company page URL.
Example: https://www.linkedin.com/company/celonis/ → slug is "celonis"
Search for "site:linkedin.com/company [company name]" to find the exact URL.

OUTPUT FORMAT — numbered list 1–5:

[N]. [Company Name]
- Why a strong source: ...
- Size: ...
- HQ: ...
- LinkedIn slug: [exact slug only]
- LinkedIn URL: https://www.linkedin.com/company/[slug]/
```

Save output as NODE2A_TEXT.

### Node 2b — 5 more donor companies

Extract company names already found (lines starting with a digit + dot) from NODE2A_TEXT. Apply:

```
You are a senior IT headhunter with deep knowledge of the DACH technology talent market.

Identify 5 MORE donor companies — different from those already found.

JOB ANALYSIS:
[NODE1_TEXT]

ROLE: [job_title]
COMPANY: [company_name]
LOCATION: [job_location]

ALREADY FOUND — do NOT repeat any of these:
[comma-separated company names from NODE2A_TEXT]

LOCATION CONSTRAINT — apply strictly:
- HYBRID or ON-SITE: donors must have offices, engineering teams, or a known employee base within ~50 km of [job_location].
- FULLY REMOTE: no geographic constraint — best companies across Germany, Austria and beyond.

Use web search to verify each company is real, active, and a strong fit today. Use at most 4 searches — be selective.

SELECTION CRITERIA: same as Node 2a. Do NOT include [company_name] or anything from ALREADY FOUND.

OUTPUT FORMAT — numbered list 6–10:

[N]. [Company Name]
- Why a strong source: ...
- LinkedIn slug: [exact slug only]
- LinkedIn URL: https://www.linkedin.com/company/[slug]/
```

Save output as NODE2B_TEXT.

### Extract donor slugs

From the combined NODE2A_TEXT + NODE2B_TEXT, extract all values matching:
`LinkedIn slug: <value>` using the pattern `LinkedIn slug:\s*["']?([a-zA-Z0-9\-_]+)["']?`

Set DONOR_SLUGS as the extracted array and DONOR_SLUGS_RAW as the slugs joined by `, `.

Tell the user: "✓ Donor companies found: [DONOR_SLUGS_RAW]"

---

## STEP 7 — Node 3: Generate Apify Search Parameters

If `search_tier` is "2" or "3", DONOR_SLUGS_RAW was not set in Step 6. When filling in the `[DONOR_SLUGS_RAW]` placeholder in the prompt below, use "(none — not applicable for this tier)".

YOU generate the three Apify search configs directly. Apply this framework:

```
You are a technical sourcing specialist. Generate three structured JSON input objects
for the Apify LinkedIn Profile Search Actor (harvestapi/linkedin-profile-search).

JOB ANALYSIS & SEARCH KEYWORDS:
[NODE1_TEXT]

DONOR COMPANY SLUGS (for Search 1):
[DONOR_SLUGS_RAW]

ROLE: [job_title]
LOCATION: [job_location]
WORK MODEL: [work_model]

PARAMETER INSTRUCTIONS

1. searchQuery (string) — IMPORTANT: must be 300 characters or fewer.
   - Search 1: Must-Haves AND Nice-to-Haves AND domain terms
   - Search 2: Must-Haves AND domain terms
   - Search 3: Must-Haves only
   If the query exceeds 300 chars, truncate at the last AND before the limit.

2. currentJobTitles (array) — all 6–8 title variants from job analysis
   - Search 1 & 2: include all titles
   - Search 3: omit this field entirely

3. locations (array) — use ONLY cities from the "Geographic radius" section of Node 1.
   Bare city name only (correct: "Munich"; wrong: "Munich, Bavaria").
   Remote: single country name (e.g. "Germany").
   Same list for all three searches.

4. currentCompanyUrls (array) — LinkedIn slugs
   - Search 1: all DONOR_SLUGS
   - Search 2 & 3: omit this field entirely

5. yearsAtCurrentCompany: [1,2,3,4,5,6,7,8,9,10] — always, all searches

6. yearsOfExperience — derive from seniority in Node 1:
   Junior→[0,1,2,3]  Mid→[3,4,5,6]  Senior→[5,6,7,8,9,10]
   Staff/Lead→[8,9,10,11,12,13,14,15]  Principal→[10,11,12,13,14,15,16,17,18,19,20]
   Manager→[6,7,8,9,10,11,12,13,14,15]  Director→[10,11,12,13,14,15,16,17,18,19,20]
   Same range all searches.

7. excludeCurrentJobTitles — always, all searches:
   ["Freelancer","Freelance Developer","Freelance Engineer","Freelance Consultant",
    "Self-employed","Independent Consultant","Independent Contractor","Contractor",
    "Freiberufler","Freiberufliche","Selbstständig"]

8. profileScraperMode: "Full" — always, all searches

9. maxItems: [max_results as integer] — use the value from the submission (25, 50, 75, or 100). All searches.

10. takePages — derived from max_results: 25→1, 50→2, 75→3, 100→4. All searches.

OUTPUT FORMAT: Three labelled JSON code blocks, no comments inside JSON.

### Search 1 — Narrow
### Search 2 — Medium
### Search 3 — Broad
```

After generating, verify any `searchQuery` exceeding 300 chars is truncated at the last ` AND ` before character 300.

Parse the three JSON blocks. Select the config for the chosen tier:
- `search_tier == "1"` → use Search 1 — Narrow config → TIER_LABEL = "LinkedIn-Narrow"
- `search_tier == "2"` → use Search 2 — Medium config → TIER_LABEL = "LinkedIn-Medium"
- `search_tier == "3"` → use Search 3 — Broad config → TIER_LABEL = "LinkedIn-Broad"

Save selected config as APIFY_CONFIG (JSON object). Tell the user: "✓ Apify config ready. Starting [TIER_LABEL] search..."

---

## STEP 8 — Apify Run

Read APIFY_API_KEY from the .env already loaded.

### Start the run

Write APIFY_CONFIG to a temp file, then POST it:

**Before running the bash block below, replace `APIFY_CONFIG_JSON_HERE` with the actual APIFY_CONFIG JSON object you generated in Step 7.**

```bash
cat > /tmp/apify_input.json << 'APIFY_EOF'
APIFY_CONFIG_JSON_HERE
APIFY_EOF

RUN_RESPONSE=$(curl -s -X POST \
  "https://api.apify.com/v2/acts/harvestapi~linkedin-profile-search/runs" \
  -H "Authorization: Bearer $APIFY_API_KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/apify_input.json)

echo "$RUN_RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if 'data' not in d:
    print('ERROR:', d)
    exit(1)
print('RUN_ID:', d['data']['id'])
print('DATASET_ID:', d['data']['defaultDatasetId'])
"
```

Extract RUN_ID and DATASET_ID from the output. If the command fails or prints ERROR, stop and report: "Apify run failed to start. Check APIFY_API_KEY in sourcing-skill/.env. Response: [response]"

### Poll until complete

Check status every 15 seconds. Print current status each time. Stop when SUCCEEDED or FAILED/ABORTED:

```bash
curl -s \
  "https://api.apify.com/v2/acts/harvestapi~linkedin-profile-search/runs/$RUN_ID" \
  -H "Authorization: Bearer $APIFY_API_KEY" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['status'])"
```

Stop polling and report an error if 100 poll cycles (25 minutes) pass without SUCCEEDED status.

If status is FAILED or ABORTED, stop and report: "Apify run [RUN_ID] failed with status [STATUS]. Check the Apify console for details."

### Fetch results

```bash
curl -s \
  "https://api.apify.com/v2/datasets/$DATASET_ID/items?format=json&clean=true" \
  -H "Authorization: Bearer $APIFY_API_KEY" \
  -o sourcing-skill/apify_results_raw.json

python3 -c "
import json
profiles = json.load(open('sourcing-skill/apify_results_raw.json'))
print(len(profiles), 'profiles received')
"
```

If 0 profiles: tell the user "⚠️ Apify returned 0 results. The results page will show an empty table. Consider widening the search tier." Then continue.

---

## STEP 9 — Build Candidate List

Read `sourcing-skill/apify_results_raw.json`. For each profile object, create a candidate dict
using the field mapping from the v6 n8n production workflow:

```python
import datetime

def extract_location(profile):
    loc = profile.get("location")
    if isinstance(loc, dict):
        # primary: linkedinText (e.g. "Berlin, Germany")
        text = loc.get("linkedinText") or loc.get("city") or loc.get("country")
        return text or ""
    return str(loc) if loc else ""

def extract_title(profile):
    # primary field
    if profile.get("currentJobTitle"):
        return profile["currentJobTitle"]
    # fallback: current experience entry (no endDate or endDate == "Present")
    for exp in profile.get("experience", []):
        end = exp.get("endDate")
        if not end or (isinstance(end, dict) and not end) or (isinstance(end, str) and "present" in end.lower()):
            pos = exp.get("position") or exp.get("title")
            if pos:
                return pos
    return profile.get("headline", "")

def extract_company(profile):
    # primary field
    if profile.get("currentCompanyName"):
        return profile["currentCompanyName"]
    # fallback: currentPosition array
    pos = profile.get("currentPosition") or []
    if pos:
        return pos[0].get("companyName", "")
    return ""

candidate = {
    "full_name": f"{profile.get('firstName','')} {profile.get('lastName','')}".strip(),
    "linkedin_url": profile.get("linkedinUrl") or profile.get("profileUrl") or "",
    "location": extract_location(profile),
    "current_title": extract_title(profile),
    "current_company": extract_company(profile),
    "source": TIER_LABEL,
    "mandate_id": MANDATE_ID,
    "job_title": job_title,
    "company_name": company_name,
    "added_date": datetime.datetime.now(datetime.timezone.utc).isoformat()
}
```

Save the list as `sourcing-skill/candidates.json`. Clean up the raw file:
```bash
rm sourcing-skill/apify_results_raw.json
```

---

## STEP 10 — Generate Results HTML

Read `sourcing-skill/results_template.html` and replace the 8 tokens using Python:

```python
import json, datetime

with open('sourcing-skill/results_template.html') as f:
    tmpl = f.read()

with open('sourcing-skill/candidates.json') as f:
    candidates = json.load(f)

timestamp = datetime.datetime.now().strftime('%-d %b %Y, %H:%M')

html = tmpl \
    .replace('{{MANDATE_ID}}', MANDATE_ID) \
    .replace('{{JOB_TITLE}}', job_title) \
    .replace('{{COMPANY_NAME}}', company_name) \
    .replace('{{TIER_LABEL}}', TIER_LABEL) \
    .replace('{{TIMESTAMP}}', timestamp) \
    .replace('{{CANDIDATE_COUNT}}', str(len(candidates))) \
    .replace('{{CANDIDATES_JSON}}', json.dumps(candidates, ensure_ascii=False)) \
    .replace('{{ERROR_HTML}}', '')

out_path = f'sourcing-skill/results/{MANDATE_ID}.html'
with open(out_path, 'w') as f:
    f.write(html)
print('Written to:', out_path)
```

Clean up:
```bash
rm sourcing-skill/candidates.json
```

---

## STEP 11 — Open Results

```bash
open "sourcing-skill/results/${MANDATE_ID}.html"
```

Tell the user:
"✓ Done! Results saved to sourcing-skill/results/[MANDATE_ID].html
[N] candidates found. Select candidates in the browser and click Save to Airtable.
The server is still running — keep this terminal open until you've saved."

---

## STEP 12 — Keep Server Alive

Do not stop server.py. The browser's Save to Airtable button calls `http://localhost:8765/save`.

When the user says they are done, stop the server:
```bash
lsof -ti:8765 | xargs kill -9 2>/dev/null && echo "Server stopped."
```
