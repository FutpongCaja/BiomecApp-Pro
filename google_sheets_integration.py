"""
🔗 Google Sheets Integration para BiomecApp Pro
Guarda automáticamente los resultados de cada análisis en Google Sheets
"""

import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime
from typing import Dict, Optional
import os


class GoogleSheetsManager:
    """Gestor para guardar análisis en Google Sheets"""

    def __init__(self, credentials_source: str = "google_credentials.json",
                 spreadsheet_name: str = "BiomecApp Pro - Análisis"):
        """
        Inicializa la conexión con Google Sheets

        Args:
            credentials_source: Ruta al archivo JSON O nombre de variable de entorno
            spreadsheet_name: Nombre del Google Sheet donde guardar datos
        """
        self.spreadsheet_name = spreadsheet_name
        self.credentials_source = credentials_source
        self.credentials_dict = None
        self.client = None
        self.sheet = None
        self.worksheet = None

        # Intentar conectar
        print(f"🔌 Iniciando conexión a Google Sheets...")
        print(f"📋 Buscando sheet: '{spreadsheet_name}'")
        try:
            self._connect()
        except Exception as e:
            import traceback
            print(f"⚠️ No se pudo conectar a Google Sheets: {e}")
            print(traceback.format_exc())
            print("📌 Los análisis se guardarán localmente pero no en Google Sheets")

    def _connect(self):
        """Establece la conexión con Google Sheets"""
        try:
            # Obtener credenciales (desde variable de entorno o archivo)
            print("📦 Cargando credenciales...")
            creds_dict = self._load_credentials()
            if not creds_dict:
                print("❌ No se encontraron credenciales de Google")
                return

            # Autenticar con las credenciales de servicio
            print("🔐 Autenticando con Google...")
            scopes = ['https://www.googleapis.com/auth/spreadsheets',
                     'https://www.googleapis.com/auth/drive']
            creds = Credentials.from_service_account_info(
                creds_dict,
                scopes=scopes
            )
            print("✅ Credenciales autenticadas")

            # Crear cliente gspread
            print("🌐 Creando cliente gspread...")
            self.client = gspread.authorize(creds)
            print("✅ Cliente gspread listo")

            # Abrir o crear el spreadsheet
            print(f"📂 Buscando spreadsheet: '{self.spreadsheet_name}'...")
            try:
                self.sheet = self.client.open(self.spreadsheet_name)
                print(f"✅ Encontrado spreadsheet: {self.spreadsheet_name}")
            except gspread.exceptions.SpreadsheetNotFound:
                print(f"📝 Creando nuevo Google Sheet: {self.spreadsheet_name}")
                self.sheet = self.client.create(self.spreadsheet_name)
                self.sheet.share('', perm_type='anyone', role='writer')
                print(f"✅ Google Sheet creado")

            # Seleccionar o crear worksheet "Análisis"
            print("📄 Buscando worksheet 'Análisis'...")
            try:
                self.worksheet = self.sheet.worksheet("Análisis")
                print("✅ Worksheet 'Análisis' encontrado")
            except gspread.exceptions.WorksheetNotFound:
                print("📝 Creando worksheet 'Análisis'...")
                self.worksheet = self.sheet.add_worksheet(title="Análisis", rows=1000, cols=20)
                self._setup_headers()
                print("✅ Worksheet 'Análisis' creado")

            print(f"✅ Conectado a Google Sheets: {self.spreadsheet_name}")

        except Exception as e:
            import traceback
            print(f"❌ Error conectando a Google Sheets: {e}")
            print(traceback.format_exc())
            self.client = None
            self.sheet = None
            self.worksheet = None

    def _load_credentials(self) -> Optional[dict]:
        """
        Carga las credenciales desde:
        1. Variable de entorno GOOGLE_CREDENTIALS (Render)
        2. Archivo local google_credentials.json (desarrollo)
        """
        # Intentar desde variable de entorno (Render)
        env_creds = os.environ.get('GOOGLE_CREDENTIALS')
        if env_creds:
            try:
                creds_dict = json.loads(env_creds)
                print("✅ Credenciales cargadas desde variable de entorno")
                return creds_dict
            except json.JSONDecodeError as e:
                print(f"❌ Error parsing GOOGLE_CREDENTIALS: {e}")
                return None

        # Intentar desde archivo local
        if os.path.exists(self.credentials_source):
            try:
                with open(self.credentials_source, 'r') as f:
                    creds_dict = json.load(f)
                    print("✅ Credenciales cargadas desde archivo local")
                    return creds_dict
            except Exception as e:
                print(f"❌ Error leyendo archivo {self.credentials_source}: {e}")
                return None

        print("⚠️ No se encontró GOOGLE_CREDENTIALS en variable de entorno ni archivo local")
        return None

    def _setup_headers(self):
        """Configura los headers del worksheet si está vacío"""
        headers = [
            "Fecha y Hora",
            "Nombre del Atleta",
            "Ejercicio",
            "Rodilla Izq (°)",
            "Rodilla Der (°)",
            "Simetría Rodillas (°)",
            "Cadera Izq (°)",
            "Cadera Der (°)",
            "Tobillo Izq (°)",
            "Tobillo Der (°)",
            "Inclinación Tronco (°)",
            "Estado Rodilla Izq",
            "Estado Rodilla Der",
            "Riesgo Detectado",
            "Feedback Principal",
            "URL Imagen Análisis"
        ]
        self.worksheet.append_row(headers)

    def save_analysis(self, athlete_name: str, exercise_type: str,
                     angles: Dict, feedback: str, image_url: Optional[str] = None) -> bool:
        """
        Guarda un análisis en Google Sheets

        Args:
            athlete_name: Nombre del atleta
            exercise_type: Tipo de ejercicio (sentadilla/peso_muerto)
            angles: Diccionario con los ángulos calculados
            feedback: Texto del feedback generado
            image_url: URL de la imagen analizada (opcional)

        Returns:
            True si se guardó exitosamente, False si no
        """
        if not self.worksheet:
            print("⚠️ Google Sheets no está conectado. Los datos no se guardarán en la nube.")
            return False

        try:
            # Preparar datos
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Extraer ángulos
            rodilla_izq = angles.get("rodilla_izq", "")
            rodilla_der = angles.get("rodilla_der", "")
            simetria = angles.get("simetria_rodillas", "")
            cadera_izq = angles.get("cadera_izq", "")
            cadera_der = angles.get("cadera_der", "")
            tobillo_izq = angles.get("tobillo_izq", "")
            tobillo_der = angles.get("tobillo_der", "")
            inclinacion_tronco = angles.get("inclinacion_tronco", "")

            # Determinar estados
            estado_izq = self._get_status(rodilla_izq, exercise_type, "izq")
            estado_der = self._get_status(rodilla_der, exercise_type, "der")

            # Detectar riesgos
            hay_riesgo = "🔴 SÍ" if any(x in feedback for x in ["riesgo", "Riesgo"]) else "✅ No"

            # Primer línea del feedback
            feedback_principal = feedback.split("\n")[0] if feedback else ""

            # Construir fila
            row = [
                timestamp,
                athlete_name,
                exercise_type,
                str(rodilla_izq),
                str(rodilla_der),
                str(simetria),
                str(cadera_izq),
                str(cadera_der),
                str(tobillo_izq) if tobillo_izq else "",
                str(tobillo_der) if tobillo_der else "",
                str(inclinacion_tronco) if inclinacion_tronco else "",
                estado_izq,
                estado_der,
                hay_riesgo,
                feedback_principal,
                image_url or ""
            ]

            # Agregar a Google Sheets
            self.worksheet.append_row(row)
            print(f"✅ Análisis de {athlete_name} guardado en Google Sheets")
            return True

        except Exception as e:
            print(f"❌ Error guardando en Google Sheets: {e}")
            return False

    def _get_status(self, angle_value, exercise_type: str, side: str) -> str:
        """Determina el estado basado en el ángulo"""
        if not angle_value:
            return "N/A"

        angle = float(angle_value)

        if exercise_type == "sentadilla":
            if angle < 70:
                return "⚠️ Corrección"
            elif 70 <= angle <= 100:
                return "✅ Ideal"
            else:
                return "⚠️ Profundidad baja"
        else:  # peso_muerto
            if angle < 45:
                return "🔴 Riesgo"
            elif 45 <= angle <= 70:
                return "✅ Correcto"
            else:
                return "⚠️ Revisar"

    def get_spreadsheet_url(self) -> str:
        """Retorna la URL del spreadsheet"""
        if self.sheet:
            return f"https://docs.google.com/spreadsheets/d/{self.sheet.id}"
        return ""


# Instancia global del manager
sheets_manager: Optional[GoogleSheetsManager] = None

def init_sheets_manager(credentials_source: str = "google_credentials.json"):
    """
    Inicializa el manager de Google Sheets

    Intenta leer credenciales desde:
    - Variable de entorno GOOGLE_CREDENTIALS (Render)
    - Archivo credentials_source (desarrollo local)
    """
    global sheets_manager
    sheets_manager = GoogleSheetsManager(credentials_source)
    return sheets_manager

def save_to_sheets(athlete_name: str, exercise_type: str, angles: Dict,
                  feedback: str, image_url: Optional[str] = None) -> bool:
    """Función simplificada para guardar datos"""
    if sheets_manager:
        return sheets_manager.save_analysis(athlete_name, exercise_type, angles, feedback, image_url)
    return False
