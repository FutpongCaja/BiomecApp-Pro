# ⚡ QUICK START - BiomecApp Pro Online

**Si tienes prisa, sigue esto. Toma ~45 minutos.**

---

## 📋 CHECKLIST RÁPIDO

```
ANTES DE EMPEZAR:
  ☐ Tengo cuenta de GitHub (https://github.com)
  ☐ Tengo cuenta de Google
  ☐ Git está instalado en mi PC
  ☐ Tengo acceso a Google Cloud Console

DURANTE EL PROCESO:
  ☐ He configurado Google Sheets
  ☐ He descargado google_credentials.json
  ☐ He subido el código a GitHub
  ☐ Railway está desplegando
  ☐ La app está online

DESPUÉS:
  ☐ Acceso a la URL online
  ☐ Probé análisis
  ☐ Verificamos Google Sheets
```

---

## 🚀 5 PASOS PRINCIPALES

### 1️⃣ GOOGLE SHEETS (5 min)

```bash
→ https://console.cloud.google.com/
  • New Project: "BiomecApp Pro"
  • Enable: Google Sheets API
  • Enable: Google Drive API
  • Create Service Account
  • Download JSON → google_credentials.json
  • Save in: MediaPipe_Pro/
```

**Resultado:** Archivo `google_credentials.json` en la carpeta

---

### 2️⃣ GITHUB (5 min)

**Opción A (Fácil - Windows):**
```bash
1. Abre carpeta: C:\...\MediaPipe_Pro
2. Doble click: SUBIR_A_GITHUB.bat
3. Ingresa mensaje
4. ¡Listo!
```

**Opción B (Manual):**
```bash
cd C:\Users\herna\OneDrive\Desktop\Claude\MediaPipe\MediaPipe_Pro

git init
git add .
git commit -m "BiomecApp Pro online"
git remote add origin https://github.com/TU_USER/biomecapp-pro.git
git branch -M main
git push -u origin main
```

**Resultado:** Repositorio en GitHub con todo el código

---

### 3️⃣ RAILWAY (10 min)

```bash
→ https://railway.app/
  1. Sign up / Login
  2. New Project
  3. Deploy from GitHub
  4. Select: biomecapp-pro
  5. Settings > Variables
  6. Add: GOOGLE_CREDENTIALS = (contenido del JSON)
  7. Esperar a que termine
```

**Resultado:** URL de tu app: `biomecapp-pro-production.up.railway.app`

---

### 4️⃣ VERIFICAR (5 min)

```bash
1. Abre: https://biomecapp-pro-production.up.railway.app
2. Sube una foto
3. Haz click en "Analizar"
4. Deberías ver resultados ✅
5. Ve a Google Sheets
6. Busca: "BiomecApp Pro - Análisis"
7. Deberías ver tu análisis guardado ✅
```

**Resultado:** App funcionando online + datos en Google Sheets

---

### 5️⃣ COMPARTIR (1 min)

```bash
Tu app está lista en:
https://biomecapp-pro-production.up.railway.app

Comparte este link con tus clientes
Ellos pueden:
  • Subir fotos/videos
  • Ver análisis
  • Tú ves datos en Google Sheets
```

---

## ⚠️ SI ALGO FALLA

**"No puedo encontrar git"**
→ Descarga: https://git-scm.com/

**"GitHub no me reconoce"**
→ Usa token en lugar de contraseña
→ https://github.com/settings/tokens

**"Railway no despliega"**
→ Revisa los logs
→ Verifica que `Procfile` tenga el comando correcto

**"No se conecta a Google Sheets"**
→ Verifica que `google_credentials.json` esté en la carpeta
→ Verifica que la variable `GOOGLE_CREDENTIALS` esté en Railway

**"No aparece en Google Sheets"**
→ Crea manualmente un Sheet llamado "BiomecApp Pro - Análisis"
→ Comparte con el email del service account

---

## 💾 DESPUÉS DE DESPLEGAR

**Para actualizar en el futuro:**

```bash
# 1. Haz cambios locales
# 2. Prueba: python main.py
# 3. Sube a GitHub:

git add .
git commit -m "Descripción del cambio"
git push

# Railway redesplegará automático
```

---

## 📊 RESULTADO ESPERADO

```
┌──────────────────────────────────────┐
│  Tu app online:                      │
│  biomecapp-pro-*.up.railway.app      │
│                                      │
│  Google Sheet automático:            │
│  "BiomecApp Pro - Análisis"          │
│                                      │
│  Actualización automática:           │
│  git push → Railway redeploya       │
└──────────────────────────────────────┘
```

---

## 📞 GUÍAS COMPLETAS

Si necesitas más detalles:

- **Paso a paso detallado:** `PASO_A_PASO_ONLINE.md`
- **Google Sheets:** `SETUP_GOOGLE_SHEETS.md`
- **Documentación:** `README_PRO.md`
- **Resumen:** `RESUMEN_COMPLETO.md`

---

## ✅ ¡LISTO!

Sigue estos 5 pasos y en ~45 minutos tu app estará online 🚀

¿Preguntas? Abre `PASO_A_PASO_ONLINE.md` para más detalles.
