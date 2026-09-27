"""Endpoint que recibe los mensajes de Telegram (webhook)."""
import hmac
import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cotizador.bot import procesar_update  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        secreto = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
        recibido = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not secreto or not hmac.compare_digest(secreto, recibido):
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
        self._responder(200, "Bot de cotización de puertas activo")

    def _responder(self, codigo, texto):
        self.send_response(codigo)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(texto.encode("utf-8"))
