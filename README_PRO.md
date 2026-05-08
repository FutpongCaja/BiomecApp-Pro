# 🚀 BiomecApp Pro - Versión con Google Sheets

**BiomecApp Pro** es la versión empresarial de BiomecApp. Todo funciona igual que el original, pero **con registro automático en Google Sheets**.

---

## 📁 Estructura

```
MediaPipe_Pro/
├── main.py                           ← Aplicación principal (MODIFICADA para Pro)
├── google_sheets_integration.py      ← Módulo de Google Sheets (NUEVO)
├── google_credentials.json           ← Credenciales Google (DEBES AGREGAR)
├── requirements.txt                  ← Dependencias (ACTUALIZADO)
├── SETUP_GOOGLE_SHEETS.md            ← Guía de configuración
├── README_PRO.md                     ← Este archivo
├── Dockerfile
├── railway.toml
└── ... otros archivos
```

---

## ⚡ Quick Start

### 1. Configura Google Sheets
Lee **SETUP_GOOGLE_SHEETS.md** (paso a paso, muy simple)

### 2. Instala dependencias
```bash
pip install -r requirements.txt
```

### 3. Inicia la app
```bash
python main.py
```

### 4. Abre en el navegador
```
http://localhost:8000
```

¡Usa la app normalmente! Los análisis se guardarán automáticamente en Google Sheets.

---

## ✨ Características Pro

### Original ✓
- Análisis de pose con MediaPipe
- Cálculo de ángulos de articulaciones
- Feedback detallado en tiempo real
- Interfaz web moderna

### Pro (NUEVO) ✨
- **Guardado automático en Google Sheets** 📊
- **Historial completo de análisis** 📈
- **Datos organizados por fecha, atleta y ejercicio** 🗂️
- **Datos listos para análisis y reportes** 📉

---

## 🔧 Cambios vs. Original

### ¿Qué cambió en main.py?
1. **Imports nuevos** (líneas 13-14): Google Sheets integration
2. **Inicialización** (línea 27): Conecta con Google Sheets al inicio
3. **En /analyze-video** (línea 843): Guarda resultado en Sheets
4. **En /analyze-frame** (línea 878): Guarda resultado en Sheets

### Código clave:
```python
# Guardar automáticamente en Google Sheets
save_to_sheets(full_name, exercise_type, angles, feedback)
```

Simple, ¿verdad?

---

## 📊 ¿Qué se guarda en Google Sheets?

Para **cada análisis**:

```
Juan García | sentadilla | 85° | 83° | 2° | 72° | 73° | ... | 2026-05-08 14:30:45 | ✅ Ideal | ✅ No
```

**16 columnas** con toda la información:
- Datos personales (nombre, email)
- Ejercicio
- Todos los ángulos (rodillas, caderas, tobillos, tronco)
- Estados y riesgos
- Feedback
- Timestamp

---

## 🛡️ ¿La versión original sigue funcionando?

**SÍ, 100%.**

Ambas versiones están separadas:
- `MediaPipe/` → Original (sin cambios)
- `MediaPipe_Pro/` → Con Google Sheets

Puedes usar ambas simultáneamente.

---

## 🔐 Privacidad y Seguridad

### Google Credentials
- El archivo `google_credentials.json` es **privado** (no lo compartas)
- Las credenciales usan **Service Account** (no acceso a tu cuenta personal)
- Solo tiene acceso a Google Sheets, nada más

### Datos
- Se guardan en **tu Google Sheets** (bajo tu control)
- Puedes hacer privado, compartir o eliminar cuando quieras

---

## 📈 Casos de Uso

### 1. **Entrenador Personal**
Analiza múltiples atletas y mantén un registro histórico. Visualiza mejoras en el tiempo.

### 2. **Clínica de Rehabilitación**
Monitorea el progreso de pacientes. Descarga datos para reportes médicos.

### 3. **Gimnasio / Academia**
Ofrece análisis técnico a miembros. Crea reportes de mejora.

### 4. **Investigación**
Recopila datos biomecánicos de múltiples sujetos en un solo lugar.

---

## 🚨 Troubleshooting

| Problema | Solución |
|----------|----------|
| "Cannot import google_sheets_integration" | Verifica que `google_sheets_integration.py` esté en la carpeta |
| "Error conectando a Google Sheets" | Lee SETUP_GOOGLE_SHEETS.md, paso 3-4 |
| No aparece en logs "Conectado a Google Sheets" | `google_credentials.json` no está configurado (pero funciona offline) |
| Los datos no se guardan | Revisa que el archivo `google_credentials.json` sea válido |

---

## 💡 Tips

1. **Crea varias hojas**: Puedes tener múltiples Google Sheets para diferentes grupos
2. **Usa filtros**: En Google Sheets, filtra por "Riesgo Detectado" = "🔴 SÍ" para ver casos críticos
3. **Crea dashboards**: Usa Google Sheets para graficar tendencias de ángulos
4. **Exporta datos**: Descarga a CSV/Excel para análisis en Python, R, etc.

---

## 📚 Más Información

- **Configuración detallada**: Ver `SETUP_GOOGLE_SHEETS.md`
- **Código de integración**: Ver `google_sheets_integration.py`
- **Cambios en la API**: Ver comentarios en `main.py` (busca "📊")

---

## 🎯 Resumen

| Aspecto | Detalles |
|--------|----------|
| **Compatibilidad** | 100% con original |
| **Nuevas dependencias** | gspread, google-auth |
| **Archivos nuevos** | google_sheets_integration.py, SETUP_GOOGLE_SHEETS.md |
| **Configuración** | ~5 minutos (Google Cloud) |
| **Tiempo de desarrollo** | Sin cambios en la experiencia del usuario |

---

## 🚀 ¡Listo para comenzar?

1. Lee **SETUP_GOOGLE_SHEETS.md**
2. Configura Google Sheets
3. ¡Inicia y comienza a recolectar datos! 📊

¡Que disfrutes BiomecApp Pro! 💪
