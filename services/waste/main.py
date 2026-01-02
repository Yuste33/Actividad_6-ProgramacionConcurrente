import socket
import os
from fastapi import FastAPI
import requests

app = FastAPI(title="Waste Service")

CONSUL_HOST = os.getenv("CONSUL_HOST", "consul")
CONSUL_PORT = int(os.getenv("CONSUL_PORT", 8500))
SERVICE_NAME = "waste_service"
INSTANCE_ID = socket.gethostname()
SERVICE_PORT = 8000
SERVICE_IP = socket.gethostbyname(INSTANCE_ID)

waste_state = {
    "container_001": "80%",
    "container_002": "20%",
    "trucks_active": 3
}

def register_to_consul():
    url = f"http://{CONSUL_HOST}:{CONSUL_PORT}/v1/agent/service/register"
    data = {
        "Name": SERVICE_NAME,
        "ID": INSTANCE_ID,
        "Address": SERVICE_IP,
        "Port": SERVICE_PORT,
        "Tags": ["wakanda", "waste"],
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

@app.get("/containers")
def get_waste_status():
    response = waste_state.copy()
    response["served_by_instance"] = INSTANCE_ID
    return response

@app.post("/request_pickup")
def request_pickup(container_id: str):
    waste_state[container_id] = "0%"
    return {"message": "Recogida programada", "target": container_id}