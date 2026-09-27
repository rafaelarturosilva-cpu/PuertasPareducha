# Pareducha
Calculo de Puertas de Bano

- `PuertaBatiente.ipynb` y `PuertaCorrediza.ipynb`: los cálculos originales en Colab.
- `cotizador/`: la misma lógica como módulo de Python, más un bot de Telegram.
- `cotizador/precios.json`: **tablas de precios**. Edita este archivo para cambiar precios, rangos o accesorios.

## Bot de Telegram

Escribe `/cotizar` al bot, elige el tipo de puerta, responde las medidas y marca
esmerilado y accesorios con botones. El bot devuelve la cotización completa.

Otros comandos: `/precios` (ver tablas) e `/id` (ver tu ID de Telegram).

### Puesta en marcha (una sola vez)

1. **Crear el bot**: en Telegram, habla con [@BotFather](https://t.me/BotFather),
   envía `/newbot` y guarda el *token* que te entrega.
2. **Crear el proyecto en Vercel**: en [vercel.com/new](https://vercel.com/new)
   importa este repositorio (sin cambiar ninguna opción).
3. **Variables de entorno** (Vercel → proyecto → Settings → Environment Variables):

   | Variable | Valor |
   |---|---|
   | `TELEGRAM_BOT_TOKEN` | El token de BotFather |
   | `TELEGRAM_WEBHOOK_SECRET` | Una clave inventada, solo letras, números, `_` o `-` (ej. `puertas_2026_xyz`) |
   | `ALLOWED_USER_IDS` | IDs de Telegram autorizados, separados por coma (ej. `12345678,87654321`) |

   Luego ve a **Deployments** y pulsa **Redeploy** para que tome las variables.
4. **Conectar Telegram con Vercel**: abre en el navegador
   `https://<tu-proyecto>.vercel.app/api/setup?secret=<TELEGRAM_WEBHOOK_SECRET>`.
   Debe responder con `"ok": true`.
5. **Autorizarte**: escribe `/id` al bot, copia tu ID en `ALLOWED_USER_IDS` y vuelve a hacer Redeploy.
   Cualquier persona que no esté en esa lista recibe un mensaje de "no autorizado".

Cada vez que hagas `git push` a `main`, Vercel vuelve a desplegar automáticamente
(por ejemplo, después de cambiar `precios.json`).

### Pruebas

```bash
python -m unittest -v tests.test_cotizador
```
