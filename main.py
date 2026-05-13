import os
import cv2
import numpy as np
import mediapipe as mp
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import base64
import tempfile
import math
import json

# 🔗 Google Sheets Integration (BiomecApp Pro)
from google_sheets_integration import init_sheets_manager, save_to_sheets

app = FastAPI(title="BiomecApp Pro")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📊 Inicializar Google Sheets Manager
# Esto va a leer de GOOGLE_CREDENTIALS (variable de entorno en Render)
# o de google_credentials.json (archivo local)
init_sheets_manager()

mp_pose    = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils


# ─── HELPERS ────────────────────────────────────────────────────────────────

def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(np.degrees(radians))
    return 360 - angle if angle > 180 else angle


def get_pt(landmarks, landmark_id, w, h):
    lm = landmarks[landmark_id]
    return [lm.x * w, lm.y * h]


# ─── JUMP ANALYSIS (Phase 2) ───────────────────────────────────────────────

def analyze_jump_video(video_path, jump_type):
    """
    Analiza TODO el video frame a frame para detectar salto
    Calcula: altura, tiempo de vuelo, simetría, potencia
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30

    hip_positions_l = []
    hip_positions_r = []
    ankle_positions_l = []
    ankle_positions_r = []
    frame_count = 0
    best_frame = None
    best_frame_idx = 0

    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            h, w = frame.shape[:2]
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(image_rgb)

            if results.pose_landmarks:
                lm = results.pose_landmarks.landmark
                L = mp_pose.PoseLandmark

                # Obtener posiciones Y de caderas y tobillos (eje vertical)
                l_hip_y = lm[L.LEFT_HIP.value].y * h
                r_hip_y = lm[L.RIGHT_HIP.value].y * h
                l_ankle_y = lm[L.LEFT_ANKLE.value].y * h
                r_ankle_y = lm[L.RIGHT_ANKLE.value].y * h

                hip_positions_l.append(l_hip_y)
                hip_positions_r.append(r_hip_y)
                ankle_positions_l.append(l_ankle_y)
                ankle_positions_r.append(r_ankle_y)

                # Guardar frame en pico máximo (máxima altura de cadera)
                avg_hip = (l_hip_y + r_hip_y) / 2
                if frame_count == 0 or avg_hip < hip_positions_l[best_frame_idx]:
                    best_frame = frame.copy()
                    best_frame_idx = len(hip_positions_l) - 1

            frame_count += 1

    cap.release()

    if not hip_positions_l:
        return None, None, None

    # Detectar fases del salto
    jump_data = detect_jump_phases(hip_positions_l, hip_positions_r, ankle_positions_l, ankle_positions_r, fps)

    # Calcular métricas
    metrics = calculate_jump_metrics(jump_data, jump_type)

    # Dibujar anotaciones en el best frame
    if best_frame is not None:
        annotated = draw_jump_analysis(best_frame, metrics, jump_type)
    else:
        annotated = frame if 'frame' in locals() else None

    return metrics, annotated, jump_data


def detect_jump_phases(hip_l, hip_r, ankle_l, ankle_r, fps):
    """
    Detecta las fases del salto analizando posiciones de caderas y tobillos
    Retorna: despegue_frame, aterrizaje_frame, altura_máxima, etc.
    """
    hip_avg = [(hip_l[i] + hip_r[i]) / 2 for i in range(len(hip_l))]
    ankle_avg = [(ankle_l[i] + ankle_r[i]) / 2 for i in range(len(ankle_l))]

    # Normalizar posiciones (0-1)
    h_min, h_max = min(hip_avg), max(hip_avg)
    hip_norm = [(h - h_min) / (h_max - h_min + 0.001) for h in hip_avg]

    # Detectar cambios en velocidad vertical (derivada)
    velocidades = [0]
    for i in range(1, len(hip_norm)):
        vel = hip_norm[i] - hip_norm[i-1]
        velocidades.append(vel)

    # Encontrar puntos clave
    # Descenso: velocidad positiva (baja)
    # Despegue: cambio de baja a subida (máximo en diferencia negativa)
    # Vuelo: velocidad negativa pero caderas suben
    # Aterrizaje: caderas bajan y se estabilizan

    despegue = None
    aterrizaje = None
    min_hip = min(hip_norm)
    max_hip = max(hip_norm)

    for i in range(1, len(hip_norm) - 1):
        # Despegue: caderas suben rápido (velocidad cambia de positiva a negativa)
        if velocidades[i-1] > 0 and velocidades[i] < -0.01 and despegue is None:
            despegue = i

        # Aterrizaje: después de despegue, caderas bajan y se estabilizan
        if despegue is not None and i > despegue + 5:
            if velocidades[i] > -0.005 and hip_norm[i] < min_hip + 0.1:
                aterrizaje = i
                break

    # Si no detectó bien, estimar
    if despegue is None:
        despegue = len(hip_norm) // 3
    if aterrizaje is None:
        aterrizaje = len(hip_norm) - 5

    tiempo_vuelo = (aterrizaje - despegue) / fps
    altura_max = max(hip_norm[despegue:min(aterrizaje+1, len(hip_norm))])
    altura_inicial = hip_norm[0]
    altura_relativa = (altura_max - altura_inicial) * (h_max - h_min) / 100  # En píxeles relativos

    # Calcular simetría de piernas
    simetria_despegue = abs(hip_l[despegue] - hip_r[despegue]) if despegue < len(hip_l) else 0
    simetria_aterrizaje = abs(hip_l[aterrizaje] - hip_r[aterrizaje]) if aterrizaje < len(hip_l) else 0

    return {
        'despegue': despegue,
        'aterrizaje': aterrizaje,
        'tiempo_vuelo': tiempo_vuelo,
        'altura_relativa': altura_relativa,
        'simetria_despegue': simetria_despegue,
        'simetria_aterrizaje': simetria_aterrizaje,
        'hip_trajectory': hip_avg,
        'velocidades': velocidades
    }


def calculate_jump_metrics(jump_data, jump_type):
    """
    Calcula métricas finales del salto
    altura (cm), tiempo de vuelo (ms), simetría (°), potencia (índice)
    """
    if not jump_data:
        return {}

    # Usar fórmula: h = g * t² / 8  (donde g=9.8 m/s², h en cm, t en segundos)
    tiempo_vuelo = jump_data['tiempo_vuelo']
    altura_cm = max(5, int(9.8 * (tiempo_vuelo ** 2) / 8 * 100))  # Mínimo 5cm

    # Si es muy alto, capear a valores realistas (máx ~1.5m para humanos)
    altura_cm = min(altura_cm, 150)

    tiempo_vuelo_ms = int(tiempo_vuelo * 1000)

    # Simetría promedio
    simetria = (jump_data['simetria_despegue'] + jump_data['simetria_aterrizaje']) / 2

    angles = {
        "altura_salto_cm": altura_cm,
        "tiempo_vuelo_ms": tiempo_vuelo_ms,
        "simetria_piernas": round(simetria, 1)
    }

    return angles


def draw_jump_analysis(frame, metrics, jump_type):
    """
    Dibuja análisis de salto en el frame
    Solo muestra la imagen, sin textos superpuestos
    """
    if frame is None:
        return np.zeros((480, 640, 3), dtype=np.uint8)

    annotated = frame.copy()
    # No dibujar nada, solo retornar la imagen limpia
    return annotated


# ─── POSE ANALYSIS ──────────────────────────────────────────────────────────

def analyze_frame(image_bgr, exercise_type):
    h, w = image_bgr.shape[:2]
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        results = pose.process(image_rgb)

        if not results.pose_landmarks:
            return None, image_bgr

        lm = results.pose_landmarks.landmark
        L  = mp_pose.PoseLandmark

        def pt(lid):
            return get_pt(lm, lid, w, h)

        angles = {}

        # ⚠️ Check if this is a jump analysis (coming soon)
        if exercise_type in ["salto_vertical", "salto_horizontal"]:
            # Fase 2: Implementar análisis de saltos
            # Por ahora, retornamos un análisis placeholder
            angles["postura_inicial"] = 0
            # Dibujar esqueleto igual
            annotated = image_bgr.copy()
            mp_drawing.draw_landmarks(
                annotated,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(50, 255, 120), thickness=2, circle_radius=4),
                mp_drawing.DrawingSpec(color=(0, 180, 255), thickness=2),
            )
            return angles, annotated

        # Rodillas y caderas (los originales que funcionaban)
        l_knee = calculate_angle(pt(L.LEFT_HIP.value),       pt(L.LEFT_KNEE.value),  pt(L.LEFT_ANKLE.value))
        r_knee = calculate_angle(pt(L.RIGHT_HIP.value),      pt(L.RIGHT_KNEE.value), pt(L.RIGHT_ANKLE.value))
        l_hip  = calculate_angle(pt(L.LEFT_SHOULDER.value),  pt(L.LEFT_HIP.value),   pt(L.LEFT_KNEE.value))
        r_hip  = calculate_angle(pt(L.RIGHT_SHOULDER.value), pt(L.RIGHT_HIP.value),  pt(L.RIGHT_KNEE.value))

        angles["rodilla_izq"]      = round(l_knee, 1)
        angles["rodilla_der"]      = round(r_knee, 1)
        angles["cadera_izq"]       = round(l_hip,  1)
        angles["cadera_der"]       = round(r_hip,  1)
        angles["simetria_rodillas"]= round(abs(l_knee - r_knee), 1)

        # Inclinación de tibia respecto a vertical — dato clínico real de dorsiflexión
        # 0° = tibia vertical, 20-30° = normal en sentadilla, >35° = restricción de tobillo
        try:
            lk = lm[L.LEFT_KNEE.value]
            la = lm[L.LEFT_ANKLE.value]
            rk = lm[L.RIGHT_KNEE.value]
            ra = lm[L.RIGHT_ANKLE.value]
            l_ank = round(math.degrees(math.atan2(abs(lk.x - la.x), abs(la.y - lk.y))), 1)
            r_ank = round(math.degrees(math.atan2(abs(rk.x - ra.x), abs(ra.y - rk.y))), 1)
            angles["tobillo_izq"] = l_ank
            angles["tobillo_der"] = r_ank
        except Exception:
            l_ank = None
            r_ank = None

        if exercise_type == "peso_muerto":
            l_sh    = pt(L.LEFT_SHOULDER.value)
            r_sh    = pt(L.RIGHT_SHOULDER.value)
            l_hp    = pt(L.LEFT_HIP.value)
            r_hp    = pt(L.RIGHT_HIP.value)
            mid_sh  = [(l_sh[0]+r_sh[0])/2, (l_sh[1]+r_sh[1])/2]
            mid_hip = [(l_hp[0]+r_hp[0])/2, (l_hp[1]+r_hp[1])/2]
            dx = mid_sh[0] - mid_hip[0]
            dy = -(mid_sh[1] - mid_hip[1])
            angles["inclinacion_tronco"] = round(abs(math.degrees(math.atan2(dx, dy))), 1)

        # Dibujar esqueleto
        annotated = image_bgr.copy()
        mp_drawing.draw_landmarks(
            annotated,
            results.pose_landmarks,
            mp_pose.POSE_CONNECTIONS,
            mp_drawing.DrawingSpec(color=(50, 255, 120), thickness=2, circle_radius=4),
            mp_drawing.DrawingSpec(color=(0, 180, 255), thickness=2),
        )

        font  = cv2.FONT_HERSHEY_SIMPLEX
        scale = max(0.5, min(1.0, w / 800))

        def draw_angle(pos, angle, color=(255, 255, 0)):
            x, y = int(pos[0]), int(pos[1])
            cv2.putText(annotated, f"{int(angle)}\xb0", (x-30, y-12), font, scale, (0, 0, 0), 3)
            cv2.putText(annotated, f"{int(angle)}\xb0", (x-30, y-12), font, scale, color, 2)

        draw_angle(pt(L.LEFT_KNEE.value),  l_knee)
        draw_angle(pt(L.RIGHT_KNEE.value), r_knee)
        draw_angle(pt(L.LEFT_HIP.value),   l_hip,  (0, 255, 200))
        draw_angle(pt(L.RIGHT_HIP.value),  r_hip,  (0, 255, 200))
        if l_ank is not None:
            draw_angle(pt(L.LEFT_ANKLE.value),  l_ank, (255, 140, 0))
            draw_angle(pt(L.RIGHT_ANKLE.value), r_ank, (255, 140, 0))

        return angles, annotated


# ─── KEY FRAME EXTRACTION ───────────────────────────────────────────────────

def extract_key_frame(video_path, exercise_type):
    cap        = cv2.VideoCapture(video_path)
    best_frame = None
    best_score = float('inf')
    frame_idx  = 0
    total      = 0

    with mp_pose.Pose(min_detection_confidence=0.5) as pose:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            total     += 1
            frame_idx += 1
            if frame_idx % 3 != 0:
                continue

            rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb)
            if not results.pose_landmarks:
                continue

            lm   = results.pose_landmarks.landmark
            h, w = frame.shape[:2]
            L    = mp_pose.PoseLandmark

            def pt(lid):
                return get_pt(lm, lid, w, h)

            if exercise_type == "sentadilla":
                score = calculate_angle(pt(L.LEFT_HIP.value), pt(L.LEFT_KNEE.value), pt(L.LEFT_ANKLE.value))
            elif exercise_type in ["salto_vertical", "salto_horizontal"]:
                # Para saltos, buscar el frame donde está más erguido (cadera arriba)
                score = calculate_angle(pt(L.LEFT_SHOULDER.value), pt(L.LEFT_HIP.value), pt(L.LEFT_KNEE.value))
            else:
                # peso_muerto
                score = calculate_angle(pt(L.LEFT_SHOULDER.value), pt(L.LEFT_HIP.value), pt(L.LEFT_KNEE.value))

            if score < best_score:
                best_score = score
                best_frame = frame.copy()

    cap.release()

    if best_frame is None and total > 0:
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, total // 2)
        ret, best_frame = cap.read()
        cap.release()

    return best_frame


# ─── FEEDBACK POR REGLAS ─────────────────────────────────────────────────────

def generate_feedback(angles, exercise_type, athlete_name=""):
    bien  = []
    corr  = []
    riesg = []
    ejer  = []
    name_str = f"{athlete_name}, " if athlete_name else ""

    # 🚀 ANÁLISIS DE SALTOS (Phase 2 - IMPLEMENTADO)
    if exercise_type in ["salto_vertical", "salto_horizontal"]:
        altura = angles.get("altura_salto_cm", 0)
        tiempo_vuelo = angles.get("tiempo_vuelo_ms", 0)
        simetria = angles.get("simetria_piernas", 0)

        title = "Salto Vertical" if exercise_type == "salto_vertical" else "Salto Horizontal"

        # Evaluación de altura
        if altura < 20:
            riesg.append(f"Altura del salto muy baja ({altura} cm) — falta potencia en las piernas.")
            ejer.append("Sentadillas profundas con pausa en cajón para desarrollar fuerza explosiva.")
        elif altura < 40:
            corr.append(f"Altura del salto de {altura} cm — hay margen para mejorar.")
            ejer.append("Ejercicios pliométricos: saltos en caja, saltos con sentadilla.")
        elif altura < 60:
            bien.append(f"Altura del salto buena ({altura} cm) — excelente explosividad.")
            ejer.append("Mantén el entrenamiento de potencia con sentadillas y peso muerto.")
        else:
            bien.append(f"¡ALTURA EXCEPCIONAL! {altura} cm — eres un saltador de élite.")
            ejer.append("Continúa con entrenamiento avanzado de potencia y velocidad.")

        # Evaluación de simetría
        if simetria < 5:
            bien.append(f"Perfecta simetría bilateral ({simetria}°) — ambas piernas trabajan igual.")
        elif simetria < 15:
            corr.append(f"Leve asimetría ({simetria}°) — el lado {('izquierdo' if simetria > 7 else 'derecho')} es más fuerte.")
            ejer.append("Ejercicios unilaterales: sentadilla búlgara, peso muerto con una pierna.")
        else:
            riesg.append(f"Asimetría significativa ({simetria}°) — riesgo de lesión.")
            ejer.append("Prensa unilateral y sentadilla búlgara para equilibrar la fuerza.")

        # Tiempo de vuelo
        tiempo_vuelo_sec = tiempo_vuelo / 1000
        bien.append(f"Tiempo de vuelo: {tiempo_vuelo} ms ({tiempo_vuelo_sec:.2f}s)")

        # Recomendaciones generales
        if not ejer or len(ejer) == 1:
            if exercise_type == "salto_vertical":
                ejer.append("Entrena 2-3 veces por semana saltos con progresión: sentadilla, sentadilla con salto, saltos múltiples.")
            else:
                ejer.append("Mejora flexibilidad de tobillos y trabaja potencia lateral con saltos laterales y sentadillas laterales.")

        lines = []
        if bien:
            lines.append("✅ Lo que está bien:")
            lines += [f"  • {x}" for x in bien]
        if corr:
            lines.append("\n⚠️ Qué mejorar:")
            lines += [f"  • {x}" for x in corr]
        if riesg:
            lines.append("\n🔴 Riesgo de lesión:")
            lines += [f"  • {x}" for x in riesg]
        if ejer:
            lines.append("\n💪 Plan de entrenamiento:")
            lines += [f"  • {x}" for x in ejer]

        prefix = f"Análisis de {title} - {name_str}:\n\n" if name_str else f"Análisis de {title}:\n\n"
        return prefix + "\n".join(lines)

    if exercise_type == "sentadilla":
        rod_izq = angles.get("rodilla_izq", 0)
        rod_der = angles.get("rodilla_der", 0)
        cad_izq = angles.get("cadera_izq",  0)
        cad_der = angles.get("cadera_der",  0)
        sim_rod = angles.get("simetria_rodillas", 0)
        tob_izq = angles.get("tobillo_izq")
        tob_der = angles.get("tobillo_der")

        for lado, val in [("izquierda", rod_izq), ("derecha", rod_der)]:
            if val < 60:
                riesg.append(f"Rodilla {lado} muy cerrada ({val}°) — riesgo de sobrecarga patelar. No forzar más profundidad hasta corregir técnica.")
            elif val < 70:
                corr.append(f"Rodilla {lado} en {val}° — levemente por debajo del ideal (70-100°). No inclines tanto el tronco al bajar.")
            elif val <= 100:
                bien.append(f"Rodilla {lado} en {val}° — rango ideal.")
            elif val <= 120:
                corr.append(f"Rodilla {lado} en {val}° — poca profundidad. Bajá más para activar glúteos e isquiotibiales.")
            else:
                corr.append(f"Rodilla {lado} en {val}° — profundidad muy escasa. Trabajá movilidad de cadera y tobillo.")

        for lado, val in [("izquierda", cad_izq), ("derecha", cad_der)]:
            if val < 45:
                riesg.append(f"Cadera {lado} muy cerrada ({val}°) — posible compensación lumbar.")
            elif val < 60:
                corr.append(f"Cadera {lado} en {val}° — algo restringida. Trabajá apertura de cadera.")
            elif val <= 100:
                bien.append(f"Cadera {lado} en {val}° — posición correcta.")
            else:
                corr.append(f"Cadera {lado} en {val}° — revisá la postura general del tronco.")

        if sim_rod <= 5:
            bien.append(f"Simetría de rodillas excelente ({sim_rod}°).")
        elif sim_rod <= 10:
            corr.append(f"Asimetría de rodillas de {sim_rod}° — atención al lado más débil.")
            ejer.append("Sentadilla búlgara para equilibrar la fuerza de ambas piernas.")
        else:
            riesg.append(f"Asimetría importante de rodillas: {sim_rod}° — riesgo de lesión. Trabajar unilateral.")
            ejer.append("Prensa unilateral y sentadilla búlgara antes de cargar más peso.")

        if tob_izq is not None and tob_der is not None:
            tob_max = max(tob_izq, tob_der)
            if tob_max > 40:
                riesg.append(f"Inclinación de tibia excesiva ({tob_max}°) — restricción severa de tobillo. Riesgo de elevación de talones y compensación lumbar.")
                ejer.append("Movilidad de tobillo: estiramiento de pantorrilla en pared 3×30 seg y movilizaciones con banda antes de entrenar.")
            elif tob_max > 32:
                corr.append(f"Inclinación de tibia elevada ({tob_max}°) — posible restricción de dorsiflexión. Trabajá movilidad de tobillo.")
                ejer.append("Estiramiento de pantorrilla en pared, 3×30 seg por lado antes de entrenar.")
            else:
                bien.append(f"Inclinación de tibia adecuada ({tob_max}°) — buena dorsiflexión de tobillo.")

        if not ejer:
            if any(v < 70 for v in [rod_izq, rod_der]):
                ejer.append("Sentadilla con pausa en cajón: pausá 2 seg en el punto más bajo y subí controlado.")
            elif any(v > 110 for v in [rod_izq, rod_der]):
                ejer.append("Goblet squat con kettlebell: el peso al frente obliga a bajar más con tronco vertical.")
            else:
                ejer.append("Sentadilla con pausa 3 seg en el punto más bajo para consolidar técnica.")

    else:  # peso_muerto
        cad_izq = angles.get("cadera_izq",  0)
        cad_der = angles.get("cadera_der",  0)
        sim_rod = angles.get("simetria_rodillas", 0)
        tronco  = angles.get("inclinacion_tronco", 0)

        for lado, val in [("izquierda", cad_izq), ("derecha", cad_der)]:
            if val < 30:
                riesg.append(f"Cadera {lado} muy cerrada ({val}°) — carga excesiva en lumbar.")
            elif val < 45:
                corr.append(f"Cadera {lado} en {val}° — empujá el suelo con los pies al iniciar, no tires con la espalda.")
            elif val <= 70:
                bien.append(f"Cadera {lado} en {val}° — posición inicial correcta.")
            elif val <= 90:
                corr.append(f"Cadera {lado} en {val}° — bajá un poco las caderas antes de tirar.")
            else:
                riesg.append(f"Cadera {lado} en {val}° — posición de sentadilla, no de peso muerto.")

        if tronco <= 15:
            bien.append(f"Tronco bien alineado ({tronco}°).")
        elif tronco <= 25:
            corr.append(f"Tronco inclinado {tronco}° — activá el core antes de tirar y mantené el pecho arriba.")
            ejer.append("Good morning con barra liviana para reforzar la musculatura erguida.")
        else:
            riesg.append(f"Inclinación de tronco excesiva: {tronco}° — alto riesgo de lesión lumbar.")
            ejer.append("Peso muerto rumano muy liviano enfocado en mantener la espalda recta.")

        if sim_rod > 10:
            riesg.append(f"Asimetría de rodillas importante ({sim_rod}°) — revisá posición de pies y agarre.")
        elif sim_rod > 5:
            corr.append(f"Leve asimetría de rodillas ({sim_rod}°) — chequeá ancho de pies.")

        if not ejer:
            ejer.append("Peso muerto con pausa a la rodilla: detené 2 seg a esa altura para reforzar posición del tronco.")

    lines = []
    if bien:
        lines.append("✅ Lo que está bien:")
        lines += [f"  • {x}" for x in bien]
    if corr:
        lines.append("\n⚠️ Qué corregir:")
        lines += [f"  • {x}" for x in corr]
    if riesg:
        lines.append("\n🔴 Riesgo de lesión:")
        lines += [f"  • {x}" for x in riesg]
    if ejer:
        lines.append("\n💪 Ejercicio correctivo:")
        lines += [f"  • {x}" for x in ejer]

    prefix = f"Análisis de {name_str}:\n\n" if name_str else ""
    return prefix + "\n".join(lines)




# ─── HTML APP ────────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>BiomecApp</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0a0e1a;--card:#111827;--border:#1f2937;--accent:#00d4ff;--accent2:#00ff88;--text:#e5e7eb;--muted:#6b7280;--danger:#ef4444;--warning:#f59e0b}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}

/* Registro */
#registration-screen{position:fixed;inset:0;background:var(--bg);z-index:100;display:flex;align-items:center;justify-content:center;padding:20px}
.reg-card{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:32px 24px;width:100%;max-width:400px}
.reg-logo{text-align:center;margin-bottom:24px}
.reg-logo-icon{display:inline-flex;align-items:center;justify-content:center;width:56px;height:56px;background:linear-gradient(135deg,var(--accent),var(--accent2));border-radius:14px;font-size:28px;margin-bottom:12px}
.reg-logo h1{font-size:24px;font-weight:800;color:var(--accent)}
.reg-logo p{font-size:13px;color:var(--muted);margin-top:2px}
.reg-form{display:flex;flex-direction:column;gap:14px}
.reg-field{display:flex;flex-direction:column;gap:6px}
.reg-field label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.07em;font-weight:600}
.reg-field input{background:var(--bg);border:1px solid var(--border);color:var(--text);padding:12px 14px;border-radius:10px;font-size:15px;width:100%;transition:border-color .2s}
.reg-field input:focus{outline:none;border-color:var(--accent)}
.reg-field input::placeholder{color:var(--muted)}
.reg-submit{width:100%;padding:15px;border-radius:12px;font-size:15px;font-weight:700;cursor:pointer;border:none;margin-top:4px;background:linear-gradient(135deg,var(--accent),var(--accent2));color:#000}
.reg-subtitle{font-size:12px;color:var(--muted);text-align:center;margin-top:12px;line-height:1.5}

/* App */
#main-app{display:none}
header{background:linear-gradient(135deg,#0a0e1a,#0f1f3d);border-bottom:1px solid var(--border);padding:14px 18px;display:flex;align-items:center;justify-content:space-between}
.logo{display:flex;align-items:center;gap:10px}
.logo-icon{width:36px;height:36px;background:linear-gradient(135deg,var(--accent),var(--accent2));border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:18px}
.logo h1{font-size:20px;font-weight:700;color:var(--accent)}
.logo p{font-size:11px;color:var(--muted);margin-top:1px}
.athlete-badge{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:6px 10px;font-size:12px;color:var(--accent2)}
main{padding:16px;max-width:600px;margin:0 auto}
.section-label{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin-bottom:8px}
.mode-selector{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:20px}
.mode-btn{background:var(--card);border:2px solid var(--border);color:var(--text);padding:16px 10px;border-radius:12px;cursor:pointer;text-align:center;transition:all .2s}
.mode-btn.active{border-color:var(--accent);background:rgba(0,212,255,.1);box-shadow:0 0 20px rgba(0,212,255,.2)}
.mode-btn .emoji{font-size:28px;display:block;margin-bottom:6px}
.mode-btn .name{font-size:14px;font-weight:700;display:block}
.mode-btn .desc{font-size:11px;color:var(--muted);margin-top:3px}
.exercise-selector{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px}
.exercise-btn{background:var(--card);border:2px solid var(--border);color:var(--text);padding:14px 10px;border-radius:12px;cursor:pointer;text-align:center;transition:all .2s}
.exercise-btn.active{border-color:var(--accent);background:rgba(0,212,255,.1)}
.exercise-btn .emoji{font-size:26px;display:block;margin-bottom:4px}
.exercise-btn .name{font-size:13px;font-weight:600}
.exercise-btn .desc{font-size:11px;color:var(--muted);margin-top:2px}
.tabs{display:grid;grid-template-columns:1fr 1fr;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:4px;margin-bottom:16px}
.tab-btn{padding:10px;border:none;background:transparent;color:var(--muted);border-radius:7px;cursor:pointer;font-size:13px;font-weight:500;transition:all .2s}
.tab-btn.active{background:var(--accent);color:#000;font-weight:700}
.upload-btn{background:var(--card);border:2px dashed var(--border);color:var(--text);padding:20px 10px;border-radius:12px;cursor:pointer;text-align:center;transition:all .2s;width:100%}
.upload-btn:hover{border-color:var(--accent);background:rgba(0,212,255,.05)}
.file-preview{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px;display:none;align-items:center;gap:12px;margin-bottom:16px}
.file-name{font-size:13px;font-weight:600}
.file-size{font-size:11px;color:var(--muted)}
.camera-container{position:relative;border-radius:12px;overflow:hidden;background:#000;margin-bottom:16px;width:100%;min-height:500px;max-height:90vh}
#camera-feed{width:100%;display:block;object-fit:cover}
.camera-overlay{position:absolute;bottom:12px;left:50%;transform:translateX(-50%);display:flex;gap:10px}
.capture-btn{background:var(--accent2);color:#000;border:none;padding:12px 22px;border-radius:50px;font-weight:700;font-size:14px;cursor:pointer}
.stop-btn{background:var(--danger);color:#fff;border:none;padding:12px 18px;border-radius:50px;font-weight:700;font-size:14px;cursor:pointer}
.start-camera-btn,.analyze-btn,.new-analysis-btn,.pdf-btn{width:100%;padding:15px;border-radius:12px;font-size:15px;font-weight:700;cursor:pointer;border:none;margin-bottom:14px}
.start-camera-btn{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#000}
.analyze-btn{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#000;display:none}
.new-analysis-btn{background:var(--card);border:1px solid var(--border);color:var(--text)}
.pdf-btn{background:linear-gradient(135deg,#7c3aed,#a855f7);color:#fff}
.auto-toggle{display:flex;align-items:center;gap:8px;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:10px 14px;margin-bottom:12px;font-size:13px}
.toggle-switch{position:relative;width:40px;height:22px;margin-left:auto;flex-shrink:0}
.toggle-switch input{display:none}
.toggle-slider{position:absolute;cursor:pointer;inset:0;background:var(--border);border-radius:22px;transition:.3s}
.toggle-slider:before{content:'';position:absolute;width:16px;height:16px;left:3px;top:3px;background:#fff;border-radius:50%;transition:.3s}
input:checked+.toggle-slider{background:var(--accent)}
input:checked+.toggle-slider:before{transform:translateX(18px)}
.loading{display:none;text-align:center;padding:32px}
.spinner{width:40px;height:40px;border:3px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite;margin:0 auto 12px}
@keyframes spin{to{transform:rotate(360deg)}}
.loading p{font-size:13px;color:var(--muted);margin-top:4px}
.results{display:none}
.result-image{width:100%;border-radius:12px;margin-bottom:16px}
.angles-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px}
.angle-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:12px}
.angle-card .label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px}
.angle-card .value{font-size:26px;font-weight:700;color:var(--accent)}
.angle-card .status{font-size:11px;margin-top:2px}
.status-ok{color:var(--accent2)}.status-warn{color:var(--warning)}.status-bad{color:var(--danger)}
.feedback-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:16px}
.feedback-card h3{font-size:12px;text-transform:uppercase;letter-spacing:.1em;color:var(--accent);margin-bottom:12px}
.feedback-text{font-size:14px;line-height:1.75;white-space:pre-wrap}
.email-ok{background:rgba(0,255,136,.08);border:1px solid rgba(0,255,136,.3);color:var(--accent2);border-radius:10px;padding:12px 14px;margin-bottom:16px;font-size:13px;font-weight:500}
.email-warn{background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.3);color:var(--warning);border-radius:10px;padding:12px 14px;margin-bottom:16px;font-size:13px;font-weight:500}
.error-box{background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.4);color:#ef4444;border-radius:10px;padding:12px 14px;margin-bottom:14px;font-size:13px;font-weight:500;display:none}
.tab-panel{display:none}
.tab-panel.active{display:block}
</style>
</head>
<body>

<!-- REGISTRO -->
<div id="registration-screen">
  <div class="reg-card">
    <div class="reg-logo">
      <div class="reg-logo-icon">⚡</div>
      <h1>BiomecApp</h1>
      <p>Centro de Alto Rendimiento</p>
    </div>
    <form class="reg-form" id="reg-form" onsubmit="startSession(event)">
      <div class="reg-field">
        <label>Nombre</label>
        <input type="text" id="reg-nombre" required placeholder="Juan" autocomplete="given-name">
      </div>
      <div class="reg-field">
        <label>Apellido</label>
        <input type="text" id="reg-apellido" required placeholder="García" autocomplete="family-name">
      </div>
      <div class="reg-field">
        <label>Correo electrónico</label>
        <input type="email" id="reg-email" required placeholder="juan@ejemplo.com" autocomplete="email">
      </div>
      <button type="submit" class="reg-submit">Comenzar análisis →</button>
    </form>
    <p class="reg-subtitle">Al finalizar el análisis podrás descargar un informe PDF completo.</p>
  </div>
</div>

<!-- APP -->
<div id="main-app">
<header>
  <div class="logo">
    <div class="logo-icon">⚡</div>
    <div><h1>BiomecApp</h1><p>Centro de Alto Rendimiento</p></div>
  </div>
  <div id="athlete-badge" class="athlete-badge"></div>
</header>

<main>
  <p class="section-label">Tipo de Análisis</p>
  <div class="mode-selector">
    <button class="mode-btn active" id="btn-biomecania" onclick="selectMode('biomecania')">
      <span class="emoji">🏋️</span><span class="name">Biomecánica</span>
      <span class="desc">Técnica de movimiento</span>
    </button>
    <button class="mode-btn" id="btn-saltos" onclick="selectMode('saltos')">
      <span class="emoji">🦘</span><span class="name">Saltos</span>
      <span class="desc">Análisis de saltabilidad</span>
    </button>
  </div>

  <p class="section-label">Ejercicio</p>
  <div id="biomecania-exercises" class="exercise-selector">
    <button class="exercise-btn active" id="btn-sentadilla" onclick="selectExercise('sentadilla')">
      <span class="emoji">🏋️</span><span class="name">Sentadilla</span>
      <span class="desc">Rodillas · Cadera · Simetría</span>
    </button>
    <button class="exercise-btn" id="btn-peso_muerto" onclick="selectExercise('peso_muerto')">
      <span class="emoji">💪</span><span class="name">Peso Muerto</span>
      <span class="desc">Cadera · Columna · Tronco</span>
    </button>
  </div>

  <div id="saltos-exercises" class="exercise-selector" style="display:none">
    <button class="exercise-btn active" id="btn-salto_vertical" onclick="selectExercise('salto_vertical')">
      <span class="emoji">⬆️</span><span class="name">Salto Vertical</span>
      <span class="desc">Altura · Potencia · Despegue</span>
    </button>
    <button class="exercise-btn" id="btn-salto_horizontal" onclick="selectExercise('salto_horizontal')">
      <span class="emoji">➡️</span><span class="name">Salto Horizontal</span>
      <span class="desc">Distancia · Balance</span>
    </button>
  </div>

  <div class="tabs">
    <button class="tab-btn active" id="tab-upload-btn" onclick="switchTab('upload')">📤 Subir Video</button>
    <button class="tab-btn" id="tab-record-btn" onclick="switchTab('record')">📹 Grabar Video</button>
    <button class="tab-btn" id="tab-camera-btn" onclick="switchTab('camera')">📸 Cámara en Vivo</button>
  </div>

  <div class="tab-panel active" id="tab-upload">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px">
      <button class="upload-btn" onclick="document.getElementById('file-video').click()">
        <span style="font-size:28px;display:block;margin-bottom:6px">🎬</span>
        <span style="font-size:13px;font-weight:700;display:block">Subir Video</span>
        <span style="font-size:11px;color:var(--muted);display:block;margin-top:2px">MP4 · MOV · AVI</span>
      </button>
      <button class="upload-btn" onclick="document.getElementById('file-photo').click()">
        <span style="font-size:28px;display:block;margin-bottom:6px">🖼️</span>
        <span style="font-size:13px;font-weight:700;display:block">Subir Foto</span>
        <span style="font-size:11px;color:var(--muted);display:block;margin-top:2px">JPG · PNG · HEIC</span>
      </button>
    </div>
    <input type="file" id="file-video" accept="video/*" style="display:none" onchange="handleFileSelect(event)">
    <input type="file" id="file-photo" accept="image/*" style="display:none" onchange="handleFileSelect(event)">
    <div class="file-preview" id="file-preview">
      <span style="font-size:28px" id="upload-icon">🎥</span>
      <div><div class="file-name" id="file-name-display"></div>
           <div class="file-size" id="file-size-display"></div></div>
    </div>
  </div>

  <div class="tab-panel" id="tab-record">
    <div id="record-start-area">
      <button class="start-camera-btn" onclick="startRecording()" style="background:#00ff00;color:#000;font-weight:bold;font-size:16px">
        🔴 EMPEZAR A GRABAR
      </button>
      <div style="font-size:12px;color:var(--muted);margin-top:10px;text-align:center">
        <p>Toca para empezar</p>
        <p>El video se procesa automáticamente</p>
      </div>
    </div>
    <div id="record-active" style="display:none">
      <div class="camera-container">
        <video id="record-feed" autoplay playsinline muted style="transform: scaleX(-1);"></video>
        <div class="camera-overlay">
          <div style="font-size:20px;color:#ff4444;font-weight:bold" id="record-timer">00:00</div>
          <div style="display:flex;gap:10px;justify-content:center;flex-direction:column">
            <button class="stop-btn" id="record-stop-btn" onclick="stopRecording()" style="background:#ff4444;color:#fff;font-weight:bold;font-size:16px">
              ⏹ PARAR
            </button>
            <button class="capture-btn" onclick="switchCamera()" style="font-size:12px;padding:8px">🔄 Cambiar Cámara</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="tab-panel" id="tab-camera">
    <div id="camera-start-area">
      <button class="start-camera-btn" onclick="startCamera()">📸 Activar Cámara</button>
      <div class="auto-toggle">
        <span>Análisis automático (cada 3 seg)</span>
        <label class="toggle-switch">
          <input type="checkbox" id="auto-toggle">
          <span class="toggle-slider"></span>
        </label>
      </div>
    </div>
    <div id="camera-active" style="display:none">
      <div class="camera-container">
        <video id="camera-feed" autoplay playsinline muted></video>
        <div class="camera-overlay">
          <button class="capture-btn" onclick="captureAndAnalyze()">📸 Analizar</button>
          <button class="stop-btn" onclick="stopCamera()">⏹ Parar</button>
        </div>
      </div>
    </div>
  </div>

  <div id="error-box" class="error-box"></div>

  <button class="analyze-btn" id="analyze-btn" onclick="runAnalysis()">⚡ Analizar Movimiento</button>

  <div class="loading" id="loading">
    <div class="spinner"></div>
    <p>Procesando con MediaPipe...</p>
    <p>Calculando ángulos...</p>
  </div>

  <div class="results" id="results">
    <img class="result-image" id="result-image" src="" alt="Análisis de postura">
    <div class="angles-grid" id="angles-grid"></div>
    <div class="feedback-card">
      <h3>📋 Análisis Biomecánico</h3>
      <div class="feedback-text" id="feedback-text"></div>
    </div>
    <button class="pdf-btn" onclick="downloadPDF()">📄 Descargar Informe PDF</button>
    <button class="new-analysis-btn" onclick="resetAnalysis()">🔄 Nuevo Análisis</button>
  </div>
</main>
</div>

<script>
let selectedMode     = 'biomecania';
let selectedExercise = 'sentadilla';
let selectedFile     = null;
let mediaRecorder    = null;
let recordedChunks   = [];
let recordStartTime  = 0;
let facingMode       = 'user';
let cameraStream     = null;
let autoInterval     = null;
let lastResult       = null;
let athlete = { nombre:'', apellido:'', email:'' };

function startSession(e) {
  e.preventDefault();
  athlete.nombre   = document.getElementById('reg-nombre').value.trim();
  athlete.apellido = document.getElementById('reg-apellido').value.trim();
  athlete.email    = document.getElementById('reg-email').value.trim();
  document.getElementById('registration-screen').style.display = 'none';
  document.getElementById('main-app').style.display = 'block';
  document.getElementById('athlete-badge').textContent = athlete.nombre + ' ' + athlete.apellido;
}

function selectMode(mode) {
  selectedMode = mode;
  document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('btn-' + mode).classList.add('active');

  if (mode === 'biomecania') {
    document.getElementById('biomecania-exercises').style.display = 'grid';
    document.getElementById('saltos-exercises').style.display = 'none';
    selectExercise('sentadilla');
  } else if (mode === 'saltos') {
    document.getElementById('biomecania-exercises').style.display = 'none';
    document.getElementById('saltos-exercises').style.display = 'grid';
    selectExercise('salto_vertical');
  }
}

function selectExercise(type) {
  selectedExercise = type;
  document.querySelectorAll('.exercise-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('btn-' + type).classList.add('active');
}

// ─── GRABAR VIDEO ───────────────────────────────────────────────────────────

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: facingMode, width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false
    });
    const video = document.getElementById('record-feed');
    video.srcObject = stream;

    recordedChunks = [];

    // Probar diferentes codecs
    let mimeType = 'video/webm;codecs=vp9';
    if (!MediaRecorder.isTypeSupported(mimeType)) {
      mimeType = 'video/webm;codecs=vp8';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'video/webm';
      }
    }

    mediaRecorder = new MediaRecorder(stream, { mimeType: mimeType });

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) recordedChunks.push(e.data);
    };

    mediaRecorder.onstop = () => {
      const blob = new Blob(recordedChunks, { type: 'video/webm' });
      uploadRecordedVideo(blob);
      stream.getTracks().forEach(track => track.stop());
    };

    mediaRecorder.start();
    recordStartTime = Date.now();

    document.getElementById('record-start-area').style.display = 'none';
    document.getElementById('record-active').style.display = 'block';
    updateRecordTimer();

  } catch (err) {
    alert('No se pudo acceder a la cámara: ' + err.message);
  }
}

function updateRecordTimer() {
  if (!mediaRecorder || mediaRecorder.state !== 'recording') return;
  const elapsed = Math.floor((Date.now() - recordStartTime) / 1000);
  const min = Math.floor(elapsed / 60);
  const sec = elapsed % 60;
  document.getElementById('record-timer').textContent =
    (min < 10 ? '0' : '') + min + ':' + (sec < 10 ? '0' : '') + sec;
  setTimeout(updateRecordTimer, 100);
}

function switchCamera() {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    const stream = document.getElementById('record-feed').srcObject;
    stream.getTracks().forEach(track => track.stop());

    facingMode = facingMode === 'user' ? 'environment' : 'user';
    startRecording();
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop();
    document.getElementById('record-active').style.display = 'none';
    document.getElementById('record-start-area').style.display = 'block';
    document.getElementById('loading').style.display = 'flex';
  }
}

async function uploadRecordedVideo(blob) {
  try {
    const formData = new FormData();
    formData.append('video', blob, 'recorded_video.webm');
    formData.append('exercise_type', selectedExercise);
    formData.append('athlete_name', athlete.nombre);
    formData.append('athlete_lastname', athlete.apellido);
    formData.append('athlete_email', athlete.email);

    const res = await fetch('/analyze-video', { method: 'POST', body: formData });
    const data = await res.json();

    if (res.ok) {
      showResults(data);
    } else {
      document.getElementById('error-box').textContent = 'Error: ' + (data.detail || 'Análisis fallido');
      document.getElementById('error-box').style.display = 'block';
    }
  } catch (err) {
    document.getElementById('error-box').textContent = 'Error: ' + err.message;
    document.getElementById('error-box').style.display = 'block';
  } finally {
    document.getElementById('loading').style.display = 'none';
  }
}

function switchTab(tab) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + tab).classList.add('active');
  document.getElementById('tab-' + tab + '-btn').classList.add('active');
  if (tab !== 'camera') stopCamera();
}

function handleFileSelect(e) { if (e.target.files[0]) setFile(e.target.files[0]); }
function handleDrop(e) {
  e.preventDefault();
  const f = e.dataTransfer.files[0];
  if (f && (f.type.startsWith('video/') || f.type.startsWith('image/'))) setFile(f);
}
function setFile(file) {
  selectedFile = file;
  const isImage = file.type.startsWith('image/');
  document.getElementById('upload-icon').textContent = isImage ? '🖼️' : '🎬';
  document.getElementById('file-preview').style.display = 'flex';
  document.getElementById('file-name-display').textContent = file.name;
  document.getElementById('file-size-display').textContent = (file.size/1024/1024).toFixed(1) + ' MB';
  document.getElementById('analyze-btn').style.display = 'block';
}

async function startCamera() {
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' }, width: { ideal: 640 } }
    });
    const video = document.getElementById('camera-feed');
    video.srcObject = cameraStream;
    video.play();
    document.getElementById('camera-start-area').style.display = 'none';
    document.getElementById('camera-active').style.display = 'block';
    document.getElementById('auto-toggle').onchange = function() {
      clearInterval(autoInterval);
      if (this.checked) autoInterval = setInterval(captureAndAnalyze, 3000);
    };
  } catch(err) {
    showError('No se pudo acceder a la cámara: ' + err.message);
  }
}

function stopCamera() {
  if (cameraStream) { cameraStream.getTracks().forEach(t => t.stop()); cameraStream = null; }
  clearInterval(autoInterval);
  document.getElementById('camera-start-area').style.display = 'block';
  document.getElementById('camera-active').style.display = 'none';
}

function captureFrame() {
  const video = document.getElementById('camera-feed');
  if (!video.videoWidth || !video.videoHeight) {
    throw new Error('La cámara aún no está lista. Esperá un segundo e intentá de nuevo.');
  }
  const c = document.createElement('canvas');
  c.width = video.videoWidth; c.height = video.videoHeight;
  c.getContext('2d').drawImage(video, 0, 0);
  return c.toDataURL('image/jpeg', 0.85).split(',')[1];
}

async function captureAndAnalyze() { await runAnalysis(true); }

function showError(msg) {
  const b = document.getElementById('error-box');
  b.textContent = '⚠️ ' + msg;
  b.style.display = 'block';
  // No se oculta solo — el usuario lo ve hasta que sube otro archivo
}

async function runAnalysis() {
  const activeTab = document.querySelector('.tab-panel.active').id;
  const isCamera  = activeTab === 'tab-camera';

  document.getElementById('error-box').style.display = 'none';
  document.getElementById('analyze-btn').style.display = 'none';
  document.getElementById('loading').style.display = 'block';
  document.getElementById('results').style.display = 'none';

  try {
    const fd = new FormData();
    fd.append('athlete_name',     athlete.nombre);
    fd.append('athlete_lastname', athlete.apellido);
    fd.append('athlete_email',    athlete.email);

    let response;
    if (!isCamera && selectedFile && selectedFile.type.startsWith('image/')) {
      // Foto: dibujar por canvas para aplicar rotación EXIF del celular
      const b64 = await new Promise((resolve, reject) => {
        const img = new Image();
        const url = URL.createObjectURL(selectedFile);
        img.onload = () => {
          const canvas = document.createElement('canvas');
          canvas.width  = img.naturalWidth;
          canvas.height = img.naturalHeight;
          canvas.getContext('2d').drawImage(img, 0, 0);
          URL.revokeObjectURL(url);
          resolve(canvas.toDataURL('image/jpeg', 0.9).split(',')[1]);
        };
        img.onerror = reject;
        img.src = url;
      });
      fd.append('image_base64', b64);
      fd.append('exercise_type', selectedExercise);
      response = await fetch('/analyze-frame', { method:'POST', body: fd });
    } else if (!isCamera && selectedFile) {
      fd.append('video', selectedFile);
      fd.append('exercise_type', selectedExercise);
      response = await fetch('/analyze-video', { method:'POST', body: fd });
    } else if (isCamera && cameraStream) {
      fd.append('image_base64', captureFrame());
      fd.append('exercise_type', selectedExercise);
      response = await fetch('/analyze-frame', { method:'POST', body: fd });
    } else {
      throw new Error('Seleccioná un video o activá la cámara primero');
    }

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      let msg = 'Error del servidor';
      if (errData.detail) {
        if (typeof errData.detail === 'string') msg = errData.detail;
        else if (Array.isArray(errData.detail)) msg = errData.detail.map(e => e.msg || '').join(', ');
        else msg = JSON.stringify(errData.detail);
      }
      throw new Error(msg);
    }

    showResults(await response.json());

  } catch(err) {
    showError(err.message);
    document.getElementById('analyze-btn').style.display = 'block';
  } finally {
    document.getElementById('loading').style.display = 'none';
  }
}

const LABELS = {
  rodilla_izq:'Rodilla Izq', rodilla_der:'Rodilla Der',
  cadera_izq:'Cadera Izq',   cadera_der:'Cadera Der',
  tobillo_izq:'Tibia Izq (incl.)', tobillo_der:'Tibia Der (incl.)',
  simetria_rodillas:'Simetría', inclinacion_tronco:'Tronco',
  altura_salto_cm:'Altura (cm)', tiempo_vuelo_ms:'Tiempo vuelo (ms)',
  simetria_piernas:'Simetría (°)'
};
const RANGES = {
  rodilla_izq:{ok:[70,100],warn:[60,120]}, rodilla_der:{ok:[70,100],warn:[60,120]},
  cadera_izq:{ok:[60,100],warn:[45,120]},  cadera_der:{ok:[60,100],warn:[45,120]},
  tobillo_izq:{ok:[0,32],warn:[0,40]},   tobillo_der:{ok:[0,32],warn:[0,40]},
  simetria_rodillas:{ok:[0,5],warn:[0,10]},inclinacion_tronco:{ok:[0,15],warn:[0,25]},
  altura_salto_cm:{ok:[40,100],warn:[20,120]}, tiempo_vuelo_ms:{ok:[400,1000],warn:[200,1200]},
  simetria_piernas:{ok:[0,10],warn:[0,20]}
};

function showResults(data) {
  lastResult = data;
  document.getElementById('result-image').src = 'data:image/jpeg;base64,' + data.annotated_image;
  const grid = document.getElementById('angles-grid');
  grid.innerHTML = '';
  for (const [k, v] of Object.entries(data.angles)) {
    const r = RANGES[k];
    let cls = 'status-ok', txt = '✅ Ideal';
    if (r) {
      if (v < r.ok[0] || v > r.ok[1]) {
        cls = (v < r.warn[0] || v > r.warn[1]) ? 'status-bad' : 'status-warn';
        txt = cls === 'status-bad' ? '🔴 Revisar' : '⚠️ Ajustar';
      }
    }
    // Determinar símbolo de unidad (no todos tienen grados)
    let symbol = '°';
    if (k === 'altura_salto_cm') symbol = 'cm';
    else if (k === 'tiempo_vuelo_ms') symbol = 'ms';

    grid.innerHTML += `<div class="angle-card">
      <div class="label">${LABELS[k]||k}</div>
      <div class="value">${v}${symbol}</div>
      <div class="status ${cls}">${txt}</div>
    </div>`;
  }
  document.getElementById('feedback-text').textContent = data.feedback;
  document.getElementById('results').style.display = 'block';

  // SI ES SALTO, CARGAR ESTADO
  if (selectedMode === 'saltos' && data.angles.altura_salto_cm) {
    loadJumpStatus(athlete.nombre, data.angles.altura_salto_cm);
  }

  document.getElementById('results').scrollIntoView({behavior:'smooth'});
}

async function loadJumpStatus(nombre, altura) {
  try {
    const res = await fetch(`/jump-status/${encodeURIComponent(nombre)}/${altura}`);
    const status = await res.json();

    let colorSemaforo = 'gray';
    if (status.estado === 'ÓPTIMO') colorSemaforo = 'green';
    else if (status.estado === 'NORMAL') colorSemaforo = 'yellow';
    else if (status.estado === 'BAJO') colorSemaforo = 'red';

    const statusHtml = `
      <div style="margin-top: 20px; padding: 20px; background: #1a1a2e; border-radius: 8px; border-left: 4px solid ${colorSemaforo};">
        <div style="text-align: center;">
          <div style="font-size: 14px; color: #888; margin-bottom: 10px; text-transform: uppercase;">ESTADO NEUROMUSCULAR</div>
          <div style="font-size: 32px; font-weight: bold; color: ${colorSemaforo}; margin-bottom: 15px;">${status.estado}</div>
          <div style="display: inline-block; width: 60px; height: 60px; border-radius: 50%; background-color: ${colorSemaforo}; margin-bottom: 15px;"></div>
        </div>
        <div style="margin-top: 15px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 4px;">
          <div style="font-size: 12px; color: #aaa; margin-bottom: 5px;">Altura actual: <span style="color: #fff; font-weight: bold;">${status.altura_actual} cm</span></div>
          <div style="font-size: 12px; color: #aaa; margin-bottom: 5px;">Promedio (3 mejores): <span style="color: #fff; font-weight: bold;">${status.promedio} cm</span></div>
          <div style="font-size: 14px; color: ${status.diferencia_pct >= 0 ? 'lime' : 'orange'}; font-weight: bold;">
            ${status.diferencia_pct >= 0 ? '+' : ''}${status.diferencia_pct}%
          </div>
        </div>
      </div>
    `;

    document.getElementById('feedback-text').insertAdjacentHTML('afterend', statusHtml);
  } catch (e) {
    console.log('No hay histórico aún');
  }
}

async function downloadPDF() {
  if (!lastResult) return;
  const { jsPDF } = window.jspdf;
  const doc  = new jsPDF({ orientation:'portrait', unit:'mm', format:'a4' });
  const W    = 210;
  let ex = selectedExercise;
  if (selectedExercise === 'sentadilla') ex = 'Sentadilla';
  else if (selectedExercise === 'peso_muerto') ex = 'Peso Muerto';
  else if (selectedExercise === 'salto_vertical') ex = 'Salto Vertical';
  else if (selectedExercise === 'salto_horizontal') ex = 'Salto Horizontal';
  const fecha = new Date().toLocaleDateString('es-AR');

  // ── Encabezado ──────────────────────────────────────────
  doc.setFillColor(10, 14, 26);
  doc.rect(0, 0, W, 38, 'F');
  doc.setFontSize(22); doc.setTextColor(0, 212, 255);
  doc.text('BiomecApp', W/2, 17, { align:'center' });
  doc.setFontSize(10); doc.setTextColor(107, 114, 128);
  doc.text('Centro de Alto Rendimiento', W/2, 25, { align:'center' });
  doc.setFontSize(9);
  doc.text('Informe biomecánico generado automáticamente', W/2, 32, { align:'center' });

  // ── Datos del atleta ─────────────────────────────────────
  doc.setFillColor(17, 24, 39);
  doc.roundedRect(14, 42, W-28, 28, 3, 3, 'F');
  doc.setFontSize(14); doc.setTextColor(229, 231, 235);
  doc.text(athlete.nombre + ' ' + athlete.apellido, 20, 52);
  doc.setFontSize(9); doc.setTextColor(107, 114, 128);
  doc.text('Email: ' + athlete.email, 20, 60);
  doc.text('Ejercicio: ' + ex + '    |    Fecha: ' + fecha, 20, 67);

  // ── Imagen anotada ───────────────────────────────────────
  try {
    doc.addImage('data:image/jpeg;base64,' + lastResult.annotated_image, 'JPEG', 14, 75, W-28, 100);
  } catch(e) { /* si falla la imagen, seguimos igual */ }

  // ── Ángulos ──────────────────────────────────────────────
  let y = 182;
  doc.setFontSize(11); doc.setTextColor(0, 212, 255);
  doc.text('Ángulos Medidos', 14, y); y += 6;
  doc.setDrawColor(31, 41, 55); doc.setLineWidth(0.3);
  doc.line(14, y, W-14, y); y += 5;

  const entries = Object.entries(lastResult.angles);
  const colW = (W-28) / 2;
  entries.forEach(([k, v], i) => {
    const col = i % 2;
    const xOff = 14 + col * colW;
    if (col === 0 && i > 0) y += 8;
    doc.setFontSize(9); doc.setTextColor(107, 114, 128);
    doc.text(LABELS[k] || k, xOff, y);
    doc.setFontSize(11); doc.setTextColor(229, 231, 235);
    doc.text(v + '°', xOff + colW - 18, y);
  });
  if (entries.length % 2 !== 0) y += 8;

  // ── Feedback ─────────────────────────────────────────────
  y += 8;
  doc.setFontSize(11); doc.setTextColor(0, 212, 255);
  doc.text('Análisis Biomecánico', 14, y); y += 6;
  doc.setDrawColor(31, 41, 55); doc.line(14, y, W-14, y); y += 5;
  doc.setFontSize(9); doc.setTextColor(229, 231, 235);
  const lines = doc.splitTextToSize(lastResult.feedback, W-28);
  // Nueva página si no hay espacio
  if (y + lines.length * 5 > 285) { doc.addPage(); y = 20; }
  doc.text(lines, 14, y);

  doc.save('BiomecApp_' + athlete.nombre + '_' + athlete.apellido + '_' + ex + '.pdf');
}

function resetAnalysis() {
  selectedFile = null;
  lastResult   = null;
  document.getElementById('file-preview').style.display = 'none';
  document.getElementById('file-video').value = '';
  document.getElementById('file-photo').value = '';
  document.getElementById('results').style.display = 'none';
  document.getElementById('analyze-btn').style.display = 'none';
  document.getElementById('error-box').style.display = 'none';
  window.scrollTo({top:0, behavior:'smooth'});
}
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML


@app.post("/analyze-video")
async def analyze_video_endpoint(
    video: UploadFile = File(...),
    exercise_type: str = Form(...),
    athlete_name: str = Form(""),
    athlete_lastname: str = Form(""),
    athlete_email: str = Form(""),
):
    try:
        suffix = os.path.splitext(video.filename)[1] or ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await video.read())
            tmp_path = tmp.name

        full_name = f"{athlete_name} {athlete_lastname}".strip()

        # 🚀 JUMP ANALYSIS (Phase 2)
        if exercise_type in ["salto_vertical", "salto_horizontal"]:
            angles, annotated, jump_data = analyze_jump_video(tmp_path, exercise_type)
            if angles is None:
                os.unlink(tmp_path)
                raise HTTPException(status_code=400, detail="No se pudo procesar el video. Asegurate de que el cuerpo entero sea visible durante el salto.")
        else:
            # BIOMECHANICS (existing)
            key_frame = extract_key_frame(tmp_path, exercise_type)
            if key_frame is None:
                os.unlink(tmp_path)
                raise HTTPException(status_code=400, detail="No se pudo procesar el video. El cuerpo debe ser visible en su totalidad.")

            angles, annotated = analyze_frame(key_frame, exercise_type)
            if angles is None:
                os.unlink(tmp_path)
                raise HTTPException(status_code=400, detail="No se detectó ninguna persona en el video.")

        os.unlink(tmp_path)

        _, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
        ann_b64 = base64.b64encode(buf).decode()

        feedback = generate_feedback(angles, exercise_type, full_name)

        # 📊 Guardar automáticamente en Google Sheets (con email)
        save_to_sheets(full_name, exercise_type, angles, feedback, athlete_email=athlete_email)

        return JSONResponse({"angles": angles, "annotated_image": ann_b64, "feedback": feedback})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze-frame")
async def analyze_frame_endpoint(
    image_base64: str = Form(...),
    exercise_type: str = Form(...),
    athlete_name: str = Form(""),
    athlete_lastname: str = Form(""),
    athlete_email: str = Form(""),
):
    try:
        img_data = base64.b64decode(image_base64)
        nparr    = np.frombuffer(img_data, np.uint8)
        image    = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise HTTPException(status_code=400, detail="No se pudo decodificar la imagen.")

        # Para saltos desde foto/cámara en vivo, mostrar advertencia pero permitir análisis de postura
        is_jump = exercise_type in ["salto_vertical", "salto_horizontal"]

        angles, annotated = analyze_frame(image, exercise_type)
        if angles is None:
            raise HTTPException(status_code=400, detail="No se detectó ninguna persona. Asegurate de que el cuerpo entero sea visible.")

        _, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
        ann_b64 = base64.b64encode(buf).decode()

        full_name = f"{athlete_name} {athlete_lastname}".strip()

        # Para saltos desde foto, agregar nota en feedback
        feedback = generate_feedback(angles, exercise_type, full_name)
        if is_jump:
            feedback += "\n\n⚠️ NOTA: Esta es una foto estática. Para un análisis completo de altura, tiempo de vuelo y potencia, sube un VIDEO del salto completo."

        # 📊 Guardar automáticamente en Google Sheets (con email)
        save_to_sheets(full_name, exercise_type, angles, feedback, athlete_email=athlete_email)

        return JSONResponse({"angles": angles, "annotated_image": ann_b64, "feedback": feedback})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jump-status/{athlete_name}/{altura}")
async def get_jump_status(athlete_name: str, altura: float):
    """Obtiene estado del salto comparando con histórico del atleta"""
    from google_sheets_integration import sheets_manager

    if not sheets_manager:
        return JSONResponse({"error": "Google Sheets no conectado"})

    history = sheets_manager.get_jump_history(athlete_name)
    if not history:
        return JSONResponse({"status": "INICIAL", "promedio": altura, "diferencia_pct": 0, "estado": "PRIMER SALTO"})

    promedio = history["promedio"]
    diferencia = altura - promedio
    diferencia_pct = (diferencia / promedio * 100) if promedio > 0 else 0

    if diferencia_pct >= 5:
        estado = "ÓPTIMO"
    elif diferencia_pct >= -5:
        estado = "NORMAL"
    else:
        estado = "BAJO"

    return JSONResponse({
        "estado": estado,
        "altura_actual": round(altura, 1),
        "promedio": round(promedio, 1),
        "diferencia_pct": round(diferencia_pct, 1),
        "mejores_3": [round(x, 1) for x in history["mejores_3"]]
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
