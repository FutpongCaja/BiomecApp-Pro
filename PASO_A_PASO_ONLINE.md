# 🚀 BIOMECAPP PRO - PASO A PASO PARA PONER ONLINE

**Tiempo total: ~30-45 minutos**

---

## 📋 ÍNDICE
1. [Configurar Google Sheets](#1-configurar-google-sheets)
2. [Preparar el proyecto localmente](#2-preparar-el-proyecto-localmente)
3. [Desplegar con Railway](#3-desplegar-en-railway)
4. [Verificar que funciona online](#4-verificar-que-funciona-online)

---

## 1. CONFIGURAR GOOGLE SHEETS

### PASO 1.1: Crear Proyecto en Google Cloud Console

1. Ve a: **https://console.cloud.google.com/**
2. Haz clic en el **selector de proyectos** (arriba a la izquierda)
3. Haz clic en **"Nuevo proyecto"**
4. **Nombre**: `BiomecApp Pro`
5. **ID de proyecto**: Se genera automático
6. Haz clic en **"Crear"**
7. Espera a que se cree (puede tardar 1-2 minutos)

### PASO 1.2: Habilitar APIs

**Para Google Sheets API:**
1. En la barra de búsqueda, busca: `Google Sheets API`
2. Haz clic en el resultado
3. Haz clic en **"Habilitar"**

**Para Google Drive API:**
1. En la barra de búsqueda, busca: `Google Drive API`
2. Haz clic en el resultado
3. Haz clic en **"Habilitar"**

### PASO 1.3: Crear Cuenta de Servicio

1. En el menú lateral, ve a **"Credenciales"**
2. Haz clic en **"+ Crear credenciales"** (arriba)
3. Selecciona **"Cuenta de servicio"**
4. Completa el formulario:
   - **Nombre de cuenta de servicio**: `biomecapp-pro`
   - **ID de la cuenta de servicio**: Se genera automático
   - Haz clic en **"Crear y continuar"**

5. En **"Otorgar acceso al proyecto"**:
   - Rol: Busca y selecciona **"Editor"**
   - Haz clic en **"Continuar"**

6. En **"Crear clave"**:
   - Haz clic en **"Crear clave"**
   - Selecciona **"JSON"**
   - Automáticamente descargará un archivo `[ID-número].json`

### PASO 1.4: Guardar las Credenciales

1. **Renombra** el archivo descargado a: `google_credentials.json`

2. **Colócalo en la carpeta MediaPipe_Pro**:
   ```
   C:\Users\herna\OneDrive\Desktop\Claude\MediaPipe\MediaPipe_Pro\google_credentials.json
   ```

3. **Verifica** que esté en la carpeta correcta:
   - Abre el explorador
   - Ve a: `MediaPipe > MediaPipe_Pro`
   - Deberías ver: `google_credentials.json`

✅ **Google Sheets configurado**

---

## 2. PREPARAR EL PROYECTO LOCALMENTE

### PASO 2.1: Verificar Archivos

Abre una terminal/PowerShell y ve a la carpeta:
```powershell
cd C:\Users\herna\OneDrive\Desktop\Claude\MediaPipe\MediaPipe_Pro
```

Verifica que existan estos archivos:
```
✓ main.py
✓ google_sheets_integration.py
✓ requirements.txt
✓ google_credentials.json (el que acabas de descargar)
✓ Dockerfile
✓ Procfile
✓ railway.toml
```

Comando para verificar:
```powershell
ls -la
```

### PASO 2.2: Probar Localmente

```bash
# Instala dependencias
pip install -r requirements.txt

# Inicia la app
python main.py
```

**Deberías ver:**
```
✅ Conectado a Google Sheets: BiomecApp Pro - Análisis
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Abre en el navegador: **http://localhost:8000**

**Si ves la interfaz web, ¡funciona! ✅**

Presiona `Ctrl+C` para detener

### PASO 2.3: Probar que Guarda en Google Sheets

1. En la web, haz una prueba:
   - Selecciona "Sentadilla"
   - Sube una foto
   - Haz clic en "Analizar"

2. Ve a **Google Sheets**:
   - https://docs.google.com/spreadsheets/
   - Busca: "BiomecApp Pro - Análisis"
   - Deberías ver una fila con tus datos ✅

**Si está todo bien, continuamos al despliegue online**

---

## 3. DESPLEGAR EN RAILWAY

Railway es una plataforma para desplegar apps **GRATIS** (el primer mes tienes crédito)

### PASO 3.1: Crear Cuenta en Railway

1. Ve a: **https://railway.app/**
2. Haz clic en **"Create Account"**
3. Selecciona **"GitHub"** (o Google)
4. Completa el registro

### PASO 3.2: Conectar tu Repositorio GitHub

1. Abre GitHub: **https://github.com/**
2. Crea un **nuevo repositorio**:
   - **Nombre**: `biomecapp-pro`
   - **Descripción**: `BiomecApp Pro - Análisis Biomecánico con Google Sheets`
   - **Público**
   - Haz clic en **"Create repository"**

### PASO 3.3: Subir el Código a GitHub

En PowerShell/Terminal (en la carpeta MediaPipe_Pro):

```bash
# Inicializar git
git init

# Agregar archivo de configuración git
echo ".env" > .gitignore
echo "*.pyc" >> .gitignore
echo "__pycache__" >> .gitignore
echo ".DS_Store" >> .gitignore

# Agregar todos los archivos
git add .

# Commit inicial
git commit -m "BiomecApp Pro - Initial commit"

# Cambiar rama a main (si es necesario)
git branch -M main

# Agregar remote (REEMPLAZA USERNAME y REPO)
git remote add origin https://github.com/TU_USERNAME/biomecapp-pro.git

# Subir a GitHub
git push -u origin main
```

**Reemplaza:**
- `TU_USERNAME` con tu nombre de usuario de GitHub

### PASO 3.4: Configurar Railway

1. Vuelve a **https://railway.app/**
2. Haz clic en **"New Project"**
3. Selecciona **"Deploy from GitHub"**
4. **Conecta tu GitHub** (si te lo pide)
5. Selecciona el repositorio: `biomecapp-pro`
6. Haz clic en **"Deploy"**

Railway empezará a construir la app automáticamente

### PASO 3.5: Agregar Variables de Entorno

Railway necesita saber dónde está el archivo `google_credentials.json`

1. En el dashboard de Railway, ve a tu proyecto
2. Haz clic en **"Settings"**
3. Ve a **"Variables"**
4. Necesitamos agregar el contenido de `google_credentials.json` como variable

**Opción A: Copiar el contenido del JSON**
```bash
# En tu PowerShell, ve a la carpeta y copia el contenido:
Get-Content google_credentials.json | Set-Clipboard
```

5. En Railway, en **"Variables"**, agrega:
   - **Nombre**: `GOOGLE_CREDENTIALS`
   - **Valor**: Pega el contenido del JSON que copiaste

6. Haz clic en **"Save"**

### PASO 3.6: Modificar main.py para usar Variable de Entorno

En tu máquina local, edita `main.py`:

**Busca esta línea (alrededor de la línea 27):**
```python
init_sheets_manager("google_credentials.json")
```

**Reemplázala por:**
```python
import os
import json

# Detectar si estamos en producción
if os.getenv("GOOGLE_CREDENTIALS"):
    # Estamos en Railway
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    creds_dict = json.loads(creds_json)
    # Guardar temporalmente en archivo
    with open("/tmp/google_credentials.json", "w") as f:
        json.dump(creds_dict, f)
    init_sheets_manager("/tmp/google_credentials.json")
else:
    # Estamos en local
    init_sheets_manager("google_credentials.json")
```

**Sube los cambios a GitHub:**
```bash
git add main.py
git commit -m "Add environment variable support for Google Sheets"
git push
```

Railway redesplegará automáticamente

### PASO 3.7: Verificar el Despliegue

1. En el dashboard de Railway, espera a que terminen los builds
2. Haz clic en **"Deployments"**
3. Deberías ver un ✅ verde
4. Haz clic en **"View Logs"** para ver los detalles

**Deberías ver:**
```
✅ Conectado a Google Sheets: BiomecApp Pro - Análisis
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 4. VERIFICAR QUE FUNCIONA ONLINE

### PASO 4.1: Obtener la URL

1. En Railway, ve a tu proyecto
2. En **"Deployments"**, ve el último
3. Busca la sección **"Domains"**
4. Ahí verás algo como: `biomecapp-pro-production.up.railway.app`
5. **Copia esa URL**

### PASO 4.2: Probar Online

1. Abre en el navegador: `https://tu-dominio.railway.app`
2. Deberías ver la interfaz de BiomecApp
3. **Prueba un análisis**:
   - Sube una foto
   - Haz clic en "Analizar"
   - Deberías ver los resultados

### PASO 4.3: Verificar Google Sheets

1. Ve a **https://docs.google.com/spreadsheets/**
2. Busca: **"BiomecApp Pro - Análisis"**
3. Deberías ver tus datos guardados ✅

---

## 5. CONFIGURACIÓN FINAL

### PASO 5.1: Dominio Personalizado (Opcional)

Si quieres un dominio personalizado (`miapp.com` en lugar de `railway.app`):

1. En Railway, ve a **Settings**
2. Busca **"Domains"**
3. Haz clic en **"Add Custom Domain"**
4. Ingresa tu dominio
5. Railway te dará instrucciones para configurar DNS

### PASO 5.2: Monitoreo

Railway tiene un panel de control donde puedes ver:
- **Logs**: Todo lo que imprime tu app
- **Metrics**: CPU, RAM, bandwidth
- **Deployments**: Historial de versiones

---

## ✅ CHECKLIST FINAL

- [ ] Configuré Google Cloud Console
- [ ] Habilité Google Sheets API y Google Drive API
- [ ] Creé cuenta de servicio
- [ ] Descargué `google_credentials.json`
- [ ] Guardé el JSON en `MediaPipe_Pro/`
- [ ] Probé localmente (`python main.py`)
- [ ] Probé el análisis localmente
- [ ] Verifiqué Google Sheets localmente
- [ ] Creé repositorio en GitHub
- [ ] Subí código a GitHub
- [ ] Creé proyecto en Railway
- [ ] Conecté GitHub a Railway
- [ ] Agregué variable de entorno `GOOGLE_CREDENTIALS`
- [ ] Modifiqué main.py para variables de entorno
- [ ] Verifiqué el despliegue en Railway
- [ ] Probé online
- [ ] Verifiqué Google Sheets online
- [ ] ✅ ¡LISTO!

---

## 🆘 SOLUCIONAR PROBLEMAS

### Error: "No se puede conectar a Google Sheets"
**Solución**: Verifica que `google_credentials.json` esté en la carpeta correcta

### Error: "ModuleNotFoundError: No module named 'gspread'"
**Solución**: Ejecuta: `pip install -r requirements.txt`

### Railway muestra error 404
**Solución**: 
1. Verifica que el `Procfile` existe y dice: `web: python main.py`
2. Verifica los logs en Railway
3. Reinicia el deployment

### Google Sheets no se crea automáticamente
**Solución**: 
1. Crea manualmente un Google Sheet llamado "BiomecApp Pro - Análisis"
2. Abre `google_credentials.json`
3. Busca el campo `"client_email"`
4. Comparte el Google Sheet con ese email y dale permisos de Editor

### La app se cae después de un tiempo
**Solución**: Railway tiene un plan gratuito limitado. Puedes:
- Actualizar a plan de pago
- O desplegar en otra plataforma (Heroku, Render, etc.)

---

## 📞 RESUMEN FINAL

**Tu app está online en:**
```
https://biomecapp-pro-production.up.railway.app
```

**Los datos se guardan en:**
```
Google Sheets: BiomecApp Pro - Análisis
```

**¡Felicidades! 🎉 BiomecApp Pro está ONLINE y FUNCIONAL**

Ahora puedes:
- ✅ Compartir el link con tus clientes
- ✅ Ellos suben fotos/videos
- ✅ Recibes análisis automáticamente en Google Sheets
- ✅ Haces seguimiento y reportes

---

## 🚀 BONUS: Cómo Actualizar Online

Si necesitas hacer cambios en el futuro:

```bash
# 1. Haz cambios locales
# 2. Prueba localmente: python main.py
# 3. Sube a GitHub
git add .
git commit -m "Descripción del cambio"
git push

# 4. Railway redesplegará automáticamente
# 5. ¡Listo!
```

---

¿Necesitas ayuda en algún paso? 🤔
