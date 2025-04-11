import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
import requests
from tgtg import TgtgClient
from supabase import create_client, Client

app = FastAPI()

# -------------------------------
# CONFIGURACIÓN DE TELEGRAM
# -------------------------------
TELEGRAM_TOKEN = "7743706864:AAFCYRNw0sToEfsFKt8ppk2EVAIIRU3hm9Q"
TELEGRAM_CHAT_ID = "319866774"

def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=data)

# -------------------------------
# CONFIGURACIÓN DE TOO GOOD TO GO
# -------------------------------
# Se asume que tgtg-python permite autenticarse con email y contraseña.
TGTG_EMAIL = "tgoodtgalerts@gmail.com"
TGTG_PASSWORD = "Alertas23"
tgtg_client = TgtgClient(email=TGTG_EMAIL, password=TGTG_PASSWORD)

# -------------------------------
# CONFIGURACIÓN DE SUPABASE
# -------------------------------
# Usamos la información que has proporcionado.
SUPABASE_URL = "https://db.fkmjyclogvnfhwaekenb.supabase.co"
SUPABASE_KEY = "postgres://postgres:[Alertas23?]@db.fkmjyclogvnfhwaekenb.supabase.co:5432/postgres"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------------------
# MODELOS Pydantic
# -------------------------------
class TrackRequest(BaseModel):
    business: str

# -------------------------------
# ENDPOINTS DE LA API
# -------------------------------
@app.post("/api/track")
async def track_business(data: TrackRequest):
    # Guarda el negocio en Supabase.
    resp = supabase.table("tracked_businesses").insert({"business": data.business}).execute()
    return {"status": "tracking_started", "business": data.business}

@app.get("/api/track")
async def list_businesses():
    resp = supabase.table("tracked_businesses").select("*").execute()
    return resp.data

# -------------------------------
# BACKGROUND TASK: COMPROBACIÓN DE DISPONIBILIDAD
# -------------------------------
async def check_availability():
    while True:
        # Recupera todos los negocios trackeados desde Supabase.
        resp = supabase.table("tracked_businesses").select("*").execute()
        businesses = resp.data
        if not businesses:
            businesses = []

        # Consulta los items desde TGTG.
        # Se asume que `get_items()` devuelve una lista de diccionarios.
        items = tgtg_client.get_items()
        for business_obj in businesses:
            target_business = business_obj.get("business")
            for item in items:
                name = item.get("display_name")
                if name and target_business.lower() in name.lower():
                    if item.get("items_available", 0) > 0:
                        message = f"🛍️ ¡Hay packs disponibles en {name}!"
                        send_telegram_message(message)
        # Espera 5 minutos (300 segundos)
        await asyncio.sleep(300)

@app.on_event("startup")
async def startup_event():
    # Inicia la tarea en segundo plano al levantar la aplicación.
    asyncio.create_task(check_availability())

# -------------------------------
# EJECUCIÓN DEL SERVIDOR (LOCAL)
# -------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
