import socket
import os
from fastapi import FastAPI
import requests

app = FastAPI(title="Security Service")

CONSUL_HOST = os.getenv("CONSUL_HOST", "consul")
CONSUL_PORT = int(os.getenv("CONSUL_PORT", 8500))
SERVICE_NAME = "security_service"
INSTANCE_ID = socket.gethostname()
SERVICE_PORT = 8000
SERVICE_IP = socket.gethostbyname(INSTANCE_ID)

security_state = {
    "alert_level": "LOW",
    "active_units": 5,
    "last_incident": "None"
}

def register_to_consul():
    url = f"http://{CONSUL_HOST}:{CONSUL_PORT}/v1/agent/service/register"
    data = {
        "Name": SERVICE_NAME,
        "ID": INSTANCE_ID,
        "Address": SERVICE_IP,
        "Port": SERVICE_PORT,
        "Tags": ["wakanda", "security"],
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

@app.get("/events")
def get_security_events():
    response = security_state.copy()
    response["served_by_instance"] = INSTANCE_ID
    return response

@app.post("/alert")
def trigger_alert(type: str):
    security_state["alert_level"] = "HIGH"
    security_state["last_incident"] = type
    return {"message": "ALERTA RECIBIDA", "protocol": "ACTIVATE_RESPONSE"}