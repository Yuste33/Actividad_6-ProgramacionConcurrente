import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import itertools

app = FastAPI(title="Wakanda API Gateway")

# Configuración de Consul
CONSUL_URL = "http://consul:8500/v1/catalog/service"

# Cliente HTTP asíncrono global
client = httpx.AsyncClient()

# Diccionario para guardar el iterador de Round Robin para cada servicio
# Estructura: { "traffic_service": cycle([url1, url2]), ... }
rr_generators = {}


async def get_next_service_url(service_name: str):
    """
    1. Consulta a Consul las instancias disponibles del servicio.
    2. Aplica Round-Robin para elegir una.
    """
    try:
        # Consultamos a Consul (DNS o API)
        resp = await client.get(f"{CONSUL_URL}/{service_name}")
        instances = resp.json()

        if not instances:
            raise HTTPException(status_code=503, detail=f"Servicio '{service_name}' no disponible en Consul")

        # Construimos las URLs base de las instancias (ej: http://172.18.0.5:8000)
        service_urls = [
            f"http://{node['ServiceAddress']}:{node['ServicePort']}"
            for node in instances
        ]

        # Gestión del Round Robin
        if service_name not in rr_generators:
            # Creamos un iterador infinito ciclico
            rr_generators[service_name] = itertools.cycle(service_urls)
            # Nota: Si la lista de servicios cambia dinámicamente, esto debería refrescarse.
            # Para esta práctica, simplificamos asumiendo que si cambia, reiniciamos o refrescamos la lógica.
            # Una mejora sería actualizar el ciclo si cambia el número de instancias.
            # Para hacerlo simple: regeneramos el ciclo en cada llamada si queremos ser muy dinámicos,
            # pero perdemos el estado del turno.
            # Vamos a regenerar el ciclo SOLO si detectamos cambio de longitud para mantener la simpleza:
            # (Omitido por brevedad, usaremos el ciclo simple, si falla se reintenta)

        # Obtenemos el siguiente en el turno
        # Truco: para asegurar que el ciclo usa las URLs frescas, en un entorno real
        # se usa una lógica más compleja. Aquí, para que funcione el balanceo simple:
        # Simplemente rotamos manualmente la lista obtenida de consul si no queremos persistir estado complejo.

        # IMPLEMENTACIÓN SIMPLE DE ROUND ROBIN SIN ESTADO PERSISTENTE COMPLEJO:
        # Usamos una variable global contador (o random) es más fácil para empezar,
        # pero itertools.cycle es lo pythonico.
        # Para evitar complicaciones de caché:
        next_url = next(rr_generators[service_name])

        # Pequeña validación por si las instancias cambiaron drásticamente (opcional)
        if next_url not in service_urls:
            rr_generators[service_name] = itertools.cycle(service_urls)
            next_url = next(rr_generators[service_name])

        return next_url

    except Exception as e:
        print(f"Error contactando Consul: {e}")
        raise HTTPException(status_code=503, detail="Error de descubrimiento de servicios")


@app.get("/")
async def root():
    return {"message": "Wakanda Gateway Online"}


# --- PROXY GENÉRICO ---
# Captura cualquier método (GET, POST, etc) a una ruta que empiece por /traffic
# y la redirige al servicio 'traffic_service'

@app.api_route("/traffic/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def traffic_proxy(path: str, request: Request):
    # 1. Descubrir dónde está el servicio
    base_url = await get_next_service_url("traffic_service")

    # 2. Construir la URL destino (ej: http://ip_servicio:8000/status)
    # Nota: 'path' es lo que viene después de /traffic/
    dest_url = f"{base_url}/{path}"

    # 3. Reenviar la petición (Proxy)
    try:
        # Leemos el body si existe
        body = await request.body()

        response = await client.request(
            method=request.method,
            url=dest_url,
            headers=request.headers.raw,  # Pasamos headers originales
            content=body,
            timeout=5.0
        )

        return JSONResponse(content=response.json(), status_code=response.status_code)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Error conectando con microservicio: {exc}")


# Cuando arranca la app
@app.on_event("startup")
async def startup_event():
    print("Gateway iniciado. Conectando a Consul...")


@app.on_event("shutdown")
async def shutdown_event():
    await client.aclose()