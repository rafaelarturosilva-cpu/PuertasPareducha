import os
import unittest

from cotizador import bot, calculos


class TestCalculos(unittest.TestCase):
    def test_corrediza_ejemplo_notebook(self):
        cot = calculos.cotizar_corrediza(1.555, "Si", ["Tirador Pomo Negro"])
        self.assertEqual(cot["precio_base"], 285.0)  # 185 + 100
        self.assertEqual(cot["total"], 320.0)        # + 25 esmerilado + 10 tirador

    def test_corrediza_fuera_de_rango(self):
        cot = calculos.cotizar_corrediza(0.5, "No", [])
        self.assertEqual(cot["total"], 0.0)
        self.assertTrue(cot["avisos"])

    def test_batiente_sin_fijo_ejemplo_notebook(self):
        cot = calculos.cotizar_batiente(0.60, 0.60, "No", ["Tirador Toallero"])
        self.assertEqual(cot["precio_puerta"], 190.0)  # 90 + 100
        self.assertEqual(cot["precio_fijo"], 0.0)
        self.assertEqual(cot["total"], 215.0)
        self.assertIn("no llevara panel fijo", cot["avisos"][0])

    def test_batiente_con_fijo(self):
        cot = calculos.cotizar_batiente(0.90, 0.60, "Si", [])
        self.assertEqual(cot["ancho_fijo"], 0.3)
        self.assertEqual(cot["precio_puerta"], 140.0)  # 90 + 50
        self.assertEqual(cot["precio_fijo"], 94.0)     # 44 + 50
        self.assertEqual(cot["total"], 264.0)          # + 30 esmerilado

    def test_formatear(self):
        texto = calculos.formatear(calculos.cotizar_corrediza(1.555, "Si", []), "Ana", "Baño")
        self.assertIn("PRECIO TOTAL A COBRAR: $310.00", texto)


class ChatFalso:
    """Simula Telegram: guarda los mensajes que envía el bot."""

    def __init__(self):
        self.enviados = []
        self.ultimo_id = 0

    def __call__(self, metodo, datos):
        self.enviados.append((metodo, datos))
        self.ultimo_id += 1
        return {"ok": True}

    def ultimo(self, metodo):
        return next(d for m, d in reversed(self.enviados) if m == metodo)


USUARIO = {"id": 111, "is_bot": False}


def mensaje(texto, responde_a=None):
    msg = {"message_id": 1, "chat": {"id": 5}, "from": USUARIO, "text": texto}
    if responde_a:
        msg["reply_to_message"] = {"from": {"is_bot": True}, "text": responde_a}
    return {"message": msg}


def boton(datos, texto_mensaje):
    return {"callback_query": {"id": "q", "from": USUARIO, "data": datos,
                               "message": {"message_id": 9, "chat": {"id": 5}, "text": texto_mensaje}}}


class TestConversacion(unittest.TestCase):
    def setUp(self):
        os.environ["ALLOWED_USER_IDS"] = "111"
        self.api = ChatFalso()

    def enviar(self, update):
        bot.procesar_update(update, self.api)

    def responder_ultimo(self, texto):
        self.enviar(mensaje(texto, self.api.ultimo("sendMessage")["text"]))

    def test_flujo_batiente_completo(self):
        self.enviar(mensaje("/cotizar"))
        self.enviar(boton("tipo:Batiente", self.api.ultimo("sendMessage")["text"]))
        self.responder_ultimo("Eithan Silva")
        self.responder_ultimo("Baño Principal")
        self.responder_ultimo("0,90")
        self.responder_ultimo("0.60 m")

        pregunta = self.api.ultimo("sendMessage")["text"]
        self.assertIn("esmerilado", pregunta)
        self.enviar(boton("esm:Si", pregunta))
        texto_acc = self.api.ultimo("editMessageText")["text"]
        self.enviar(boton("acc:1", texto_acc))   # marca el primer accesorio (Tirador Tipo O, $17)
        self.enviar(boton("fin:1", texto_acc))

        final = self.api.ultimo("editMessageText")["text"]
        self.assertIn("Cliente: Eithan Silva | 📍 Ubicación: Baño Principal", final)
        self.assertIn("Tirador Tipo O: +$17.00", final)
        self.assertIn("PRECIO TOTAL A COBRAR: $281.00", final)  # 140 + 94 + 30 + 17

    def test_medida_invalida_repite_pregunta(self):
        self.enviar(mensaje("/cotizar"))
        self.enviar(boton("tipo:Corrediza", self.api.ultimo("sendMessage")["text"]))
        self.responder_ultimo("Ana")
        self.responder_ultimo("Baño")
        self.responder_ultimo("abc")
        self.assertIn("No entendí la medida", self.api.ultimo("sendMessage")["text"])
        self.responder_ultimo("3")
        self.assertIn("fuera de las medidas", self.api.ultimo("sendMessage")["text"])
        self.responder_ultimo("1.2")
        self.assertIn("esmerilado", self.api.ultimo("sendMessage")["text"])

    def test_usuario_no_autorizado(self):
        os.environ["ALLOWED_USER_IDS"] = "999"
        self.enviar(mensaje("/cotizar"))
        self.assertIn("Tu ID de Telegram es: 111", self.api.ultimo("sendMessage")["text"])


if __name__ == "__main__":
    unittest.main()
