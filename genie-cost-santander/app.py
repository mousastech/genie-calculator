"""
Genie Cost Calculator — Databricks App
Projects Genie One / Genie Agent consumption and cost to build a budget.

Cost model is a faithful port of the internal Mosaic GenAI Calculator
(go/genaicalculator), Genie tab, "Genie One, Genie Agents" section.

Model:
  - Each persona has a fixed gross consumption in DBU/user/month (region-independent).
  - Free tier: FREE_DBU_PER_USER (default 150) DBU/user/month, applied per persona,
    capped at what that persona actually incurs.
  - billed = max(incurred - free, 0)
  - cost (list) = total billed DBU * region rate ($/DBU)
"""
import os
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Calculadora de Costos Genie — Santander")

# --- Cost model constants (sourced from Mosaic GenAI Calculator, Sept 2026) ---
FREE_DBU_PER_USER = 150.0

# Gross consumption per user per month, in DBUs. (dollar_per_user / 0.07 baseline)
PERSONA_DBU = {
    "genieOne": {
        "beginner":   26.142857,   # ~3-7 questions/mo
        "practitioner": 97.857143, # ~11-21/mo
        "power":      336.428571,  # ~35-65/mo
        "superPower": 1447.857143, # ~103-181/mo
    },
    "genieAgent": {
        "beginner":   21.142857,   # ~4-9 messages/mo
        "practitioner": 65.0,      # ~11-23/mo
        "power":      186.285714,  # ~26-57/mo
        "superPower": 661.714286,  # ~48-145/mo
    },
}

PERSONA_HINTS = {
    "genieOne": {
        "beginner": "~3-7 preguntas/mes · exploración ligera y ocasional",
        "practitioner": "~11-21/mes · analítica self-service regular",
        "power": "~35-65/mes · análisis iterativo diario",
        "superPower": "~103-181/mes · flujos analíticos intensivos",
    },
    "genieAgent": {
        "beginner": "~4-9 mensajes/mes · preguntas agénticas ocasionales",
        "practitioner": "~11-23/mes · análisis agéntico regular",
        "power": "~26-57/mes · investigaciones multi-paso frecuentes",
        "superPower": "~48-145/mes · flujos agénticos intensivos diarios",
    },
}

# Region -> $/DBU (Genie serverless rate). Sourced from the Mosaic calculator region table.
REGIONS = [
    {"name": "AWS-US East (N. Virginia)", "cloud": "aws", "rate": 0.07},
    {"name": "AWS-US East (Ohio)", "cloud": "aws", "rate": 0.07},
    {"name": "AWS-US West (Oregon)", "cloud": "aws", "rate": 0.07},
    {"name": "AWS-US West (N. California)", "cloud": "aws", "rate": 0.082},
    {"name": "AWS-Canada", "cloud": "aws", "rate": 0.078},
    {"name": "AWS-SA (Brazil)", "cloud": "aws", "rate": 0.112},
    {"name": "AWS-Europe (Ireland)", "cloud": "aws", "rate": 0.078},
    {"name": "AWS-Europe (London)", "cloud": "aws", "rate": 0.081},
    {"name": "AWS-Europe (France)", "cloud": "aws", "rate": 0.082},
    {"name": "AWS-Europe (Frankfurt)", "cloud": "aws", "rate": 0.084},
    {"name": "AWS-AP (Singapore)", "cloud": "aws", "rate": 0.088},
    {"name": "AWS-AP (Sydney)", "cloud": "aws", "rate": 0.088},
    {"name": "AWS-AP (Mumbai)", "cloud": "aws", "rate": 0.074},
    {"name": "AWS-AP (Tokyo)", "cloud": "aws", "rate": 0.09},
    {"name": "AWS-AP (Seoul)", "cloud": "aws", "rate": 0.086},
    {"name": "Azure-US East", "cloud": "azure", "rate": 0.07},
    {"name": "Azure-US East 2", "cloud": "azure", "rate": 0.07},
    {"name": "Azure-US Central", "cloud": "azure", "rate": 0.079},
    {"name": "Azure-US North Central", "cloud": "azure", "rate": 0.07},
    {"name": "Azure-US South Central", "cloud": "azure", "rate": 0.084},
    {"name": "Azure-US West", "cloud": "azure", "rate": 0.082},
    {"name": "Azure-US West 2", "cloud": "azure", "rate": 0.07},
    {"name": "Azure-US West 3", "cloud": "azure", "rate": 0.07},
    {"name": "Azure-US West Central", "cloud": "azure", "rate": 0.084},
    {"name": "Azure-Brazil South", "cloud": "azure", "rate": 0.112},
    {"name": "Azure-Canada Central", "cloud": "azure", "rate": 0.078},
    {"name": "Azure-Canada East", "cloud": "azure", "rate": 0.078},
    {"name": "Azure-EU North", "cloud": "azure", "rate": 0.078},
    {"name": "Azure-EU West", "cloud": "azure", "rate": 0.084},
    {"name": "Azure-UK South", "cloud": "azure", "rate": 0.081},
    {"name": "Azure-UK West", "cloud": "azure", "rate": 0.085},
    {"name": "Azure-France Central", "cloud": "azure", "rate": 0.082},
    {"name": "Azure-Germany West Central", "cloud": "azure", "rate": 0.084},
    {"name": "Azure-Norway East", "cloud": "azure", "rate": 0.092},
    {"name": "Azure-Switzerland North", "cloud": "azure", "rate": 0.092},
    {"name": "Azure-Switzerland West", "cloud": "azure", "rate": 0.12},
    {"name": "Azure-Sweden Central", "cloud": "azure", "rate": 0.074},
    {"name": "Azure-Asia East", "cloud": "azure", "rate": 0.096},
    {"name": "Azure-Asia Southeast", "cloud": "azure", "rate": 0.088},
    {"name": "Azure-Australia East", "cloud": "azure", "rate": 0.088},
    {"name": "Azure-Australia Southeast", "cloud": "azure", "rate": 0.091},
    {"name": "Azure-Australia Central", "cloud": "azure", "rate": 0.088},
    {"name": "Azure-Australia Central 2", "cloud": "azure", "rate": 0.088},
    {"name": "Azure-Japan East", "cloud": "azure", "rate": 0.09},
    {"name": "Azure-Japan West", "cloud": "azure", "rate": 0.09},
    {"name": "Azure-Korea Central", "cloud": "azure", "rate": 0.086},
    {"name": "Azure-India Central", "cloud": "azure", "rate": 0.074},
    {"name": "Azure-India West", "cloud": "azure", "rate": 0.09},
    {"name": "Azure-India South", "cloud": "azure", "rate": 0.099},
    {"name": "Azure-UAE North", "cloud": "azure", "rate": 0.086},
    {"name": "Azure-South Africa North", "cloud": "azure", "rate": 0.093},
    {"name": "GCP-US (Iowa)", "cloud": "gcp", "rate": 0.07},
    {"name": "GCP-US (South Carolina)", "cloud": "gcp", "rate": 0.07},
    {"name": "GCP-US (Oregon)", "cloud": "gcp", "rate": 0.07},
    {"name": "GCP-US (Nevada)", "cloud": "gcp", "rate": 0.07},
    {"name": "GCP-US (Virginia)", "cloud": "gcp", "rate": 0.07},
    {"name": "GCP-Canada (Quebec)", "cloud": "gcp", "rate": 0.078},
    {"name": "GCP-Europe (England)", "cloud": "gcp", "rate": 0.081},
    {"name": "GCP-Europe (Belgium)", "cloud": "gcp", "rate": 0.082},
    {"name": "GCP-Europe (Frankfurt)", "cloud": "gcp", "rate": 0.084},
    {"name": "GCP-Asia (Singapore)", "cloud": "gcp", "rate": 0.088},
    {"name": "GCP-Asia (Tokyo)", "cloud": "gcp", "rate": 0.09},
    {"name": "GCP-Australia (Sydney)", "cloud": "gcp", "rate": 0.088},
    {"name": "GCP-India (Mumbai)", "cloud": "gcp", "rate": 0.074},
]


@app.get("/api/model")
def get_model():
    return {
        "freeDbuPerUser": FREE_DBU_PER_USER,
        "personaDbu": PERSONA_DBU,
        "personaHints": PERSONA_HINTS,
        "regions": REGIONS,
    }


class CalcRequest(BaseModel):
    users: dict            # {"genieOne": {"beginner": 500, ...}, "genieAgent": {...}}
    region: str = "AWS-US East (N. Virginia)"
    freeDbuPerUser: float = FREE_DBU_PER_USER
    promoPct: float = 0.0  # 0-100


def _rate_for(region: str) -> float:
    for r in REGIONS:
        if r["name"] == region:
            return r["rate"]
    return 0.07


def compute(users: dict, region: str, free_per_user: float, promo_pct: float) -> dict:
    rate = _rate_for(region)
    lines = []
    tot_incurred = tot_free = tot_billed = 0.0
    for product in ("genieOne", "genieAgent"):
        for persona, dbu in PERSONA_DBU[product].items():
            n = float(users.get(product, {}).get(persona, 0) or 0)
            incurred = n * dbu
            free = min(n * free_per_user, incurred)
            billed = max(incurred - free, 0.0)
            tot_incurred += incurred
            tot_free += free
            tot_billed += billed
            lines.append({
                "product": product, "persona": persona, "users": n,
                "dbuPerUser": dbu, "incurred": incurred, "free": free,
                "billed": billed, "cost": billed * rate,
            })
    cost_list = tot_billed * rate
    cost_promo = cost_list * (1 - promo_pct / 100.0)
    return {
        "rate": rate,
        "lines": lines,
        "totals": {
            "incurred": tot_incurred, "free": tot_free, "billed": tot_billed,
            "pctFree": (tot_free / tot_incurred * 100.0) if tot_incurred else 0.0,
            "costListMonthly": cost_list,
            "costPromoMonthly": cost_promo,
            "costListAnnual": cost_list * 12,
            "costPromoAnnual": cost_promo * 12,
        },
    }


@app.post("/api/calculate")
def calculate(req: CalcRequest):
    return JSONResponse(compute(req.users, req.region, req.freeDbuPerUser, req.promoPct))


# --- static frontend ---
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
def health():
    return {"status": "ok"}
