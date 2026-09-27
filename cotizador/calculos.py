"""Cálculo de cotizaciones de puertas de baño (batiente y corrediza).

Misma lógica que los notebooks PuertaBatiente.ipynb y PuertaCorrediza.ipynb,
con las tablas de precios leídas desde precios.json.
"""
import json
from pathlib import Path

RUTA_PRECIOS = Path(__file__).with_name("precios.json")


def cargar_precios():
    return json.loads(RUTA_PRECIOS.read_text(encoding="utf-8"))


PRECIOS = cargar_precios()


def buscar_rango(tabla, ancho):
    """Devuelve el rango de la tabla que contiene el ancho, o None."""
    ancho = round(ancho, 3)
    for rango in tabla:
        if rango["min"] <= ancho <= rango["max"]:
            return rango
    return None


def texto_rango(rango):
    if rango is None:
        return "Fuera de rango"
    return f"{rango['min']:.3f} m a {rango['max']:.3f} m"


def _sumar_accesorios(catalogo, seleccionados):
    desglose = [(acc, catalogo[acc]) for acc in seleccionados if acc in catalogo]
    return desglose, sum(costo for _, costo in desglose)


def cotizar_corrediza(ancho_puerta, esmerilado, accesorios, precios=None):
    tablas = (precios or PRECIOS)["corrediza"]
    avisos = []

    rango = buscar_rango(tablas["rangos_ancho"], ancho_puerta)
    if rango:
        precio_base = rango["precio"] + tablas["recargo"]
    else:
        precio_base = 0.0
        avisos.append(f"⚠️ ADVERTENCIA: El ancho ingresado ({ancho_puerta}m) no está dentro de ningún rango de la Tabla 1.")

    precio_esmerilado = tablas["esmerilado"].get(esmerilado, 0.0)
    desglose, precio_accesorios = _sumar_accesorios(tablas["accesorios"], accesorios)

    return {
        "tipo": "Corrediza",
        "ancho_puerta": ancho_puerta,
        "rango": texto_rango(rango),
        "precio_base": precio_base,
        "esmerilado": esmerilado,
        "precio_esmerilado": precio_esmerilado,
        "accesorios": desglose,
        "total": precio_base + precio_esmerilado + precio_accesorios,
        "avisos": avisos,
    }


def cotizar_batiente(ancho_total, ancho_puerta, esmerilado, accesorios, precios=None):
    tablas = (precios or PRECIOS)["batiente"]
    avisos = []

    ancho_fijo = round(ancho_total - ancho_puerta, 3)
    sin_fijo = ancho_fijo <= 0

    # Puerta: el recargo depende de si lleva panel fijo o no
    rango_puerta = buscar_rango(tablas["rangos_puerta"], ancho_puerta)
    if rango_puerta:
        recargo = tablas["recargo_puerta_sin_fijo"] if sin_fijo else tablas["recargo_puerta_con_fijo"]
        precio_puerta = rango_puerta["precio"] + recargo
    else:
        precio_puerta = 0.0
        avisos.append(f"⚠️ ADVERTENCIA: La puerta ({ancho_puerta:.3f}m) está fuera de rango en Tabla 1A.")

    # Panel fijo
    rango_fijo = buscar_rango(tablas["rangos_fijo"], ancho_fijo)
    if rango_fijo:
        precio_fijo = rango_fijo["precio"] + (0.0 if sin_fijo else tablas["recargo_fijo"])
    else:
        precio_fijo = 0.0
    if precio_fijo == 0.0:
        if sin_fijo:
            avisos.append("⚠️ NOTA: Esta puerta no llevara panel fijo.")
        else:
            avisos.append(f"⚠️ ADVERTENCIA: El panel fijo ({ancho_fijo:.3f}m) está fuera de rango en Tabla 1B.")

    precio_esmerilado = tablas["esmerilado"].get(esmerilado, 0.0)
    desglose, precio_accesorios = _sumar_accesorios(tablas["accesorios"], accesorios)
    subtotal_vidrios = precio_puerta + precio_fijo

    return {
        "tipo": "Batiente",
        "ancho_total": ancho_total,
        "ancho_puerta": ancho_puerta,
        "ancho_fijo": ancho_fijo,
        "rango_puerta": texto_rango(rango_puerta),
        "precio_puerta": precio_puerta,
        "rango_fijo": texto_rango(rango_fijo),
        "precio_fijo": precio_fijo,
        "subtotal_vidrios": subtotal_vidrios,
        "esmerilado": esmerilado,
        "precio_esmerilado": precio_esmerilado,
        "accesorios": desglose,
        "total": subtotal_vidrios + precio_esmerilado + precio_accesorios,
        "avisos": avisos,
    }


def formatear(cot, cliente, referencia):
    """Genera el resumen de la cotización como texto, igual que en los notebooks."""
    sep = "=" * 30
    lineas = list(cot["avisos"])
    if cot["tipo"] == "Corrediza":
        lineas += [
            sep,
            "📄 COTIZACIÓN DE PUERTA DE BAÑO CORREDIZA",
            f"👤 Cliente: {cliente} | 📍 Ubicación: {referencia}",
            sep,
            f"📏 Ancho ingresado: {cot['ancho_puerta']:.2f} m",
            f"📌 Rango asignado: [{cot['rango']}]",
            f"💵 Precio Base (Tabla 1): ${cot['precio_base']:.2f}",
        ]
    else:
        lineas += [
            sep,
            "📄 COTIZACIÓN DE PUERTA DE BAÑO BATIENTE + PANEL FIJO",
            f"👤 Cliente: {cliente} | 📍 Ubicación: {referencia}",
            sep,
            f"📏 Ancho Total Ingresado: {cot['ancho_total']:.2f} m",
            f" ├── 🚪 Puerta Batiente: {cot['ancho_puerta']:.2f} m [{cot['rango_puerta']}] -> ${cot['precio_puerta']:.2f}",
            f" └── 🖼️ Panel Fijo: {cot['ancho_fijo']:.2f} m [{cot['rango_fijo']}] -> ${cot['precio_fijo']:.2f}",
            f"💵 Subtotal Cristales: ${cot['subtotal_vidrios']:.2f}",
        ]
    lineas += [
        "-" * 30,
        "🎨 Esmerilado (Tabla 2):",
        f"  • {cot['esmerilado']}: +${cot['precio_esmerilado']:.2f}",
        "-" * 30,
        "🛠️ Accesorios Seleccionados (Tabla 3):",
    ]
    if cot["accesorios"]:
        lineas += [f"  • {nombre}: +${costo:.2f}" for nombre, costo in cot["accesorios"]]
    else:
        lineas.append("  • Ningún accesorio adicional seleccionado.")
    lineas += [sep, f"💰 PRECIO TOTAL A COBRAR: ${cot['total']:.2f}", sep]
    return "\n".join(lineas)
