import os
import json
from datetime import datetime

import flet as ft
import asyncio
from collections import Counter, deque
from urllib.parse import urlparse, parse_qs

import pandas as pd

from Programas_auxiliares import load_db, log_uso, guardar_jugada, set_query_param
import construir_patrones
import requests

ROJOS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
NEGROS = set(range(1, 37)) - ROJOS

PROGRESION = ['1', '1', '+1', '+1', '+2', '+3', '+5', '+8', '+13', '+21', '+34', '+55', '+89', '+144', '+233', '+233']
FICHAS = [1, 1,  2,  3,  5,  8, 13, 21,  34,  55,  89, 144, 233, 377]

MAPA_COLORES_LOGICA = {
    0: 'GGG', 1: 'RIB', 2: 'NPB', 3: 'RIB', 4: 'NPB', 5: 'RIB', 6: 'NPB', 7: 'RIB', 8: 'NPB', 9: 'RIB',
    10: 'NPB', 11: 'NIB', 12: 'RPB', 13: 'NIB', 14: 'RPB', 15: 'NIB', 16: 'RPB', 17: 'NIB', 18: 'RPB',
    19: 'RIA', 20: 'NPA', 21: 'RIA', 22: 'NPA', 23: 'RIA', 24: 'NPA', 25: 'RIA', 26: 'NPA', 27: 'RIA',
    28: 'NPA', 29: 'NIA', 30: 'RPA', 31: 'NIA', 32: 'RPA', 33: 'NIA', 34: 'RPA', 35: 'NIA', 36: 'RPA'
}

TILE_W = 30
TILE_H = 30
GAP = 1

estado_script = "ESPERANDO"
patron_activo = "-"
numeros_prediccion = set()
giros_restantes = 7
historial_numeros = deque(maxlen=20)
historial_colores = deque(maxlen=7)
historial_paridad = deque(maxlen=7)
historial_comb_col_pos = deque(maxlen=7)
historial_combinado = deque(maxlen=7)
historial_powerby = deque(maxlen=7)
reg_play = {}

# Cargando Configurcion
data = load_db("Conf_patrones.json")

# 2. Parámetros Generales
PATRONES_COLORES = [d for d in data if d.get("estrategia") == "Colores"]
PATRONES_PARIDAD = [d for d in data if d.get("estrategia") == "Paridad"]
PATRONES_COMBINADOS = [d for d in data if d.get("estrategia") == "Combinados_2"]
PATRONES_POWER_BY = [d for d in data if d.get("estrategia") == "Power_By"]


def textoformatocontainer(
    titulo: str,
    valor: str,
    valor_name: str = None,
    titulo_size: int = 18,
    titulo_color: str = "blue",
    titulo_weight: ft.FontWeight = ft.FontWeight.BOLD,
    # Estilos del valor
    valor_size: int = 20,
    valor_color: str = "red",
    valor_weight: ft.FontWeight = ft.FontWeight.W_900,
    # Estilos del container
    bgcolor: str = ft.Colors.GREY_200,
    padding: int = 10,
    border_radius: int = 8,
    margin: int = 5,
):
    # Creamos el TextSpan para el valor con un atributo extra 'name'
    text_span_valor = ft.TextSpan(
        str(valor),
        ft.TextStyle(size=valor_size, weight=valor_weight, color=valor_color),
    )
    if valor_name:
        # Guardamos el nombre en el objeto span como atributo custom (puede usarse para identificar)
        text_span_valor.data = valor_name

    return ft.Container(
        content=ft.Text(
            spans=[
                ft.TextSpan(
                    f"{titulo}: ",
                    ft.TextStyle(size=titulo_size, weight=titulo_weight, color=titulo_color),
                ),
                text_span_valor
            ]
        ),
        bgcolor=bgcolor,
        padding=padding,
        border_radius=border_radius,
        margin=margin,
        expand=False
    )


def color_bg(n):
    if n == 0:
        return ft.Colors.GREEN_400
    return ft.Colors.RED_400 if n in ROJOS else ft.Colors.BLUE_GREY_900


def color_fg(n):
    if n == 0:
        return ft.Colors.BLACK
    return ft.Colors.WHITE


OPEN_WRITERS = set()
OPEN_SESSIONS = set()
OPEN_WS = set()
BG_TASKS = set()


def track_task(coro):
    t = asyncio.create_task(coro)
    BG_TASKS.add(t)
    t.add_done_callback(BG_TASKS.discard)
    return t


async def shutdown():
    # 1) cerrar writers
    for w in list(OPEN_WRITERS):
        try:
            w.close()
            await w.wait_closed()
        except Exception:
            pass
        finally:
            OPEN_WRITERS.discard(w)

    # 2) cerrar clientes http / sesiones
    for s in list(OPEN_SESSIONS):
        try:
            await s.close() if hasattr(s, "close") else await s.aclose()
        except Exception:
            pass
        finally:
            OPEN_SESSIONS.discard(s)

    # 3) cerrar websockets
    for ws in list(OPEN_WS):
        try:
            await ws.close()
        except Exception:
            pass
        finally:
            OPEN_WS.discard(ws)

    # 4) cancelar tareas pendientes
    for t in list(BG_TASKS):
        t.cancel()
    await asyncio.gather(*BG_TASKS, return_exceptions=True)


def main(page: ft.Page):
    page.title = "Roulette Pro Clean Version. 2.0"
    page.window.prevent_close = False

    def apply_size():
        W, H = 500, 700
        page.padding = 12
        page.window.maximized = False
        page.window.full_screen = False
        page.window.width = W
        page.window.height = H
        page.window.resizable = True
        # también puedes fijar min/max si quieres forzar tamaño
        page.window.min_width = W
        page.window.max_width = W+300
        page.window.min_height = H
        page.window.max_height = H+100

        page.update()

    apply_size()
    page.on_window_event = lambda e: apply_size() if e.data == "resized" else None

    def generar_analisis(e=None):
        pass

    def crear_mensaje(patrones: list, patron_f: str) -> tuple[str, str]:
        global numeros_prediccion
        """
        Busca un patrón en la lista de diccionarios y devuelve un mensaje formateado.
        """
        for p in patrones:

            if p.get("Patron") == "".join(patron_f):
                color = p.get("color", "—")
                paridad = p.get("paridad", "—")
                decenas = []
                if p.get("decena_1"):
                    decenas.append("D1")
                if p.get("decena_2"):
                    decenas.append("D2")
                if p.get("decena_3"):
                    decenas.append("D3")
                decenas_txt = " y ".join(decenas) if decenas else "ninguna decena"
                cadena = f"Jugar: {color} - {paridad} - {decenas_txt}"
                l_numeros = "-".join(str(n) for n in p.get("numeros", []))
                numeros_prediccion = p["numeros"]
                return cadena, l_numeros
        return "", ""

    def jugar_ultimos_x(ultimas):
        for x in reversed(ultimas):
            agregar_a_secuencia(x)

    def manejar_estado_prediccion(numero):
        global giros_restantes, reg_play
        giros_restantes -= 1

        # Comprobar si hubo acierto
        if numero in numeros_prediccion:
            mensajes_txt.value = f"¡ACIERTO! ({patron_activo}). Reiniciar todo para Volver Analizar..."
            reg_play["tiro_win"] = 10 - giros_restantes
            reg_play["resultado"] = "Win"
            #ultimas = secuencia[:int(ultimas_jugadas_txt.value)]
            if giros_restantes<=3:
                ultimas = secuencia[:7]
            else:
                ultimas = secuencia[:10-giros_restantes]
            guardar_jugada(reg_play)
            limpiar_secuencia()
            jugar_ultimos_x(ultimas)
            return

        # Comprobar si se acabó la ventana
        if giros_restantes <= 0:
            mensajes_txt.value = f"Ventana cerrada para ({patron_activo}). Reiniciar todo para Volver Analizar..."
            mensajes_txt.update()
            reg_play["tiro_win"] = 10
            reg_play["resultado"] = "Loss"
            guardar_jugada(reg_play)
            #ultimas = secuencia[:int(ultimas_jugadas_txt.value)]
            ultimas = secuencia[:7]
            limpiar_secuencia()
            jugar_ultimos_x(ultimas)
            return

        # Actualizar contador si no pasa nada
        mensajes_txt.value = f"** {abs(10-giros_restantes)} Giro **, de 10 restantes para lograr el acierto."
        mensajes_txt.update()

        if progresion_txt.value == "-":
            progresion_txt.value = str(PROGRESION[10 - giros_restantes])
        else:
            progresion_txt.value += ", " + str(PROGRESION[10 - giros_restantes])
        importe = int(FICHAS[10 - giros_restantes]) * float(ficha_valor.value)
        progresion_label.value = f"Progresion de Fichas ({str(FICHAS[10 - giros_restantes])}) [${importe}]:"
        page.update()

    def manejar_estado_analizando():
        global estado_script, giros_restantes, historial_powerby

        if PATRONES_POWER_BY and PATRONES_POWER_BY[0].get("Patrones"):
            buscar_patron, l_num = crear_mensaje(PATRONES_POWER_BY[0]['Patrones'], historial_powerby)
            if buscar_patron != '':
                jugada_activa_txt.value = buscar_patron
                patron_activo_txt.value = "PATRONES POWER BY"
                estado_script = "ACTIVA"
                giros_restantes = 10
                numeros_activos_txt.value = l_num
                mensajes_txt.value = f"Giro: 1 de {giros_restantes} tiros, para tener el acierto.."
                page.update()
                return

        if PATRONES_COMBINADOS and PATRONES_COMBINADOS[0].get("Patrones"):
            buscar_patron, l_num = crear_mensaje(PATRONES_COMBINADOS[0]['Patrones'], historial_comb_col_pos)
            if buscar_patron != '':
                jugada_activa_txt.value = buscar_patron
                patron_activo_txt.value = "PATRONES COMBINADOS COLOR/POSICION"
                estado_script = "ACTIVA"
                giros_restantes = 10
                numeros_activos_txt.value = l_num
                mensajes_txt.value = f"Giro: 1 de {giros_restantes} tiros, para tener el acierto.."
                page.update()
                return

        if PATRONES_COMBINADOS and PATRONES_COMBINADOS[0].get("Patrones"):
            buscar_patron, l_num = crear_mensaje(PATRONES_COMBINADOS[0]['Patrones'], historial_combinado)
            if buscar_patron != '':
                jugada_activa_txt.value = buscar_patron
                patron_activo_txt.value = "PATRONES COMBINADOS COLOR/PARIDAD"
                estado_script = "ACTIVA"
                giros_restantes = 10
                numeros_activos_txt.value = l_num
                mensajes_txt.value = f"Giro: 1 de {giros_restantes} tiros, para tener el acierto.."
                page.update()
                return

        if PATRONES_COLORES and PATRONES_COLORES[0].get("Patrones"):
            buscar_patron, l_num = crear_mensaje(PATRONES_COLORES[0]['Patrones'], historial_colores)
            if buscar_patron != '':
                jugada_activa_txt.value = buscar_patron
                patron_activo_txt.value = "PATRONES COLORES"
                estado_script = "ACTIVA"
                giros_restantes = 10
                mensajes_txt.value = f"Giro: 1 de {giros_restantes} tiros, para tener el acierto.."
                numeros_activos_txt.value = l_num
                page.update()
                return

        if PATRONES_PARIDAD and PATRONES_PARIDAD[0].get("Patrones"):
            buscar_patron, l_num = crear_mensaje(PATRONES_PARIDAD[0]['Patrones'], historial_paridad)
            if buscar_patron != '':
                jugada_activa_txt.value = buscar_patron
                patron_activo_txt.value = "PATRONES PARIDAD"
                estado_script = "ACTIVA"
                giros_restantes = 10
                mensajes_txt.value = f"Giro: 1 de {giros_restantes} tiros, para tener el acierto.."
                numeros_activos_txt.value = l_num
                page.update()
                return

        # si no encontró nada
        jugada_activa_txt.value = ""
        patron_activo_txt.value = ""
        estado_script = "ANALIZANDO"
        giros_restantes = 0
        mensajes_txt.value = f"Continuamos Analizando Ultimos Patrones."
        numeros_activos_txt.value = ""
        page.update()
        return


    def procesar_numero(numero):
        global historial_numeros, historial_colores, historial_paridad, historial_comb_col_pos, historial_combinado, \
            historial_powerby, giros_restantes, estado_script, reg_play

        # 1. Actualizar historiales
        historial_numeros.append(numero)
        historial_colores.append(MAPA_COLORES_LOGICA.get(numero, 'G')[:1])
        historial_paridad.append(MAPA_COLORES_LOGICA.get(numero, 'G')[1:][:1])
        historial_comb_col_pos.append(MAPA_COLORES_LOGICA.get(numero, 'G')[:1] +
                                   MAPA_COLORES_LOGICA.get(numero, 'G')[2:])
        historial_combinado.append(MAPA_COLORES_LOGICA.get(numero, 'G')[1:][:1] +
                                   MAPA_COLORES_LOGICA.get(numero, 'G')[:1])
        historial_powerby.append(MAPA_COLORES_LOGICA.get(numero, 'G')[1:][:1] + MAPA_COLORES_LOGICA.get(numero, 'G')[:1]
                                 + MAPA_COLORES_LOGICA.get(numero, 'G')[2:])

        # 2. Máquina de Estados Lógicos
        if estado_script == 'ESPERANDO':
            giros_restantes -= 1

            if giros_restantes == 0:
                mensajes_txt.value = "ANALIZANDO ULTIMO PATRON..."
                estado_script = 'ANALIZANDO'
            else:
                mensajes_txt.value = f"Esperando las proximas {giros_restantes} jugadas"
                page.update()
                return

        # 2. Máquina de Estados Lógicos
        if estado_script == 'ACTIVA':
            manejar_estado_prediccion(numero)

        else:  # Si no estábamos en predicción, entonces analizamos.
            manejar_estado_analizando()
            sec_activa = ""
            if patron_activo_txt.value == "PATRONES COLORES":
                sec_activa = historial_colores
            elif patron_activo_txt.value == "PATRONES PARIDAD":
                sec_activa = historial_paridad
            elif patron_activo_txt.value == "PATRONES COMBINADOS COLOR/PARIDAD":
                sec_activa = historial_combinado
            elif patron_activo_txt.value == "PATRONES COMBINADOS COLOR/POSICION":
                sec_activa = historial_comb_col_pos
            elif patron_activo_txt.value == "PATRONES POWER BY":
                sec_activa = historial_powerby

            if sec_activa != "":
                reg_play = {'numero': numero,
                            'secuencia_activa': "".join(sec_activa),
                            'patron': patron_activo_txt.value,
                            'tiro_win': 0,
                            'jugada': jugada_activa_txt.value,
                            'resultado': None
                            }
                if progresion_txt.value == "-":
                    progresion_txt.value = str(PROGRESION[10 - giros_restantes])
                    # Abrir el archivo JSON
                    with open("historial_secuencias_jugadas.json", "r", encoding="latin-1") as f:
                        data = json.load(f)  # Esto es una lista de diccionarios

                    buscar = "".join(sec_activa)
                    apariciones_txt.value = sum(1 for d in data if d.get("secuencia_activa") == buscar)

                    tiros_ganadores = [str(d["tiro_win"]) for d in data if d.get("secuencia_activa") == buscar]
                    conteo = Counter(tiros_ganadores)
                    apariciones_ordenadas = sorted(conteo.items(), key=lambda x: int(x[0]))

                    tiros_ganadores_txt.value = " - ".join([f"'{k}' ({v})" for k, v in apariciones_ordenadas])
                else:
                    progresion_txt.value += ", " + str(PROGRESION[10 - giros_restantes])

                importe = f" [$ {int(FICHAS[10 - giros_restantes]) * ficha_valor.value}]"
                progresion_label.value = f"Progresion de Fichas ({str(FICHAS[10 - giros_restantes])}) - {importe}:"
                page.update()

    def limpiar_secuencia(e=None):
        global estado_script, patron_activo, numeros_prediccion, giros_restantes, historial_numeros, \
            historial_colores, historial_combinado, historial_powerby

        seq_row.controls.clear()
        secuencia.clear()
        qty_text.value = "Secuencia (0):"

        estado_script = "ESPERANDO"
        patron_activo = "-"
        numeros_prediccion = set()
        historial_numeros = deque(maxlen=20)
        historial_colores = deque(maxlen=7)
        historial_combinado = deque(maxlen=7)  # Los patrones combinados tienen 14 caracteres (7 pares de 2)
        historial_powerby = deque(maxlen=7)  # Los patrones combinados tienen 21 caracteres (7 pares de 3)

        jugada_activa_txt.value = ""
        patron_activo_txt.value = ""
        estado_script = "ESPERANDO"
        giros_restantes = 7
        mensajes_txt.value = f"Esperando las proximas {giros_restantes} jugadas."
        numeros_activos_txt.value = ""
        progresion_txt.value = "-"
        progresion_label.value = f"Progresion de Fichas (0) [$0.00]:"
        tiros_ganadores_txt.value = "-"
        apariciones_txt.value = "-"
        page.update()

    def on_ruleta_change(e=None):
        sel = ruleta_dd.value
        info = meta.get(sel, {})
        # si tienes mensajes_txt:
        mensajes_txt.value = f"Ruleta: {sel}  ·  max_numeros={info.get('max_numeros', '-')}"
        mensajes_txt.update()

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
            "startedAt": started_at[:10]+ " " + started_at[11:][:8],
            "numero": outcome
        }

    def jugadas_automaticas(e=None):
        import time

        sel = ruleta_dd.value
        info = meta.get(sel)
        if not sel or not meta:
            mensajes_txt.value = "Seleccione una ruleta válida."
        else:
            if boton_API.text == "Conectar API":
                boton_API.text = "Desconectar API"
                boton_API.bgcolor = ft.Colors.RED_200
                mensajes_txt.value = f"Se activa de Juego automatico con Ruleta => {sel} <="
            else:
                boton_API.text = "Conectar API"
                espera_txt.value = ""
                espera_txt.update()
                boton_API.bgcolor = ft.Colors.GREEN_200
                mensajes_txt.value = f"Se concluye el Juego automatico."
        page.update()

        url_end = info.get("API")
        ultimo_id = None
        segundos = 0
        while boton_API.text == "Desconectar API":
            segundos += 1
            try:
                resp = requests.get(url_end, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()

                    jugada_id = data.get("id")
                    numero = data["data"]["result"]["outcome"]["number"]

                    # Detectar si hay un nuevo id (jugada nueva)
                    if jugada_id != ultimo_id:
                        ultimo_id = jugada_id
                        mensajes_txt.value = f"Nuevo número registrado: {numero} (ID: {jugada_id})"
                        agregar_a_secuencia(numero)
                        segundos = 0
                        page.update()

            except Exception as e:
                mensajes_txt.value = f"Error Lectura API: {e}."

            time.sleep(1)  # espera 1 segundo
            espera_txt.value = f"Espera {segundos} seg."
            espera_txt.update()
        espera_txt.value = ""
        espera_txt.update()

    def reed_url(TARGET, URL_1, URL_2):
        import time
        import math

        file_path = "ultimos_numeros.xlsx"
        if os.path.exists(file_path):
            # Leer el archivo existente
            df_old = pd.read_excel(file_path, engine="openpyxl")
            if df_old.empty:
                tabla_vacia = True
                ultima_fecha = '2000-01-01 01:01:00'
            else:
                tabla_vacia = False
                df_old[1] = pd.to_datetime(df_old[1])
                # Obtener la última fecha registrada
                ultima_fecha = df_old[1].max()
        else:
            tabla_vacia = True
            ultima_fecha = '2000-01-01 01:01:00'

        HEADERS = {
            "User-Agent": "Mozilla/5.0",
        }
        url_end = URL_1 + "0" + URL_2
        qs = parse_qs(urlparse(url_end).query)
        page0 = 0
        size = int(qs.get("size", [50])[0])
        need_pages = math.ceil(TARGET / size)

        all_rows = []
        i = 0
        fecha_menor = False
        for i in range(need_pages):
            page_num = page0 + i
            url_end = URL_1 + str(i) + URL_2
            url = set_query_param(url_end, page=page_num, size=size)
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            payload = r.json()
            items = extract_items(payload)
            if not items:
                mensajes_txt.value = f"Sin datos en página"
                mensajes_txt.update()
                return

            for it in items:
                norm = normalize(it)

                norm_fecha = pd.to_datetime(norm['startedAt'])
                # Si ultima_fecha viene del DataFrame
                ultima_fecha = pd.to_datetime(ultima_fecha)

                if norm_fecha > ultima_fecha:
                    id_play = it['id']
                    if norm['numero'] == 0:
                        color = "V"
                        decena = "0"
                        columna = "0"
                        fila = "0"
                        paridad = "0"
                        posicion = "0"
                    else:
                        color = "R" if norm['numero'] in ROJOS else "N"

                        if norm['numero'] <= 13:
                            decena = "D1"
                        else:
                            if norm['numero'] >= 24:
                                decena = "D3"
                            else:
                                decena = "D2"

                        paridad = "P" if norm['numero'] % 2 == 0 else "I"
                        posicion = "A" if norm['numero'] > 18 else "B"

                        r = norm['numero'] % 3
                        columna = "C34" if r == 1 else ("C35" if r == 2 else "C36")

                        idx = (norm['numero'] + 2) // 3  # ceil(n/3) sin floats
                        fila = f"F{idx}"

                    valores = [norm['numero'], norm['startedAt'], id_play, color, decena, columna, fila, paridad, posicion]

                    all_rows.append(valores)
                    mensajes_txt.value = f"Recolectando Jugadas -> acumuladas: {len(all_rows)}"
                    mensajes_txt.update()
                    if len(all_rows) >= TARGET:
                        break
                else:
                    fecha_menor = True
                    break
            time.sleep(0.2)
            if fecha_menor:
                break
        time.sleep(0.1)

        # Ordenar ascendente por fecha/hora
        all_rows.sort(key=lambda x: x[2], reverse=True)
        # ---- Ordenar por fecha (y por 'orden' como desempate) ----
        all_rows = sorted(all_rows, key=lambda r: datetime.fromisoformat(r[1].replace("Z", "+00:00")))
        rows_nuevas = all_rows
        #
        # Guardar en CSV
        if len(all_rows)>0:
            df_new = pd.DataFrame(all_rows)
            # Filtrar solo los registros con fecha mayor
            df_new[1] = pd.to_datetime(df_new[1])

            df_to_add = df_new[df_new[1] > ultima_fecha]

            if not df_to_add.empty:
                if tabla_vacia:
                    # Crear archivo nuevo
                    df_new.to_excel(file_path, index=False, engine="openpyxl")
                    all_rows = df_new.to_dict(orient="records")
                    mensajes_txt.value = f"✅El archivo historico creado satifactoriamente."
                    mensajes_txt.update()
                else:
                    # Concatenar y guardar
                    df_final = pd.concat([df_old, df_to_add], ignore_index=True)
                    df_final.to_excel(file_path, index=False, engine="openpyxl")
                    all_rows = df_final.to_dict(orient="records")
                    mensajes_txt.value = f"✅Se actualizo el archivo historico satifactoriamente."
                    mensajes_txt.update()

            mensajes_txt.value= f"✅Generando nuevos patrones."
            mensajes_txt.update()

            res_color = construir_patrones.analizar_patrones_color_rows(all_rows)

            # tu módulo anterior
            data_json = construir_patrones.construir_json_estrategia_colores(res_color)
            with open("estrategia_colores.json", "w", encoding="utf-8") as f:
                 json.dump(data_json, f, indent=2, ensure_ascii=False)

            for it in range(len(rows_nuevas)):
                agregar_a_secuencia(rows_nuevas[it][0])

    def recopilar_jugadas(e=None):
        sel = ruleta_dd.value
        info = meta.get(sel)
        if not sel or not meta:
            mensajes_txt.value = "Seleccione una ruleta válida."
        else:
            mensajes_txt.value = f"Conexion a la ruleta para recolectar ultimas jugadas"

            reed_url(info.get('max_numeros'), info.get("API_1"), info.get("API_2"))

    # --- Bloque de Ruleta y Conexion con la API
    ruleta_dd = ft.Dropdown(
        label="Ruletas",
        value=None,
        options=[],
        width=150,
        on_change=on_ruleta_change,
    )
    data = load_db("ruletas.json")
    nombres = []
    meta = {}
    for d in data:
        if isinstance(d, dict) and "ruleta" in d:
            nombre = d["ruleta"]
            if nombre not in nombres:
                nombres.append(nombre)
            meta[nombre] = {
                "max_numeros": d.get("max_numeros"),
                "API_1": d.get("API_1"),
                "API_2": d.get("API_2"),
                "API": d.get("API")
            }

    def chk_changed(e: ft.ControlEvent):
        if e.control.value:  # checkbox activado
            txt.disabled = False
            # restaurar último valor válido si existe
            txt.value = prev_value.get("val", "1") if prev_value.get("val", "") not in ("", "-") else "1"
        else:  # checkbox desactivado
            # intentar guardar el valor actual si es un entero válido
            try:
                if txt.value and txt.value != "-":
                    int(txt.value)
                    prev_value["val"] = txt.value
            except Exception:
                # si no es válido, mantener prev_value tal cual
                pass
            txt.value = "-"
            txt.disabled = True
        page.update()

    def eliminar_ultimo(e=None):
        pass

    ruleta_dd.options = [ft.dropdown.Option(n) for n in nombres]

    if nombres:
        ruleta_dd.value = nombres[0]

    boton_API = (
        ft.ElevatedButton(
            text="Conectar API",
            on_click=jugadas_automaticas,
            bgcolor=ft.Colors.GREEN_200
        )
    )
    espera_txt = (
        ft.Text(
            value="",
            size=16,
            weight=ft.FontWeight.BOLD,
            bgcolor=ft.Colors.YELLOW_100
        )
    )
    ruleta_block = (
        ft.Container(
            content=ft.Row(
                [
                    ruleta_dd,
                    boton_API,
                    espera_txt,
                ],
                spacing=4,
                alignment=ft.MainAxisAlignment.START
            ),
            expand=False,
            padding=4,
            width=450,
            bgcolor=ft.Colors.GREY_50,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=10
        )
    )

    # --- Bloque botones: Recopilar + Generar + Limpiar ---
    top_controls_block = (
        ft.Container(
            content=ft.Row(
                [
                    ft.ElevatedButton("Recopilar", on_click=recopilar_jugadas),
                    ft.ElevatedButton("Generar", on_click=generar_analisis, disabled=True),
                    ft.OutlinedButton("Limpiar", on_click=limpiar_secuencia),
                    ft.OutlinedButton("Elimar Ultimo", on_click=eliminar_ultimo)
                ],
                spacing=4,
                expand=False,
                alignment=ft.MainAxisAlignment.START,
            ),
        padding=4,
        expand=False,
        width=450,
        bgcolor=ft.Colors.GREY_50,
        border=ft.border.all(1, ft.Colors.GREY_300),
        border_radius=10
        )
    )

    # --- Bloque de Mensajes (línea actualizable) ---
    mensajes_txt = ft.Text("Esperando las proximas 7 jugadas",
                           size=12
                           )  # inicia en blanco
    mensajes_block = (
        ft.Container(
            content=ft.Row([ft.Text("Mensajes:",
                                    weight=ft.FontWeight.BOLD),
                                    mensajes_txt], spacing=8),
            padding=4,
            expand=False,
            width=450,
            bgcolor=ft.Colors.GREY_50,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=10,
        )
    )

    # Secuencia inferior (chips)
    seq_row = ft.Row(
        spacing=4,
        expand=False,
        wrap=False,
        scroll=ft.ScrollMode.ALWAYS,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    seq_box = ft.Container(
        content=seq_row,
        padding=4,
        expand=False,
        bgcolor=ft.Colors.GREY_50,
        border=ft.border.all(1, ft.Colors.GREY_300),
        border_radius=10,
    )

    qty_text = ft.Text(
        "Secuencia (0):",
        weight=ft.FontWeight.BOLD
    )

    secuencia = []

    # --- Patron Activo ---
    patron_activo_txt = ft.Text("-", size=14, weight=ft.FontWeight.BOLD)
    patron_activo_block = (
        ft.Container(
            content=ft.Row(
                [ft.Text("Patron Activo:",
                         weight=ft.FontWeight.BOLD
                         ),
                patron_activo_txt],
                spacing=4,
                expand=False,
            ),
            expand=False,
            padding=4,
            width=450,
            bgcolor=ft.Colors.GREY_50,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=10,
        )
    )

    # --- Jugada Activa ---
    jugada_activa_txt = ft.Text("-",
                                size=14,
                                weight=ft.FontWeight.BOLD
                                )
    jugada_activa_block = (
        ft.Container(
            content=ft.Column(
                [
                    ft.Row([ft.Text("Jugada Activa:", weight=ft.FontWeight.BOLD), jugada_activa_txt], spacing=4),
                ],
                spacing=4,
                expand=False
            ),
            padding=4,
            expand=False,
            width=450,
            bgcolor=ft.Colors.GREY_50,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=10
        )
    )

    # --- Numeros Activos ---
    numeros_activos_txt = ft.Text("-",
                                  size=14,
                                  weight=ft.FontWeight.BOLD
                                  )
    numeros_activos_block = (
        ft.Container(
            content=ft.Column(
                        [
                    ft.Row([ft.Text("Numeros Activos:", weight=ft.FontWeight.BOLD), numeros_activos_txt], spacing=4),
                ],
                spacing=4,
                expand=False
            ),
            padding=4,
            expand=False,
            width=450,
            bgcolor=ft.Colors.GREY_50,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=10
        )
    )

    # --- Historico de Apariciones ---
    apariciones_txt = ft.Text("-",
                              size=14,
                              weight=ft.FontWeight.BOLD
                              )

    apariciones_block = (
        ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [ft.Text(
                                "Cantidad de Apariciones en el Historico:",
                                weight=ft.FontWeight.BOLD
                                ),
                        apariciones_txt],
                        spacing=8
                    ),
                ],
                spacing=4,
                expand=False
            ),
            padding=4,
            expand=False,
            width=450,
            bgcolor=ft.Colors.GREY_50,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=10
        )
    )

    # --- Tiros ganadores ---
    tiros_ganadores_txt = (
        ft.TextField(
            value="-",
            text_size=14,
            text_style=ft.TextStyle(
                weight=ft.FontWeight.BOLD
            ),
            read_only=True,
            multiline=True,
            min_lines=1,      # mínimo de líneas visibles
            max_lines=8,      # máximo antes de que aparezca scroll
            expand=True,
            border=ft.InputBorder.NONE
        )
    )

    tiros_ganadores_block = (
        ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [ft.Text("Tiros Ganadores del Patron:",
                                    weight=ft.FontWeight.BOLD,
                                    no_wrap=False
                                    ),
                                tiros_ganadores_txt],
                        spacing=8
                    ),
                ],
                spacing=4,
                expand=False
            ),
            padding=4,
            width=450,
            bgcolor=ft.Colors.GREY_50,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=10
        )
    )

    # --- Progresion ---
    progresion_label = ft.Text(
        "Progresion de Fichas (0)  [$0.00]:",
        weight=ft.FontWeight.BOLD
    )
    progresion_txt = ft.Text(
        "-",
        size=14,
        weight=ft.FontWeight.BOLD
    )

    progresion_block = ft.Container(
        content= ft.Column(
            [
                progresion_label,
                progresion_txt
            ],
            spacing=4,
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.START,  # alinea ambos a la izquierda
            tight=True
        ),
        padding=4,
        expand=False,
        width=450,
        bgcolor=ft.Colors.GREY_50,
        border=ft.border.all(1, ft.Colors.GREY_300),
        border_radius=10
        )

    # --- Recuperar x ultimas jugadas ---
    prev_value = {"val": "1"}

    chk = ft.Checkbox(
                label="Establecer Recuperar Primeras Jugadas Fijas:",
                value=False
            )
    txt = ft.TextField(
        value="-",
        width=40,
        height=30,
        disabled=True,
        bgcolor=ft.Colors.GREY_50,
        content_padding=ft.Padding(4, 4, 4, 4),  # recomendable usar ft.Padding
        text_align=ft.TextAlign.CENTER,
        border=ft.border.all(1, ft.Colors.GREY_300),
        keyboard_type=ft.KeyboardType.NUMBER
    )

    chk.on_change = chk_changed

    recuperar_jugadas_block = (
        ft.Container(
            content=ft.Row(
                [chk, txt],
                        alignment=ft.MainAxisAlignment.START,
                        spacing=4
            ),
            expand=False,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=10
        )
    )

    # --- Valor de las fichas que estamos jugando ---

    ficha_label = ft.Text("Establecer Valor de la Ficha a jugar:")
    ficha_valor = (
        ft.TextField(
            value="0.01",
            width=60,
            height=30,
            disabled=False,
            bgcolor=ft.Colors.GREY_50,
            content_padding=ft.Padding(4, 4, 4, 4),
            text_align=ft.TextAlign.CENTER,
            border=ft.border.all(1, ft.Colors.GREY_300),
            keyboard_type=ft.KeyboardType.NUMBER
        )
    )

    valor_fichas_jugadas_block = (
        ft.Container(
            content=ft.Row(
                        [ficha_label, ficha_valor],
                        alignment=ft.MainAxisAlignment.START,
                        spacing=4
                    ),
            expand=False,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=10
        )
    )

    # Agregar Numeros a la secuencia
    def agregar_a_secuencia(n: int):
        chip = ft.Container(
            width=25, height=25,
            bgcolor=color_bg(n),
            border_radius=999,
            alignment=ft.alignment.center,
            border=ft.border.all(1, ft.Colors.BLACK12),
            content=ft.Text(
                        str(n),
                        color=color_fg(n),
                        size=11,
                        weight=ft.FontWeight.BOLD
            ),
            tooltip=f"Número {n}",
            expand=False
        )
        seq_row.controls.insert(0, chip)  # añade el chip al inicio
        secuencia.insert(0, n)  # añade el número al inicio
        qty_text.value = f"Secuencia ({len(secuencia)}):"
        page.update()

        procesar_numero(n)
        page.update()

    def tile_num(n: int) -> ft.Container:
        return ft.Container(
            width=TILE_W, height=TILE_H,
            bgcolor=color_bg(n),
            border=ft.border.all(1, ft.Colors.BLACK),
            border_radius=6,
            alignment=ft.alignment.center,
            content=ft.Text(str(n), color=color_fg(n), weight=ft.FontWeight.BOLD),
            on_click=lambda e, v=n: agregar_a_secuencia(v),
            tooltip=f"Clic: {n}",
            expand=False
        )

    # --- Columna 0 (alto = 3 filas) ---
    cero_columna = ft.Container(
        width=TILE_W,
        height=TILE_H * 3 + GAP * 2,
        bgcolor=color_bg(0),
        border=ft.border.all(1, ft.Colors.BLACK),
        border_radius=6,
        alignment=ft.alignment.center,
        content=ft.Text("0", color=color_fg(0), weight=ft.FontWeight.BOLD),
        on_click=lambda e: agregar_a_secuencia(0),
        tooltip="Clic: 0",
        expand=False
    )

    columnas_numeros = []
    for c in range(12):  # 12 columnas
        b = c * 3  # base: 0,3,6,...,33
        col = ft.Column(
            controls=[tile_num(b + 3), tile_num(b + 2), tile_num(b + 1)],
            spacing=GAP,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=False
        )
        columnas_numeros.append(col)

    tablero_scroll = ft.Row(
        controls=[cero_columna] + [ft.Container(content=col, padding=0) for col in columnas_numeros],
        spacing=GAP,
        expand=False,
        wrap=False,
        scroll=ft.ScrollMode.ALWAYS,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    page.add(
        ft.Column(
            [
                ruleta_block,
                top_controls_block,
                mensajes_block,
                ft.Container(
                    content=tablero_scroll,
                    expand=False,
                    padding=8,
                    bgcolor=ft.Colors.GREY_100,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=10,
                    height=TILE_H * 3 + GAP * 2 + 16  # altura para encajar bien las 3 filas + padding
                ),
                ft.Divider(),
                ft.Row(
                    [
                        qty_text,
                    ],
                ),
                seq_box,
                patron_activo_block,
                jugada_activa_block,
                numeros_activos_block,
                apariciones_block,
                tiros_ganadores_block,
                valor_fichas_jugadas_block,
                progresion_block,
                recuperar_jugadas_block
            ],
            spacing=4,
            expand=False
        )
    )


log_uso("historial_uso.json")

ft.app(target=main)
