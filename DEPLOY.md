# BiomecApp — Guía de Deploy en Railway

## Qué hace esta app
Analiza postura en sentadilla y peso muerto desde video o cámara en vivo.
Usa MediaPipe para medir ángulos articulares y Gemini para dar feedback como entrenador.

---

## Paso 1 — Conseguí tu Gemini API Key (gratis)

1. Abrí [aistudio.google.com](https://aistudio.google.com)
2. Hacé clic en **"Get API Key"** → **"Create API key"**
3. Copiá la key (empieza con `AIza...`)
4. Guardala, la vas a cargar en la app

---

## Paso 2 — Subí el código a GitHub

1. Andá a [github.com](https://github.com) → **"New repository"**
2. Nombre: `biomecapp` (o el que quieras), público o privado
3. Subí estos 4 archivos:
   - `main.py`
   - `requirements.txt`
   - `Procfile`
   - `railway.toml`

   Podés arrastrarlos directamente en la pantalla de GitHub.

---

## Paso 3 — Deploy en Railway

1. Andá a [railway.app](https://railway.app) y creá una cuenta (es gratis con GitHub)
2. Hacé clic en **"New Project"** → **"Deploy from GitHub repo"**
3. Seleccioná tu repo `biomecapp`
4. Railway detecta automáticamente el `Procfile` y arranca el deploy
5. Esperá ~3 minutos mientras instala todo

---

## Paso 4 — Obtené tu URL pública

1. En Railway, una vez que el deploy termina, andá a **Settings → Domains**
2. Hacé clic en **"Generate Domain"**
3. Te da una URL tipo: `https://biomecapp-production.up.railway.app`
4. **Esa URL funciona desde cualquier celular del mundo**

---

## Paso 5 — Primer uso

1. Abrí la URL en cualquier celular
2. Tocá el ⚙️ arriba a la derecha
3. Pegá tu Gemini API Key y guardá
4. Seleccioná el ejercicio → subí un video o usá la cámara
5. Tocá **"Analizar Movimiento"**

---

## Notas importantes

- **La cámara en vivo requiere HTTPS** — Railway lo da automáticamente ✅
- **Costo**: Railway tiene free tier generoso (~500 horas/mes). Para un centro pequeño alcanza.
- **Gemini**: El free tier da 1.500 análisis por día — más que suficiente.
- **Mejor resultado**: Filmar de costado, cuerpo completo visible, buena iluminación.

---

## Si algo falla

- Si el deploy falla, revisá los logs en Railway → **"Deployments"** → **"View Logs"**
- El error más común es falta de memoria. En ese caso, en Railway ve a **Settings → Resources** y aumentá la RAM a 512MB.
