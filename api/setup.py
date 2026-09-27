"""Registra el webhook y los comandos del bot en Telegram.

Visitar una vez tras desplegar:  https://<tu-proyecto>.vercel.app/api/setup?secret=<TELEGRAM_WEBHOOK_SECRET>
"""
import hmac
import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cotizador.bot import llamar_telegram  # noqa: E402

COMANDOS = [
    {"command": "cotizar", "description": "Nueva cotización"},
    {"command": "precios", "description": "Ver tablas de precios"},
    {"command": "id", "description": "Ver tu ID de Telegram"},
]


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        secreto = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
        recibido = parse_qs(urlparse(self.path).query).get("secret", [""])[0]
        if not secreto or not hmac.compare_digest(secreto, recibido):
            self._responder(403, {"error": "Falta ?secret= correcto (TELEGRAM_WEBHOOK_SECRET)"})
            return

        host = os.environ.get("VERCEL_PROJECT_PRODUCTION_URL") or self.headers.get("Host")
        url = f"https://{host}/api/webhook"
        resultado = {
            "webhook_url": url,
            "setWebhook": llamar_telegram("setWebhook", {
                "url": url,
                "secret_token": secreto,
                "allowed_updates": ["message", "callback_query"],
                "drop_pending_updates": True,
            }),
            "setMyCommands": llamar_telegram("setMyCommands", {"commands": COMANDOS}),
        }
        self._responder(200, resultado)

    def _responder(self, codigo, datos):
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(datos, ensure_ascii=False, indent=2).encode("utf-8"))
