"""Punto de entrada en Vercel: recibe todas las peticiones y las reparte.

- POST /api/webhook  → mensajes de Telegram
- GET  /api/setup?secret=<TELEGRAM_WEBHOOK_SECRET>  → registra el webhook y los comandos
"""
import hmac
import json
import os
import traceback
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from cotizador.bot import llamar_telegram, procesar_update

COMANDOS = [
    {"command": "cotizar", "description": "Nueva cotización"},
    {"command": "precios", "description": "Ver tablas de precios"},
    {"command": "id", "description": "Ver tu ID de Telegram"},
]


def secreto_valido(recibido):
    secreto = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
    return bool(secreto) and hmac.compare_digest(secreto, recibido)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if urlparse(self.path).path.rstrip("/") != "/api/webhook":
            self._responder(404, "no encontrado")
            return
        if not secreto_valido(self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")):
            self._responder(403, "forbidden")
            return

        largo = int(self.headers.get("Content-Length", 0))
        try:
            procesar_update(json.loads(self.rfile.read(largo)))
        except Exception:
            # Respondemos 200 igual para que Telegram no reintente el mismo mensaje
            traceback.print_exc()
        self._responder(200, "ok")

    def do_GET(self):
        url = urlparse(self.path)
        if url.path.rstrip("/") == "/api/setup":
            self._setup(parse_qs(url.query).get("secret", [""])[0])
        else:
            self._responder(200, "Bot de cotización de puertas activo")

    def _setup(self, recibido):
        if not secreto_valido(recibido):
            self._responder(403, {"error": "Falta ?secret= correcto (TELEGRAM_WEBHOOK_SECRET)"})
            return
        host = os.environ.get("VERCEL_PROJECT_PRODUCTION_URL") or self.headers.get("Host")
        webhook = f"https://{host}/api/webhook"
        self._responder(200, {
            "webhook_url": webhook,
            "setWebhook": llamar_telegram("setWebhook", {
                "url": webhook,
                "secret_token": os.environ["TELEGRAM_WEBHOOK_SECRET"],
                "allowed_updates": ["message", "callback_query"],
                "drop_pending_updates": True,
            }),
            "setMyCommands": llamar_telegram("setMyCommands", {"commands": COMANDOS}),
        })

    def _responder(self, codigo, datos):
        es_json = not isinstance(datos, str)
        cuerpo = json.dumps(datos, ensure_ascii=False, indent=2) if es_json else datos
        self.send_response(codigo)
        self.send_header("Content-Type", ("application/json" if es_json else "text/plain") + "; charset=utf-8")
        self.end_headers()
        self.wfile.write(cuerpo.encode("utf-8"))
