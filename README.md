# Genie Cost Calculator

Databricks App to **project Genie One / Genie Agents consumption and cost** and build a budget.

The cost model is a faithful port of the internal Mosaic GenAI Calculator (Genie tab):
each user persona has a fixed gross consumption in **DBU/user/month**, a free tier of
150 DBU/user/month is applied per persona, and the remaining billed DBUs are priced at
the selected region's `$/DBU` rate.

```
billed = max(users × dbu_per_user − min(users × 150, incurred), 0)
cost   = billed_DBU × region_rate
```

Validated against the reference calculator (default mix → 20,560.71 billed DBU → $1,439.25/mo on AWS US East).

## Variants

| Folder | Language | Branding | Default region |
|--------|----------|----------|----------------|
| [`genie-cost-calculator/`](genie-cost-calculator/) | Portuguese (BR) | Databricks | AWS-SA (Brazil) |
| [`genie-cost-santander/`](genie-cost-santander/) | Spanish | Banco Santander | Azure-EU West |

## Features

- 64 cloud regions with correct `$/DBU` pricing
- Editable free tier (150 DBU/user) and promo/discount %
- KPIs: steady-state monthly cost, year-1 budget, billed DBUs, % covered by free tier
- 12-month budget projection with a configurable adoption ramp
- Per-persona breakdown table
- Saved scenarios (localStorage)

## Stack

FastAPI backend serving a single-file frontend (vanilla JS + Chart.js via CDN). Compute is done client-side; the backend also exposes `/api/model` and `/api/calculate`.

## Run / deploy (Databricks Apps)

```bash
cd genie-cost-calculator   # or genie-cost-santander
databricks sync . /Workspace/Users/<you>/genie-cost-calculator --profile <profile>
databricks apps deploy genie-cost-calculator \
  --source-code-path /Workspace/Users/<you>/genie-cost-calculator --profile <profile>
```

---

*Estimates carry a ±10% margin, in USD list price, before contractual discounts.*
