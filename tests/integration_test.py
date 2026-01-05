import httpx
import time
import random
import asyncio

GATEWAY_URL = "http://localhost:8000"


class Colors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


async def simulate_user_activity():
    async with httpx.AsyncClient(timeout=5.0) as client:
        print(f"--- Iniciando simulación de tráfico en Wakanda ---")

        for i in range(1, 21):  # Haremos 20 iteraciones
            print(f"\n[Iteración {i}/20]")

            # 1. Consultar Tráfico
            try:
                resp = await client.get(f"{GATEWAY_URL}/traffic/status")
                print(f"🚦 Tráfico: {resp.status_code} - {resp.json().get('served_by_instance', 'Unknown')}")
            except Exception as e:
                print(f"{Colors.FAIL}🚦 Tráfico: ERROR - {e}{Colors.ENDC}")

            # 2. Consultar Energía
            try:
                resp = await client.get(f"{GATEWAY_URL}/energy/grid")
                print(f"⚡ Energía: {resp.status_code} - {resp.json().get('served_by_instance', 'Unknown')}")
            except Exception as e:
                print(f"{Colors.FAIL}⚡ Energía: ERROR - {e}{Colors.ENDC}")

            # 3. Reportar Alerta de Seguridad (POST aleatorio)
            if random.random() > 0.7:  # 30% de probabilidad
                try:
                    resp = await client.post(f"{GATEWAY_URL}/security/alert", params={"type": "Robo_Vibranium"})
                    print(f"{Colors.WARNING}🛡️  Seguridad (ALERTA): {resp.status_code}{Colors.ENDC}")
                except Exception as e:
                    print(f"{Colors.FAIL}🛡️  Seguridad: ERROR - {e}{Colors.ENDC}")

            # 4. Ajustar Semáforo (POST)
            try:
                resp = await client.post(f"{GATEWAY_URL}/traffic/adjust", params={"green_time": random.randint(30, 60)})
            except:
                pass

            # Pausa aleatoria para simular uso real
            wait_time = random.uniform(0.5, 2.0)
            time.sleep(wait_time)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(simulate_user_activity())