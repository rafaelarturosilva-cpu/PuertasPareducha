"""Lógica del bot de Telegram para cotizar puertas.

El bot no guarda estado en servidor: los datos ya ingresados viajan en el
texto de cada mensaje del bot (un resumen visible) y en los botones.
Cuando el usuario responde a una pregunta, el bot lee el resumen del mensaje
al que se respondió y sabe qué dato falta.
"""
import json
import os
import urllib.error
import urllib.request

from . import calculos

ENCABEZADO = "📝 Nueva cotización"

# Datos que se piden por texto, en orden, para cada tipo de puerta
PASOS = {
    "Corrediza": ["Cliente", "Referencia", "Ancho puerta"],
    "Batiente": ["Cliente", "Referencia", "Ancho total", "Ancho puerta"],
}
PREGUNTAS = {
    "Cliente": "✏️ Escribe el nombre del cliente:",
    "Referencia": "✏️ Escribe la referencia del proyecto (ej. Baño Principal):",
    "Ancho total": "✏️ Escribe el ancho total del vano en metros (ej. 0.90):",
    "Ancho puerta": "✏️ Escribe el ancho de la puerta en metros (ej. 1.30):",
}
CAMPOS = ["Tipo", "Cliente", "Referencia", "Ancho total", "Ancho puerta", "Esmerilado"]
CAMPOS_ANCHO = {"Ancho total", "Ancho puerta"}

AYUDA = (
    "Hola 👋 Soy el cotizador de puertas de baño.\n\n"
    "/cotizar – nueva cotización\n"
    "/precios – ver tablas de precios\n"
    "/id – ver tu ID de Telegram"
)


# ---------------------------------------------------------------------------
# API de Telegram
# ---------------------------------------------------------------------------

def llamar_telegram(metodo, datos):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{metodo}",
        data=json.dumps(datos).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        # p. ej. "message is not modified" al pulsar dos veces el mismo botón
        print(f"Telegram {metodo} falló: {e.code} {e.read()[:300]!r}")
        return {"ok": False}


# ---------------------------------------------------------------------------
# Estado dentro del texto del mensaje
# ---------------------------------------------------------------------------

def resumen(estado):
    lineas = [ENCABEZADO]
    for campo in CAMPOS:
        if campo in estado:
            valor = estado[campo]
            if campo in CAMPOS_ANCHO:
                valor = f"{valor:.3f} m"
            lineas.append(f"{campo}: {valor}")
    return "\n".join(lineas)


def leer_estado(texto):
    """Recupera el estado desde el resumen de un mensaje del bot."""
    if not texto or not texto.startswith(ENCABEZADO):
        return None
    estado = {}
    for linea in texto.splitlines()[1:]:
        campo, sep, valor = linea.partition(": ")
        if sep and campo in CAMPOS:
            estado[campo] = float(valor.removesuffix(" m")) if campo in CAMPOS_ANCHO else valor
    return estado if "Tipo" in estado else None


def siguiente_paso(estado):
    for campo in PASOS[estado["Tipo"]]:
        if campo not in estado:
            return campo
    return None


def leer_ancho(texto):
    try:
        ancho = round(float(texto.strip().lower().replace(",", ".").removesuffix("m").strip()), 3)
    except ValueError:
        return None
    return ancho if 0 < ancho < 10 else None


def validar_ancho(estado, campo, ancho):
    """Devuelve un mensaje de error si el ancho no sirve, o None si es válido."""
    tablas = calculos.PRECIOS
    if estado["Tipo"] == "Corrediza":
        tabla = tablas["corrediza"]["rangos_ancho"]
        if not calculos.buscar_rango(tabla, ancho):
            return f"⚠️ {ancho:.3f} m está fuera de las medidas cotizables ({tabla[0]['min']:.3f} a {tabla[-1]['max']:.3f} m)."
    elif campo == "Ancho puerta":
        tabla = tablas["batiente"]["rangos_puerta"]
        if ancho > estado["Ancho total"]:
            return "⚠️ La puerta no puede ser más ancha que el vano."
        if not calculos.buscar_rango(tabla, ancho):
            return f"⚠️ {ancho:.3f} m está fuera de las medidas de puerta batiente ({tabla[0]['min']:.3f} a {tabla[-1]['max']:.3f} m)."
    return None


# ---------------------------------------------------------------------------
# Envío de cada paso
# ---------------------------------------------------------------------------

def teclado(filas):
    return {"inline_keyboard": [[{"text": t, "callback_data": d} for t, d in fila] for fila in filas]}


def teclado_accesorios(tipo, mascara):
    catalogo = list(calculos.PRECIOS[tipo.lower()]["accesorios"].items())
    filas = []
    for i, (nombre, costo) in enumerate(catalogo):
        marca = "✅ " if mascara & (1 << i) else ""
        filas.append([(f"{marca}{nombre} (+${costo:.0f})", f"acc:{mascara ^ (1 << i)}")])
    filas.append([("✔️ Listo, calcular", f"fin:{mascara}"), ("✖️ Cancelar", "cancelar")])
    return teclado(filas)


def pedir_siguiente(api, chat_id, estado, error=None):
    paso = siguiente_paso(estado)
    texto = resumen(estado) + "\n\n"
    if error:
        texto += error + "\n"
    if paso:
        api("sendMessage", {
            "chat_id": chat_id,
            "text": texto + PREGUNTAS[paso],
            "reply_markup": {"force_reply": True, "input_field_placeholder": paso},
        })
    else:
        api("sendMessage", {
            "chat_id": chat_id,
            "text": texto + "🎨 ¿Lleva esmerilado?",
            "reply_markup": teclado([[("Sí", "esm:Si"), ("No", "esm:No")], [("✖️ Cancelar", "cancelar")]]),
        })


def texto_precios():
    p = calculos.PRECIOS
    partes = ["🚪 CORREDIZA – ancho"]
    partes += [f"  {r['min']:.3f}–{r['max']:.3f} m: ${r['precio'] + p['corrediza']['recargo']:.2f}" for r in p["corrediza"]["rangos_ancho"]]
    partes.append(f"  Esmerilado: +${p['corrediza']['esmerilado']['Si']:.2f}")
    partes += [f"  {n}: +${c:.2f}" for n, c in p["corrediza"]["accesorios"].items()]
    b = p["batiente"]
    partes.append(f"\n🚪 BATIENTE – puerta (precio tabla; +${b['recargo_puerta_sin_fijo']:.0f} sin fijo, +${b['recargo_puerta_con_fijo']:.0f} con fijo)")
    partes += [f"  {r['min']:.3f}–{r['max']:.3f} m: ${r['precio']:.2f}" for r in b["rangos_puerta"]]
    partes.append(f"🖼️ Panel fijo (precio tabla; +${b['recargo_fijo']:.0f} cuando lleva fijo)")
    partes += [f"  {r['min']:.3f}–{r['max']:.3f} m: ${r['precio']:.2f}" for r in b["rangos_fijo"]]
    partes.append(f"  Esmerilado: +${b['esmerilado']['Si']:.2f}")
    partes += [f"  {n}: +${c:.2f}" for n, c in b["accesorios"].items()]
    return "\n".join(partes)


def calcular(estado, mascara):
    tipo = estado["Tipo"]
    nombres = list(calculos.PRECIOS[tipo.lower()]["accesorios"])
    accesorios = [n for i, n in enumerate(nombres) if mascara & (1 << i)]
    if tipo == "Corrediza":
        cot = calculos.cotizar_corrediza(estado["Ancho puerta"], estado["Esmerilado"], accesorios)
    else:
        cot = calculos.cotizar_batiente(estado["Ancho total"], estado["Ancho puerta"], estado["Esmerilado"], accesorios)
    return calculos.formatear(cot, estado["Cliente"], estado["Referencia"])


# ---------------------------------------------------------------------------
# Manejo de updates
# ---------------------------------------------------------------------------

def usuarios_permitidos():
    valor = os.environ.get("ALLOWED_USER_IDS", "")
    return {int(x) for x in valor.replace(" ", "").split(",") if x}


def procesar_update(update, api=llamar_telegram):
    if "callback_query" in update:
        procesar_boton(update["callback_query"], api)
    elif "message" in update:
        procesar_mensaje(update["message"], api)


def autorizado(usuario, chat_id, api):
    if usuario["id"] in usuarios_permitidos():
        return True
    api("sendMessage", {
        "chat_id": chat_id,
        "text": f"🔒 No estás autorizado para usar este bot.\nTu ID de Telegram es: {usuario['id']}",
    })
    return False


def procesar_mensaje(msg, api):
    chat_id = msg["chat"]["id"]
    texto = (msg.get("text") or "").strip()
    comando = texto.split()[0].split("@")[0].lower() if texto.startswith("/") else None

    if comando == "/id":
        api("sendMessage", {"chat_id": chat_id, "text": f"Tu ID de Telegram es: {msg['from']['id']}"})
        return
    if not autorizado(msg["from"], chat_id, api):
        return

    if comando == "/cotizar":
        api("sendMessage", {
            "chat_id": chat_id,
            "text": ENCABEZADO + "\n\n🚪 ¿Qué tipo de puerta?",
            "reply_markup": teclado([[("Batiente", "tipo:Batiente"), ("Corrediza", "tipo:Corrediza")]]),
        })
        return
    if comando == "/precios":
        api("sendMessage", {"chat_id": chat_id, "text": texto_precios()})
        return

    respuesta_a = msg.get("reply_to_message") or {}
    estado = leer_estado(respuesta_a.get("text")) if respuesta_a.get("from", {}).get("is_bot") else None
    paso = siguiente_paso(estado) if estado else None
    if comando or not paso or not texto:
        api("sendMessage", {"chat_id": chat_id, "text": AYUDA})
        return

    if paso in CAMPOS_ANCHO:
        ancho = leer_ancho(texto)
        error = "⚠️ No entendí la medida. Escríbela en metros, por ejemplo 1.30" if ancho is None else validar_ancho(estado, paso, ancho)
        if error:
            pedir_siguiente(api, chat_id, estado, error)
            return
        estado[paso] = ancho
    else:
        estado[paso] = texto.splitlines()[0].strip()[:60]
    pedir_siguiente(api, chat_id, estado)


def procesar_boton(query, api):
    msg = query.get("message") or {}
    chat_id = msg.get("chat", {}).get("id")
    datos = query.get("data", "")
    api("answerCallbackQuery", {"callback_query_id": query["id"]})
    if chat_id is None or not autorizado(query["from"], chat_id, api):
        return

    def editar(texto, markup=None):
        payload = {"chat_id": chat_id, "message_id": msg["message_id"], "text": texto}
        if markup:
            payload["reply_markup"] = markup
        api("editMessageText", payload)

    accion, _, valor = datos.partition(":")
    if accion == "cancelar":
        editar("✖️ Cotización cancelada. Usa /cotizar para empezar otra.")
        return
    if accion == "tipo" and valor in PASOS:
        editar(f"{ENCABEZADO}\n\n🚪 Tipo elegido: {valor}")
        pedir_siguiente(api, chat_id, {"Tipo": valor})
        return

    estado = leer_estado(msg.get("text"))
    if not estado or siguiente_paso(estado):
        editar("⚠️ Este mensaje ya no es válido. Usa /cotizar para empezar de nuevo.")
        return

    if accion == "esm" and valor in ("Si", "No"):
        estado["Esmerilado"] = valor
        editar(resumen(estado) + "\n\n🛠️ Elige los accesorios y pulsa Listo:", teclado_accesorios(estado["Tipo"], 0))
    elif accion == "acc" and "Esmerilado" in estado:
        editar(resumen(estado) + "\n\n🛠️ Elige los accesorios y pulsa Listo:", teclado_accesorios(estado["Tipo"], int(valor)))
    elif accion == "fin" and "Esmerilado" in estado:
        editar(calcular(estado, int(valor)))
        api("sendMessage", {"chat_id": chat_id, "text": "Usa /cotizar para una nueva cotización."})
