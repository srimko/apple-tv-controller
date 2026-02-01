"""Serveur HTTP pour controle a distance."""

from __future__ import annotations

import asyncio
from typing import Callable

from aiohttp import web

from .config import HTTP_REQUEST_TIMEOUT, SERVER_PORT, logger
from .connection import connect_atv, scan_devices, select_device
from .exceptions import AppleTVError
from .scenarios import load_scenarios, run_scenario


async def http_health(request: web.Request) -> web.Response:
    """Health check."""
    return web.json_response({"status": "ok"})


async def http_list_scenarios(request: web.Request) -> web.Response:
    """Liste les scenarios disponibles."""
    scenarios = load_scenarios()
    return web.json_response({"scenarios": list(scenarios.keys())})


async def _execute_scenario(name: str, device_name: str) -> dict:
    """Execute un scenario (logique separee pour le timeout)."""
    devices = await scan_devices()
    device = select_device(devices, device_name)

    async with connect_atv(device) as atv:
        success = await run_scenario(atv, name)

    return {
        "success": success,
        "scenario": name,
        "device": device_name,
    }


async def http_run_scenario(request: web.Request) -> web.Response:
    """Execute un scenario avec timeout."""
    name = request.match_info.get("name")
    device_name = request.query.get("device", "Salon")

    scenarios = load_scenarios()
    if name not in scenarios:
        return web.json_response(
            {"success": False, "error": f"Scenario '{name}' non trouve"},
            status=404,
        )

    try:
        # Timeout global pour toute l'operation
        result = await asyncio.wait_for(
            _execute_scenario(name, device_name),
            timeout=HTTP_REQUEST_TIMEOUT
        )
        return web.json_response(result)

    except asyncio.TimeoutError:
        logger.error(f"Timeout lors de l'execution du scenario '{name}'")
        return web.json_response(
            {"success": False, "error": "Timeout - operation trop longue"},
            status=504,
        )
    except AppleTVError as e:
        logger.error(f"Erreur Apple TV: {e}")
        return web.json_response(
            {"success": False, "error": str(e)},
            status=400,
        )
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        return web.json_response(
            {"success": False, "error": "Erreur interne du serveur"},
            status=500,
        )


async def http_shutdown(request: web.Request) -> web.Response:
    """Arrete le serveur proprement."""
    logger.info("Arret du serveur demande...")

    async def _shutdown():
        await asyncio.sleep(0.5)
        raise SystemExit(0)

    asyncio.create_task(_shutdown())
    return web.json_response({"status": "shutting_down"})


@web.middleware
async def timeout_middleware(
    request: web.Request,
    handler: Callable[[web.Request], web.Response]
) -> web.Response:
    """Middleware pour appliquer un timeout global aux requetes."""
    try:
        return await asyncio.wait_for(
            handler(request),
            timeout=HTTP_REQUEST_TIMEOUT + 10
        )
    except asyncio.TimeoutError:
        return web.json_response(
            {"success": False, "error": "Request timeout"},
            status=504,
        )


async def run_server(port: int = SERVER_PORT) -> None:
    """Lance le serveur HTTP."""
    app = web.Application(
        middlewares=[timeout_middleware],
        client_max_size=1024 * 100,  # Limite 100KB par requete
    )
    app.router.add_get("/health", http_health)
    app.router.add_get("/scenarios", http_list_scenarios)
    app.router.add_post("/scenario/{name}", http_run_scenario)
    app.router.add_post("/shutdown", http_shutdown)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)

    print(f"Serveur HTTP demarre sur http://0.0.0.0:{port}")
    print("Endpoints:")
    print("  GET  /health")
    print("  GET  /scenarios")
    print("  POST /scenario/{name}?device=Salon")
    print("  POST /shutdown")
    print(f"\nTimeout requetes: {HTTP_REQUEST_TIMEOUT}s")
    print("Ctrl+C pour arreter")

    await site.start()

    # Boucle infinie
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await runner.cleanup()
