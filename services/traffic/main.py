import socket
import os
from fastapi import FastAPI, Request
import requests
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

app = FastAPI(title="Traffic Service")
def setup_telemetry(service_name):
    resource = Resource(attributes={"service.name": service_name})
    trace.set_tracer_provider(TracerProvider(resource=resource))
    jaeger_exporter = JaegerExporter(agent_host_name="jaeger", agent_port=6831)
    span_processor = BatchSpanProcessor(jaeger_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    FastAPIInstrumentor.instrument_app(app)

setup_telemetry("traffic_service")


REQUEST_COUNT = Counter("traffic_requests_total", "Total requests traffic", ["endpoint"])

@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    response = await call_next(request)
    REQUEST_COUNT.labels(endpoint=request.url.path).inc()
    return response

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

CONSUL_HOST = os.getenv("CONSUL_HOST", "consul")
CONSUL_PORT = int(os.getenv("CONSUL_PORT", 8500))
SERVICE_NAME = "traffic_service"
INSTANCE_ID = socket.gethostname()
SERVICE_PORT = 8000
SERVICE_IP = socket.gethostbyname(INSTANCE_ID)

traffic_state = {
    "intersection_id": "I-101",
    "signal_phase": "RED",
    "vehicle_count": 45,
    "average_speed": 30.5
}

def register_to_consul():
    url = f"http://{CONSUL_HOST}:{CONSUL_PORT}/v1/agent/service/register"
    data = {
        "Name": SERVICE_NAME,
        "ID": INSTANCE_ID,
        "Address": SERVICE_IP,
        "Port": SERVICE_PORT,
        "Tags": ["wakanda", "traffic"],
        "Check": {
            "HTTP": f"http://{SERVICE_IP}:{SERVICE_PORT}/health",
            "Interval": "10s",
            "Timeout": "5s"
        }
    }
    try:
        requests.put(url, json=data)
    except Exception as e:
        print(f"Error consul: {e}")

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

@app.get("/status")
def get_traffic_status():
    response = traffic_state.copy()
    response["served_by_instance"] = INSTANCE_ID
    return response

@app.post("/adjust")
def adjust_traffic(green_time: int):
    traffic_state["signal_phase"] = "GREEN"
    return {"message": f"Semaforo ajustado a {green_time}s", "status": "GREEN"}