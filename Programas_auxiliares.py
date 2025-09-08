import csv
import math
import pathlib
import numpy as np
from collections import Counter
import requests
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import os
import pandas as pd
import time
from datetime import datetime, timedelta
import json
import openpyxl

# === CONSTANTES ===
URL_API = "https://api.casinoscores.com/svc-evolution-game-events/api/bacbo/latest"
# #START_URL = "https://api.casinoscores.com/svc-evolution-game-events/api/bacbo?page=1&size=18&sort=data.settledAt,desc&duration=7200&wheelResults=PlayerWon,BankerWon,Tie"  # pega aquí el link copiado
# #START_URL = "https://api.casinoscores.com/svc-evolution-game-events/api/bacbo?page=1&size=18&sort=data.settledAt,desc&duration=2120&wheelResults=PlayerWon,BankerWon,Tie"  # pega aquí el link copiado
# START_URL = "https://api.casinoscores.com/svc-evolution-game-events/api/immersiveroulette?page=0&size=29&sort=data.settledAt,desc&duration=72"
# TARGET = 4000

HEADERS = {
    "User-Agent": "Mozilla/5.0",
}


# === INICIALIZAR LISTAS ===
numeros_capturados = []  # Global temporal para mostrar todos los números capturados con colores

# Ruta del chromedriver (asegúrate de que esté junto al .exe si empaquetas)
chrome_driver_path = os.path.join(os.getcwd(), "chromedriver.exe")

def set_query_param(url, **updates):
    parts = urlparse(url)
    q = parse_qs(parts.query)
    for k, v in updates.items():
        q[k] = [str(v)]
    new_query = urlencode(q, doseq=True)
    return urlunparse((parts.scheme, parts.netloc, parts.path, parts.params, new_query, parts.fragment))


def extract_items(payload):
    # Busca lista dentro del JSON
    if isinstance(payload, list):
        return payload
    for key in ("content", "items", "results", "data", "list"):
        val = payload.get(key)
        if isinstance(val, list):
            return val
        if isinstance(val, dict):
            for subkey in ("content", "items", "results", "list"):
                subval = val.get(subkey)
                if isinstance(subval, list):
                    return subval
    return []


def normalize(row, outcome=None):
    """Extrae solo la información del diccionario 'data'."""
    d = row.get("data", {})
    started_at = d.get("startedAt")
    res = d.get("result", {})
    outcome = res.get("outcome")["number"]
    return {
        "startedAt": started_at,
        "numero": outcome
    }


def load_db(file_name):
    FILE = pathlib.Path(file_name)
    if not FILE.exists():
        return []
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        # archivo corrupto → empezamos vacío
        return []


def find_index_by_id(data, ruleta: str):
    for i, rec in enumerate(data):
        if rec.get("ruleta") == ruleta:
            return i
    return None


def reed_URL(TARGET,START_URL ):
    qs = parse_qs(urlparse(START_URL).query)
    page0 = 0
    size = int(qs.get("size", [50])[0])
    need_pages = math.ceil(TARGET / size)

    all_rows = []
    seen = set()
    i = 0

    for i in range(need_pages):
        page = page0 + i
        url = set_query_param(START_URL, page=page, size=size)
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        payload = r.json()
        items = extract_items(payload)
        if not items:
            print(f"Sin datos en página {page}")
            break

        for it in items:
            norm = normalize(it)
            # Usar startedAt como identificador único
            if norm["startedAt"] in seen:
                continue
            seen.add(norm["startedAt"])
            all_rows.append(norm)
            if len(all_rows) >= TARGET:
                break

        print(f"\rPágina {page} -> acumuladas: {len(all_rows)}", end="", flush=True)
        if len(all_rows) >= TARGET:
            break
        time.sleep(0.3)

    # Ordenar ascendente por fecha/hora
    all_rows.sort(key=lambda r: datetime.fromisoformat(r["startedAt"].replace("Z", "+00:00")))

    # Guardar en CSV
    with open("ultimos_numeros.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_rows[0].keys())
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\n\n✅Recoleccion de datos satifactoria con {len(all_rows)} jugadas.")


def lectura_ultimos_numeros(ruleta_play):
    # Cargar configuración

    data = load_db("ruletas.json")
    idx = find_index_by_id(data, ruleta_play)

    if idx is None:
        print("Esa ruleta no esta Configurada en el Bot")
        return False
    else:
        datos = data[idx]
        #TARGET = datos.get("max_numeros")
        #START_URL = datos.get("API")

    # === RECOLECTAR 500 ULTIMAS JUGADAS =====
    while True:
        respuesta = input(f"🎰 Deseas recolector los ultimos {ruleta_play} numeros (S/N)?:").upper()
        print("-" * 50)
        if respuesta =="S" or respuesta == "N":
            break

    if respuesta =="S":
        print("\n🔍 Iniciando recopilación...")
        print("Abriendo sitio web... (Resuelve el CAPTCHA si aparece)")
        reed_URL(datos.get("max_numeros"), datos.get("API"))

def buscar_last_valor():
    # === BUSCAR EL ÚLTIMO COLOR GANADOR ===
    global resultado
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    men_error = ""
    while True:
        try:
            timestamp = int(time.time() * 1000)

            response = requests.get(URL_API, headers=HEADERS)
            response.raise_for_status()  # Lan
            json_data = response.json()

        except requests.exceptions.Timeout:
            men_error = "⏱️ Tiempo de espera agotado (timeout)."
        except requests.exceptions.ConnectionError:
            men_error = "🔌 Error de conexión con el servidor."
        except requests.exceptions.HTTPError as err:
            men_error = f"⚠️ Error HTTP: {err.response.status_code}"
        except requests.exceptions.RequestException as e:
            men_error = f"❌ Error inesperado: {e}"
        return men_error

def analizar_jugada_completa(numeros_jugada, numeros_lista, num_gatillos):
    # Parte 1: Calcular Tasa de Acierto General
    precedentes = [numeros_lista[i - 1] for i in range(1, len(numeros_lista)) if numeros_lista[i] in numeros_jugada]
    if not precedentes: return None
    gatillos_set = {num for num, count in Counter(precedentes).most_common(num_gatillos)}

    oportunidades, timings_de_acierto, indices_de_primer_acierto = 0, [], []
    for i in range(len(numeros_lista) - 1):
        if numeros_lista[i] in gatillos_set:
            oportunidades += 1
            if numeros_lista[i + 1] in numeros_jugada:
                timings_de_acierto.append(1)
                indices_de_primer_acierto.append(i + 1)

    tasa_de_acierto = (len(timings_de_acierto) / oportunidades * 100) if oportunidades > 0 else 0
    momento_optimo = Counter(timings_de_acierto).most_common(1)[0][0] if timings_de_acierto else 'N/A'
    densidad_racha = np.mean(
        [sum(1 for k in range(1, 4) if idx + k < len(numeros_lista) and numeros_lista[idx + k] in numeros_jugada)
         for idx in indices_de_primer_acierto]) if indices_de_primer_acierto else 0

    # Parte 2: Lógica para Calcular Temporización Individual
    VENTANA_BUSQUEDA_TEMPORAL = 8
    resultados_temporales = []
    for gatillo in gatillos_set:
        tiempos = []
        for i in range(len(numeros_lista) - VENTANA_BUSQUEDA_TEMPORAL):
            if numeros_lista[i] == gatillo:
                for j in range(1, VENTANA_BUSQUEDA_TEMPORAL + 1):
                    if numeros_lista[i + j] in numeros_jugada:
                        tiempos.append(j)
        if tiempos:
            momento_optimo_individual = Counter(tiempos).most_common(1)[0][0]
            resultados_temporales.append((gatillo, momento_optimo_individual))

    formato_final_temporizado = "N/A"
    if resultados_temporales:
        resultados_ordenados = sorted(resultados_temporales, key=lambda x: (x[1], x[0]))
        formato_final_temporizado = [f"{g}/{t}" for g, t in resultados_ordenados]

    return {
        "gatillos_set": sorted(list(gatillos_set)),  # Lista original para otros motores
        "gatillos_temporizados": formato_final_temporizado,  # Lista nueva para el informe
        "tasa_acierto": tasa_de_acierto,
        "momento_optimo": momento_optimo,
        "densidad_racha": densidad_racha,
        "indices_acierto": indices_de_primer_acierto
    }


def motor_5_analizar_eco_del_eco(resultados_motor1, numeros_lista, JUGADAS_ALGORITMOS, VENTANA_BUSQUEDA_ACIERTO):
    VENTANA_ECO_SECUNDARIO = 8
    NUM_TOP_ECO_SECUNDARIO = 12
    informe_final_motor_5 = {}
    resonancia_cruzada_data = {}
    for nombre_algo_ganador, data_ganador in sorted(resultados_motor1.items()):
        indices_acierto = data_ganador.get('indices_acierto', [])
        if not indices_acierto: continue
        siguiente_giro_hits = Counter()
        for idx in indices_acierto:
            if idx + 1 < len(numeros_lista):
                siguiente_numero = numeros_lista[idx + 1]
                for nombre_algo_objetivo, numeros_algo_objetivo in sorted(JUGADAS_ALGORITMOS.items()):
                    if nombre_algo_objetivo != nombre_algo_ganador and siguiente_numero in numeros_algo_objetivo:
                        siguiente_giro_hits.update([nombre_algo_objetivo])
        if siguiente_giro_hits:
            resonancia_cruzada_data[nombre_algo_ganador] = siguiente_giro_hits.most_common(1)[0][0]
    for nombre_algo_primario, nombre_algo_secundario in sorted(resonancia_cruzada_data.items()):
        ecos_secundarios = []
        if nombre_algo_primario not in resultados_motor1: continue
        gatillos_primarios = resultados_motor1[nombre_algo_primario]['gatillos_set']
        for i in range(len(numeros_lista) - (VENTANA_BUSQUEDA_ACIERTO + 2)):
            if numeros_lista[i] in gatillos_primarios:
                if numeros_lista[i + 1] in JUGADAS_ALGORITMOS[nombre_algo_primario]:
                    if numeros_lista[i + 2] in JUGADAS_ALGORITMOS[nombre_algo_secundario]:
                        inicio_eco = i + 3
                        fin_eco = inicio_eco + VENTANA_ECO_SECUNDARIO
                        ecos_secundarios.extend(numeros_lista[inicio_eco:fin_eco])
        if ecos_secundarios:
            top_ecos = Counter(ecos_secundarios).most_common(NUM_TOP_ECO_SECUNDARIO)
            cadena = f"{nombre_algo_primario} -> {nombre_algo_secundario}"
            informe_final_motor_5[cadena] = top_ecos
    return informe_final_motor_5


def analizar_temporizacion_de_gatillos(nombre_algo, numeros_lista, JUGADAS_ALGORITMOS, resultados_motor1):
    VENTANA_BUSQUEDA_TEMPORAL = 5  # Cuántos giros hacia adelante buscará el acierto

    if nombre_algo not in resultados_motor1:
        return "N/A"

    top_gatillos = resultados_motor1[nombre_algo].get('gatillos', [])
    numeros_jugada = JUGADAS_ALGORITMOS[nombre_algo]

    if not top_gatillos:
        return "N/A"

    resultados_temporales = []
    for gatillo in top_gatillos:
        tiempos_de_acierto = []
        for i in range(len(numeros_lista) - VENTANA_BUSQUEDA_TEMPORAL):
            if numeros_lista[i] == gatillo:
                for j in range(1, VENTANA_BUSQUEDA_TEMPORAL + 1):
                    if numeros_lista[i + j] in numeros_jugada:
                        tiempos_de_acierto.append(j)
                        break  # Contamos solo el primer acierto en la ventana

        if tiempos_de_acierto:
            momento_optimo = Counter(tiempos_de_acierto).most_common(1)[0][0]
            resultados_temporales.append((gatillo, momento_optimo))

    if resultados_temporales:
        # Ordena primero por tiempo (ascendente) y luego por número de gatillo (ascendente)
        resultados_ordenados = sorted(resultados_temporales, key=lambda x: (x[1], x[0]))

        formato_final = [f"{g}/{t}" for g, t in resultados_ordenados]
        return formato_final
    else:
        return "No se pudo determinar la temporización."


def motor_7_generar_recetas(resultados_motor1, numeros_lista, JUGADAS_ALGORITMOS, NUM_TOP_GATILLOS_ZONAS,
                            COMBINACIONES_ZONAS_MESA, NUM_TOP_GATILLOS_RUEDA, ZONAS_RULETA):
    # --- Pre-cálculos para el Motor 7 ---
    zonas_fuertes_mesa = {}
    zonas_fuertes_rueda = {}
    llamadas_resonancia = {}
    ecos_primarios = {}

    # Zonas de la ruleta sin las combinaciones pequeñas

    for nombre_algo, data_principal in resultados_motor1.items():
        # 1) Deja solo zonas válidas y pásalas a set
        zonas_validas = {
            nombre: set(nums)
            for nombre, nums in COMBINACIONES_ZONAS_MESA[0].items()
            if nombre != "estrategia"
        }
        mejor_zona_m_data = max(
            (
                (
                    nombre_zona,
                    analizar_jugada_completa(
                        set(JUGADAS_ALGORITMOS[nombre_algo]) & numeros_zona,  # intersección
                            numeros_lista,
                            NUM_TOP_GATILLOS_ZONAS,
                    ),
                )
                for nombre_zona, numeros_zona in zonas_validas.items()
            ),
            key=lambda x: (
                isinstance(x[1], dict),  # prioriza dicts sobre None/otros
                x[1].get("tasa_acierto", -1) if isinstance(x[1], dict) else -1
            ),
            default=(None, None),
        )

        if mejor_zona_m_data[0]:
            zonas_fuertes_mesa[nombre_algo] = (
                mejor_zona_m_data[0],
                COMBINACIONES_ZONAS_MESA[0][mejor_zona_m_data[0]]
            )

        # Zonas de Rueda
        zonas_validas_rueda = {
            nombre: set(nums)
            for nombre, nums in ZONAS_RULETA[0].items()
            if nombre != "estrategia"
        }

        mejor_zona_r_data = max(
            (
                (
                    nombre_zona,
                    analizar_jugada_completa(
                        set(JUGADAS_ALGORITMOS[nombre_algo]) & numeros_zona,
                            numeros_lista,
                            NUM_TOP_GATILLOS_RUEDA,
                    ),
                )
                for nombre_zona, numeros_zona in zonas_validas_rueda.items()
            ),
            key=lambda x: (
                isinstance([1], dict),
                x[1].get('tasa_acierto', -1) if isinstance(x[1], dict) else -1
            ),
            default=(None, None)
        )

        if mejor_zona_r_data[0]:
            zonas_fuertes_rueda[nombre_algo] = (
            mejor_zona_r_data[0],
            ZONAS_RULETA[0][mejor_zona_r_data[0]])

        # Resonancia
        siguiente_giro_hits = Counter(
            nombre_obj for idx in data_principal.get('indices_acierto', []) if idx + 1 < len(numeros_lista)
            for nombre_obj, numeros_obj in JUGADAS_ALGORITMOS.items()
            if nombre_obj != nombre_algo and numeros_lista[idx + 1] in numeros_obj
        )
        if siguiente_giro_hits: llamadas_resonancia[nombre_algo] = siguiente_giro_hits.most_common(1)[0][0]

        # Ecos Primarios (Top 10) y Ecos Fuertes (Top 3)
        satelites = [num for idx in data_principal.get('indices_acierto', []) for num in
                     numeros_lista[idx + 1:idx + 11]]
        if satelites:
            ecos_primarios[nombre_algo] = {num for num, count in Counter(satelites).most_common(10)}

    # --- Generación de Recetas ---
    recetas = {}
    for nombre_algo, data in sorted(resultados_motor1.items(),
                                    key=lambda item: int(item[0].split(' ')[1].split('_')[0])):
        candidatos = ecos_primarios.get(nombre_algo, set())
        gatillos = data.get('gatillos_set')
        zona_f_m_tupla = zonas_fuertes_mesa.get(nombre_algo)
        zona_f_r_tupla = zonas_fuertes_rueda.get(nombre_algo)
        algo_llamado = llamadas_resonancia.get(nombre_algo)

        if not all([candidatos, gatillos, zona_f_m_tupla, zona_f_r_tupla, algo_llamado]):
            recetas[nombre_algo] = {"jugada_final": "N/A", "componentes": "No se pudo generar una receta completa."}
            continue

        # Para el filtro de resonancia, necesitamos los Top 3 ecos del algoritmo llamado
        ecos_del_llamado_full = ecos_primarios.get(algo_llamado)
        if not ecos_del_llamado_full:
            recetas[nombre_algo] = {"jugada_final": "N/A", "componentes": "No se pudo generar una receta completa."}
            continue

        # Re-calculamos los conteos para obtener el Top 3 específico
        indices_acierto_llamado = resultados_motor1[algo_llamado].get('indices_acierto', [])
        satelites_llamado = [num for idx in indices_acierto_llamado for num in numeros_lista[idx + 1:idx + 11]]
        top_3_ecos_llamado = {num for num, count in Counter(satelites_llamado).most_common(3)}

        # Aplicar filtros
        jugada_final = candidatos
        jugada_final = jugada_final.intersection(zona_f_m_tupla[1])
        jugada_final = jugada_final.intersection(zona_f_r_tupla[1])
        jugada_final = jugada_final.intersection(top_3_ecos_llamado)

        componentes = {
            "gatillos": gatillos,
            "zona_mesa": zona_f_m_tupla[0],
            "zona_rueda": zona_f_r_tupla[0],
            "confirmacion_algoritmo": algo_llamado,
            "confirmacion_numeros": sorted(list(top_3_ecos_llamado))
        }
        recetas[nombre_algo] = {"jugada_final": sorted(list(jugada_final)) if jugada_final else "Ninguna",
                                "componentes": componentes}
    return recetas


def analizar_estabilidad(numeros_jugada, gatillos, numeros_lista, NUM_BLOQUES_ESTABILIDAD, VENTANA_BUSQUEDA_ACIERTO):
    if not gatillos: return None
    bloque_size = len(numeros_lista) // NUM_BLOQUES_ESTABILIDAD
    tasas_por_bloque = []
    for i in range(NUM_BLOQUES_ESTABILIDAD):
        inicio = i * bloque_size
        fin = (i + 1) * bloque_size
        bloque_numeros = numeros_lista[inicio:fin]
        oportunidades, aciertos = 0, 0
        for k in range(len(bloque_numeros) - VENTANA_BUSQUEDA_ACIERTO):
            if bloque_numeros[k] in gatillos:
                oportunidades += 1
                if any(bloque_numeros[k + j] in numeros_jugada for j in range(1, VENTANA_BUSQUEDA_ACIERTO + 1)):
                    aciertos += 1
        tasa_bloque = (aciertos / oportunidades * 100) if oportunidades > 0 else 0
        tasas_por_bloque.append(tasa_bloque)
    desviacion_estandar = np.std(tasas_por_bloque) if tasas_por_bloque else 0
    return {"tasas_periodicas": tasas_por_bloque, "desviacion_estandar": desviacion_estandar}