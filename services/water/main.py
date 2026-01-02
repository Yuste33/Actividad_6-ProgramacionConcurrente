import socket
import os
from fastapi import FastAPI
import requests

app = FastAPI(title="Water Service")

CONSUL_HOST = os.getenv("CONSUL_HOST", "consul")
CONSUL_PORT = int(os.getenv("CONSUL_PORT", 8500))
SERVICE_NAME = "water_service"
INSTANCE_ID = socket.gethostname()
SERVICE_PORT = 8000
SERVICE_IP = socket.gethostbyname(INSTANCE_ID)

water_state = {
    "pressure_psi": 65,
    "quality": "GOOD",
    "leaks_detected": 0
}

def register_to_consul():
    url = f"http://{CONSUL_HOST}:{CONSUL_PORT}/v1/agent/service/register"
    data = {
        "Name": SERVICE_NAME,
        "ID": INSTANCE_ID,
        "Address": SERVICE_IP,
        "Port": SERVICE_PORT,
        "Tags": ["wakanda", "water"],
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

@app.get("/pressure")
def get_water_pressure():
    response = water_state.copy()
    response["served_by_instance"] = INSTANCE_ID
    return response

@app.post("/leak_alert")
def report_leak(location: str):
    water_state["leaks_detected"] += 1
    return {"alert": "RECEIVED", "location": location}