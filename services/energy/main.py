import socket
import os
from fastapi import FastAPI
import requests

app = FastAPI(title="Energy Service")

CONSUL_HOST = os.getenv("CONSUL_HOST", "consul")
CONSUL_PORT = int(os.getenv("CONSUL_PORT", 8500))
SERVICE_NAME = "energy_service"
INSTANCE_ID = socket.gethostname()
SERVICE_PORT = 8000
SERVICE_IP = socket.gethostbyname(INSTANCE_ID)

energy_state = {
    "grid_status": "STABLE",
    "total_consumption_kw": 14500,
    "renewable_contribution": "25%"
}

def register_to_consul():
    url = f"http://{CONSUL_HOST}:{CONSUL_PORT}/v1/agent/service/register"
    data = {
        "Name": SERVICE_NAME,
        "ID": INSTANCE_ID,
        "Address": SERVICE_IP,
        "Port": SERVICE_PORT,
        "Tags": ["wakanda", "energy"],
        "Check": {
            "HTTP": f"http://{SERVICE_IP}:{SERVICE_PORT}/health",
            "Interval": "10s",
            "Timeout": "5s"
        }
    }
    try:
        requests.put(url, json=data)
        print(f"Registrado en Consul: {INSTANCE_ID}")
    except Exception as e:
        print(f"Error conectando a Consul: {e}")

def deregister_from_consul():
    url = f"http://{CONSUL_HOST}:{CONSUL_PORT}/v1/agent/service/deregister/{INSTANCE_ID}"
    try:
        requests.put(url)
    except:
        pass

@app.on_event("startup")
async def startup_event():
    register_to_consul()

@app.on_event("shutdown")
async def shutdown_event():
    deregister_from_consul()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/grid")
def get_grid_status():
    response = energy_state.copy()
    response["served_by_instance"] = INSTANCE_ID
    return response

@app.post("/report")
def report_consumption(value: int):
    return {"message": "Consumo registrado", "current_load": value}