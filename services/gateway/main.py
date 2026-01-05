import httpx
import pybreaker
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import itertools
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

app = FastAPI(title="Wakanda API Gateway")

templates = Jinja2Templates(directory="templates")

def setup_telemetry(service_name):
    resource = Resource(attributes={"service.name": service_name})
    trace.set_tracer_provider(TracerProvider(resource=resource))
    jaeger_exporter = JaegerExporter(
        agent_host_name="jaeger",
        agent_port=6831,
    )
    span_processor = BatchSpanProcessor(jaeger_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    FastAPIInstrumentor.instrument_app(app)


setup_telemetry("gateway_service")

REQUEST_COUNT = Counter("http_requests_total", "Total de peticiones HTTP", ["method", "endpoint", "status"])


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    method = request.method
    path = request.url.path
    try:
        response = await call_next(request)
        status = response.status_code
        REQUEST_COUNT.labels(method=method, endpoint=path, status=status).inc()
        return response
    except Exception as e:
        REQUEST_COUNT.labels(method=method, endpoint=path, status=500).inc()
        raise e


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


CONSUL_URL = "http://consul:8500/v1/catalog/service"
client = httpx.AsyncClient()
rr_generators = {}

circuit_breaker = pybreaker.CircuitBreaker(fail_max=3, reset_timeout=30)


@circuit_breaker
@retry(stop=stop_after_attempt(3), wait=wait_fixed(1),
       retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)))
async def forward_request(method, url, headers, content, params):
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("gateway_forwarding"):
        response = await client.request(
            method=method, url=url, headers=headers, content=content, params=params, timeout=5.0
        )
        if 500 <= response.status_code < 600:
            raise httpx.RequestError(f"Server Error {response.status_code}")
        return response


async def get_next_service_url(service_name: str):
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("consul_discovery"):
        try:
            resp = await client.get(f"{CONSUL_URL}/{service_name}")
            instances = resp.json()
            if not instances:
                raise HTTPException(status_code=503, detail=f"Servicio '{service_name}' no disponible")
            service_urls = [f"http://{node['ServiceAddress']}:{node['ServicePort']}" for node in instances]
            if service_name not in rr_generators:
                rr_generators[service_name] = itertools.cycle(service_urls)
            next_url = next(rr_generators[service_name])
            if next_url not in service_urls:
                rr_generators[service_name] = itertools.cycle(service_urls)
                next_url = next(rr_generators[service_name])
            return next_url
        except Exception as e:
            print(f"Error contactando Consul: {e}")
            raise HTTPException(status_code=503, detail="Error de descubrimiento")



@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.api_route("/{service_key}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def gateway_proxy(service_key: str, path: str, request: Request):
    service_map = {
        "traffic": "traffic_service",
        "energy": "energy_service",
        "water": "water_service",
        "waste": "waste_service",
        "security": "security_service"
    }
    if service_key not in service_map:
        raise HTTPException(status_code=404, detail=f"Servicio '{service_key}' no mapeado")

    target_service = service_map[service_key]

    try:
        base_url = await get_next_service_url(target_service)
    except HTTPException as e:
        raise e

    dest_url = f"{base_url}/{path}"

    try:
        body = await request.body()
        params = request.query_params
        response = await forward_request(
            method=request.method, url=dest_url, headers=request.headers.raw, content=body, params=params
        )
        return JSONResponse(content=response.json(), status_code=response.status_code)
    except pybreaker.CircuitBreakerError:
        raise HTTPException(status_code=503, detail="Circuit Breaker Abierto")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Fallo upstream: {exc}")


@app.on_event("startup")
async def startup_event():
    print("Gateway iniciado.")


@app.on_event("shutdown")
async def shutdown_event():
    await client.aclose()