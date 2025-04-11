import os
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
import requests
from tgtg import TgtgClient
from supabase import create_client, Client

app = FastAPI()

# Configuración de Telegram usando variables de entorno
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Error al enviar mensaje a Telegram:", e)

# Configuración de Too Good To Go
TGTG_EMAIL = os.getenv("TGTG_EMAIL")
TGTG_PASSWORD = os.getenv("TGTG_PASSWORD")
tgtg_client = TgtgClient(email=TGTG_EMAIL, password=TGTG_PASSWORD)

# Configuración de Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Modelo Pydantic para recibir el negocio a trackear
class TrackRequest(BaseModel):
    business: str

@app.get("/")
async def root():
    return {"message": "¡TGTG Alertas está corriendo!"}

@app.post("/api/track")
async def track_business(data: TrackRequest):
    resp = supabase.table("tracked_businesses").insert({"business": data.business}).execute()
    return {"status": "tracking_started", "business": data.business}

@app.get("/api/track")
async def list_businesses():
    resp = supabase.table("tracked_businesses").select("*").execute()
    return resp.data

# Tarea en segundo plano: revisar disponibilidad en TGTG
async def check_availability():
    while True:
        # Recoger los negocios almacenados en Supabase
        resp = supabase.table("tracked_businesses").select("*").execute()
        businesses = resp.data if resp.data is not None else []

        # Obtener los items de TGTG
        items = tgtg_client.get_items()

        for business_obj in businesses:
            target_business = business_obj.get("business")
            for item in items:
                name = item.get("display_name", "")
                if name and target_business.lower() in name.lower():
                    if item.get("items_available", 0) > 0:
                        message = f"🛍️ ¡Hay packs disponibles en {name}!"
                        send_telegram_message(message)
        await asyncio.sleep(300)  # Espera 5 minutos

# Iniciar la tarea en segundo plano al arrancar la aplicación
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(check_availability())

# Permite ejecutar la aplicación localmente
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
