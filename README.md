# TRMNL Meal Plan Publisher

Shows the current meal from your weekly keto meal plan on a [TRMNL](https://usetrmnl.com) e-ink device.

Uses the **Webhook Image plugin** — compatible with the TRMNL free plan. The app renders an 800×480px PNG and pushes it to TRMNL at each configured meal time. No public URL required; your server pushes out to TRMNL.

## How it works

- At each configured meal time (breakfast, lunch, dinner), renders the current meal as an 800×480px PNG and POSTs it to your TRMNL webhook URL
- Also publishes on startup, so restarting always shows the correct current meal
- Reads weekly meal plan files from `~/notes/keto/meal-plan-YYYY-MM-DD.md`
- `GET /display` serves the PNG locally for debugging — open in a browser to preview exactly what gets pushed

---

## Prerequisites

- Docker + Docker Compose
- A TRMNL device and account at [usetrmnl.com](https://usetrmnl.com)

---

## Step 1 — Add the Webhook Image plugin in TRMNL

1. Log in to [usetrmnl.com](https://usetrmnl.com) and go to **Plugins**
2. Find and add the **Webhook Image** plugin
3. Open the plugin settings — you'll see a unique **Webhook URL**
4. Copy that URL (you'll need it in Step 2)

---

## Step 2 — Configure the app

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Paste your webhook URL from Step 1
TRMNL_WEBHOOK_URL=https://usetrmnl.com/api/custom_plugins/your-uuid-here/image

BREAKFAST_TIME=07:00
LUNCH_TIME=12:00
DINNER_TIME=18:00
TIMEZONE=America/Indiana/Indianapolis
MEAL_PLAN_DIR=/mealplans
```

---

## Step 3 — Run

```bash
docker compose up --build -d
```

The app will immediately push the current meal to your device on startup.

Check status:

```bash
curl http://localhost:8000/health
```

Preview the PNG that gets pushed (open in browser):

```
http://localhost:8000/display
http://localhost:8000/display?meal_type=breakfast
http://localhost:8000/display?meal_type=lunch
http://localhost:8000/display?meal_type=dinner
```

Manually push a meal at any time:

```bash
curl -X POST "http://localhost:8000/publish?meal_type=breakfast"
```

---

## Meal time logic

| Current time | Meal pushed |
|---|---|
| Before `BREAKFAST_TIME` | Dinner (last meal of previous cycle) |
| `BREAKFAST_TIME` → `LUNCH_TIME` | Breakfast |
| `LUNCH_TIME` → `DINNER_TIME` | Lunch |
| After `DINNER_TIME` | Dinner |

The push happens at each threshold. TRMNL displays whatever was last pushed until the next push arrives.

---

## Meal plan file format

Files must be named `meal-plan-YYYY-MM-DD.md` where the date is the Monday of that week. The app picks the most recent file whose date is on or before today.

```markdown
# Keto Meal Plan — Week of May 11, 2026

## Monday

| Meal      | Food                          | Qty         | kcal | P   | F   | NC  |
|-----------|-------------------------------|-------------|------|-----|-----|-----|
| Breakfast | Hard cooked eggs *(pantry)*   | 2 large     | 156  | 12g | 10g | 1.2g|
|           | Sardines in olive oil         | 1 tin       | 190  | 22g | 11g | 0g  |
| Lunch     | Deli turkey roll-ups          | 5 oz (142g) | 150  | 25g | 2.5g| 2.5g|
| Dinner    | Chicken thighs — air fryer... | 2 thighs    | 458  | 50g | 27g | 0g  |
| Snacks    | String cheese *(pantry)*      | 1 stick     | 80   | 7g  | 6g  | 1g  |

## Tuesday
...
```

**Parser behaviour:**
- Day headings are detected by first word — `## Wednesday — Fajita Bowl Night` → Wednesday
- `## Sunday May 10 — Batch Prep` style headings are skipped automatically
- Empty meal cells continue the previous meal group
- `*(pantry)*`, `*(batch prep)*`, and cooking instructions (` — air fryer 380°F...`) are stripped from food names
- `## Weekly Summary` and `## Shopping List` sections are ignored

---

## API reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Status, current meal type, next scheduled push times |
| `GET` | `/display` | Preview the PNG that would be pushed right now |
| `GET` | `/display?meal_type=breakfast` | Preview a specific meal (`breakfast`, `lunch`, `dinner`) |
| `POST` | `/publish?meal_type=auto` | Manually push a meal to TRMNL now |
