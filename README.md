# Wakanda Smart City - Sistema de Gestión de Servicios

Arquitectura de microservicios para la gestión inteligente de Wakanda, implementada en Python con FastAPI.

## 🏗️ Arquitectura
El sistema consta de 6 microservicios contenerizados:
1.  **Gateway:** Punto de entrada único con balanceo de carga y circuit breaker.
2.  **Tráfico / Energía / Agua / Residuos / Seguridad:** Servicios de dominio.
3.  **Infraestructura:** Consul (Discovery), Prometheus (Métricas), Jaeger (Tracing).

## 🚀 Cómo ejecutar
1.  Requisitos: Docker y Docker Compose.
2.  Clonar el repositorio.
3.  Ejecutar:
    ```bash
    docker-compose up -d --build
    ```
4.  Ejecutar script de pruebas (opcional):
    ```bash
    pip install httpx
    python tests/integration_test.py
    ```

## 🔗 Endpoints Principales
* **Gateway:** http://localhost:8000
* **Consul UI:** http://localhost:8500
* **Jaeger UI:** http://localhost:16686
* **Grafana:** http://localhost:3000

## 🧪 Pruebas Realizadas
Se incluye un script de integración que valida el enrutamiento dinámico y la tolerancia a fallos mediante inyección de errores simulados.
