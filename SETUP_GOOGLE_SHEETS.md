# 📊 BiomecApp Pro - Configuración Google Sheets

## ¿Qué es la Versión Pro?

La **Versión Pro** de BiomecApp es idéntica a la versión original, pero con una **nueva característica poderosa**: 

✅ **Cada análisis se guarda automáticamente en Google Sheets**

Esto te permite:
- 📈 Crear un historial de todos los análisis
- 🔄 Comparar resultados en el tiempo
- 👥 Organizar datos por atleta
- 📊 Crear gráficos y reportes

---

## Pasos para Configurar Google Sheets

### 1️⃣ Crear un Proyecto en Google Cloud

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un **nuevo proyecto** (dale un nombre como "BiomecApp")
3. Espera a que se cree

### 2️⃣ Habilitar APIs

1. En Google Cloud Console, busca **"Google Sheets API"**
2. Haz clic en "Habilitar"
3. Busca **"Google Drive API"**
4. Haz clic en "Habilitar"

### 3️⃣ Crear Credenciales de Servicio

1. Ve a **"Credenciales"** (en el menú lateral izquierdo)
2. Haz clic en **"Crear credenciales"** → **"Cuenta de servicio"**
3. Completa el formulario:
   - **Nombre de cuenta de servicio**: `biomecapp-service`
   - Haz clic en "Crear y continuar"
4. En **"Otorgar acceso al proyecto"**, selecciona el rol **"Editor"**
5. Haz clic en "Continuar"
6. Haz clic en "Crear clave":
   - Selecciona **JSON**
   - Descargará automáticamente un archivo `[ID].json`

### 4️⃣ Guardar las Credenciales

1. Renombra el archivo descargado a **`google_credentials.json`**
2. **Colócalo en la misma carpeta que `main.py`** (en MediaPipe_Pro)

Estructura:
```
MediaPipe_Pro/
├── main.py
├── google_sheets_integration.py
├── google_credentials.json  ← AQUÍ
├── requirements.txt
└── ...
```

### 5️⃣ ¡Listo!

Cuando inicies la app:
```bash
python main.py
```

Deberías ver en la terminal:
```
✅ Conectado a Google Sheets: BiomecApp Pro - Análisis
```

---

## ¿Qué Pasa Cuando Alguien se Testea?

Cada vez que alguien haga un análisis:

1. BiomecApp calcula los ángulos y genera el feedback (como siempre)
2. **Automáticamente**, los datos se guardan en Google Sheets
3. Se crea/actualiza un Google Sheet llamado **"BiomecApp Pro - Análisis"**

### Datos que se guardan:

| Campo | Ejemplo |
|-------|---------|
| **Fecha y Hora** | 2026-05-08 14:30:45 |
| **Nombre del Atleta** | Juan García |
| **Ejercicio** | sentadilla |
| **Rodilla Izq** | 85° |
| **Rodilla Der** | 83° |
| **Simetría Rodillas** | 2° |
| **Cadera Izq** | 72° |
| **Cadera Der** | 73° |
| **Tobillo Izq** | 15° |
| **Tobillo Der** | 14° |
| **Inclinación Tronco** | (si es peso muerto) |
| **Estado Rodilla Izq** | ✅ Ideal |
| **Estado Rodilla Der** | ✅ Ideal |
| **Riesgo Detectado** | ✅ No |
| **Feedback Principal** | Análisis de Juan García: |
| **URL Imagen** | (campo para URL si la agregas después) |

---

## Acceder a los Datos en Google Sheets

1. Ve a [Google Sheets](https://docs.google.com/spreadsheets/)
2. Busca el documento **"BiomecApp Pro - Análisis"**
3. ¡Verás todos los análisis organizados en filas!

Puedes:
- 📊 Crear gráficos con Chart Editor
- 🔍 Filtrar por atleta o ejercicio
- 📈 Crear dashboards
- 📥 Exportar a CSV/Excel

---

## Solucionar Problemas

### ❌ "Error conectando a Google Sheets"

**Causa**: El archivo `google_credentials.json` no está en la carpeta correcta.

**Solución**:
1. Verifica que `google_credentials.json` esté en la misma carpeta que `main.py`
2. Verifica que el nombre del archivo sea exactamente `google_credentials.json` (sin espacios)

### ❌ "SpreadsheetNotFound"

**Causa**: La cuenta de servicio no tiene permisos.

**Solución**:
1. Crea manualmente un Google Sheet llamado **"BiomecApp Pro - Análisis"**
2. Abre el archivo `google_credentials.json` con un editor de texto
3. Busca el campo `"client_email"` (algo como `biomecapp-service@....iam.gserviceaccount.com`)
4. Comparte el Google Sheet con ese email y dale permisos de **Editor**

### ✅ Los datos se guardan pero el enlace no funciona

Esto es normal si usas credenciales de servicio. El Google Sheet se crea pero no se abre automáticamente. Accede a él desde tu cuenta de Google normalmente.

---

## Diferencia entre MediaPipe (original) y MediaPipe_Pro

| Característica | Original | Pro |
|---|---|---|
| Análisis de pose | ✅ | ✅ |
| Feedback detallado | ✅ | ✅ |
| Interfaz web | ✅ | ✅ |
| **Guardado en Google Sheets** | ❌ | ✅ |
| **Historial de análisis** | ❌ | ✅ |
| **Reportes y comparativas** | ❌ | ✅ |

---

## Preguntas Frecuentes

**¿La versión original sigue funcionando igual?**  
Sí, está intacta en la carpeta `MediaPipe`. No hay cambios.

**¿Puedo ver los datos en tiempo real?**  
Sí, abre el Google Sheet y actualiza la página (F5).

**¿Qué pasa si no tengo credenciales configuradas?**  
Funciona igual, pero sin guardar en Google Sheets. Verás un mensaje de advertencia.

**¿Puedo cambiar el nombre del Google Sheet?**  
Sí, edita el parámetro `spreadsheet_name` en `main.py` línea 27.

---

## Contacto / Soporte

Si tienes problemas, revisa los logs en la terminal cuando inicies la app. El programa es muy verbal y te dirá exactamente qué está pasando.

¡Disfruta BiomecApp Pro! 🚀
