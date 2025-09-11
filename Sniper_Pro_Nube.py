import os, platform, socket, getpass, json
from datetime import datetime, timezone
from typing import Tuple
import flet as ft
import numpy as np
import csv
from collections import Counter, deque
from Programas_auxiliares import load_db, log_uso, leer_historial
from datetime import datetime, timezone
import socket, platform, getpass, requests


def main(page: ft.Page):
    # Obtener fecha y hora
    fecha_hora = datetime.now(timezone.utc)

    # Detectar dispositivo
    osname = platform.system()
    hostname = socket.gethostname()
    user = getpass.getuser()
    dispositivo = f"{osname} - {hostname} (user {user})"

    # Detectar IP pública
    ip_publica = None
    try:
        ip_publica = requests.get("https://api.ipify.org", timeout=5).text
    except:
        ip_publica = "N/A"

    # Log en consola de Render
    print(f"📌 Conexión recibida: {fecha_hora} | {dispositivo} | IP: {ip_publica}")

    # ... aquí sigue el resto de tu código de interfaz


ROJOS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
NEGROS = set(range(1,37)) - ROJOS

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
historial_combinado = deque(maxlen=7) # Los patrones combinados tienen 14 caracteres (7 pares de 2)
historial_powerby = deque(maxlen=7) # Los patrones combinados tienen 21 caracteres (7 pares de 3)

# Cargando Configurcion
data = load_db("Conf_patrones.json")

# 2. Parámetros Generales
PATRONES_COLORES = [d for d in data if d.get("estrategia") == "Colores"]
PATRONES_PARIDAD = [d for d in data if d.get("estrategia") == "Paridad"]
PATRONES_COMBINADOS = [d for d in data if d.get("estrategia") == "Combinados_2"]
PATRONES_POWER_BY = [d for d in data if d.get("estrategia") == "Power_By"]


def color_bg(n):
    if n == 0:
        return ft.Colors.GREEN_400
    return ft.Colors.RED_400 if n in ROJOS else ft.Colors.BLUE_GREY_900


def color_fg(n):
    if n == 0:
        return ft.Colors.BLACK
    return ft.Colors.WHITE


def main(page: ft.Page):
    # Registrar uso cada vez que alguien abre la app
    log_uso()

    page.title = "Roulette Pro Clean Version. 2.0"
    page.padding = 12
    page.window_width = 470
    page.window_height = 640
    page.window_min_width = page.window_width
    page.window_min_height = page.window_height
    page.window_max_width = page.window_width
    page.window_max_height = page.window_height

    page.theme_mode = "light"

    def generar_analisis():
        pass

    def crear_mensaje(patrones: list, patron: str) -> tuple[str, str]:
        global numeros_prediccion
        """
        Busca un patrón en la lista de diccionarios y devuelve un mensaje formateado.
        """
        for p in patrones:
            if p.get("patron") == "".join(patron):
                color = p.get("color", "—")
                paridad = p.get("paridad", "—")
                decenas = []
                if p.get("decena_1"): decenas.append("D1")
                if p.get("decena_2"): decenas.append("D2")
                if p.get("decena_3"): decenas.append("D3")
                decenas_txt = " y ".join(decenas) if decenas else "ninguna decena"
                cadena = f"Jugar: {color} - {paridad} - {decenas_txt}"
                l_numeros = "-".join(str(n) for n in p.get("numeros", []))
                numeros_prediccion = p["numeros"]
                return cadena, l_numeros
        return "", ""

    def manejar_estado_prediccion(numero):
        global giros_restantes
        giros_restantes -= 1

        # Comprobar si hubo acierto
        if numero in numeros_prediccion:
            mensajes_txt.value = f"¡ACIERTO! ({patron_activo}). Reiniciar todo para Volver Analizar..."
            aciertos_txt.value = "¡ACIERTO!"
            page.update()
            limpiar_secuencia()
            return

        # Comprobar si se acabó la ventana
        if giros_restantes <= 0:
            mensajes_txt.value = f"Ventana cerrada para ({patron_activo}). Reiniciar todo para Volver Analizar..."
            aciertos_txt.value = "CERRADA"
            page.update()
            limpiar_secuencia()
            return

    # Actualizar contador si no pasa nada
    mensajes_txt.value = f"Ventana de acierto: {giros_restantes} giros restantes."
    aciertos_txt.value = f"{giros_restantes} giros"
    page.update()


        # Actualizar contador si no pasa nada
        mensajes_txt.value = f"Ventana de acierto: {giros_restantes} giros restantes."

    def manejar_estado_analizando():
        global estado_script, giros_restantes, historial_powerby

        # --- Power By ---
        buscar_patron, l_num = crear_mensaje(PATRONES_POWER_BY[0]['patrones'], historial_powerby)
        if buscar_patron != '':
            jugada_activa_txt.value = buscar_patron
            patron_activo_txt.value = "PATRONES POWER BY"
            estado_script = "ACTIVA"
            giros_restantes = 10
            aciertos_txt.value = f"{giros_restantes} giros"
            numeros_activos_txt.value = l_num
            mensajes_txt.value = f"Faltan {giros_restantes} tiros, para tener el acierto.."
            page.update()
            return

        # --- Combinados ---
        buscar_patron, l_num = crear_mensaje(PATRONES_COMBINADOS[0]['patrones'], historial_powerby)
        if buscar_patron != '':
            jugada_activa_txt.value = buscar_patron
            patron_activo_txt.value = "PATRONES COMBINADOS"
            estado_script = "ACTIVA"
            giros_restantes = 10
            aciertos_txt.value = f"{giros_restantes} giros"
            numeros_activos_txt.value = l_num
            mensajes_txt.value = f"Faltan {giros_restantes} tiros, para tener el acierto.."
            page.update()
            return

        # --- Colores ---
        buscar_patron, l_num = crear_mensaje(PATRONES_COLORES[0]['patrones'], historial_colores)
        if buscar_patron != '':
            jugada_activa_txt.value = buscar_patron
            patron_activo_txt.value = "PATRONES COLORES"
            estado_script = "ACTIVA"
            giros_restantes = 10
            aciertos_txt.value = f"{giros_restantes} giros"
            numeros_activos_txt.value = l_num
            mensajes_txt.value = f"Faltan {giros_restantes} tiros, para tener el acierto.."
            page.update()
            return

        # --- Paridad ---
        buscar_patron, l_num = crear_mensaje(PATRONES_PARIDAD[0]['patrones'], historial_paridad)
        if buscar_patron != '':
            jugada_activa_txt.value = buscar_patron
            patron_activo_txt.value = "PATRONES PARIDAD"
            estado_script = "ACTIVA"
            giros_restantes = 10
            aciertos_txt.value = f"{giros_restantes} giros"
            numeros_activos_txt.value = l_num
            mensajes_txt.value = f"Faltan {giros_restantes} tiros, para tener el acierto.."
            page.update()
            return

        # --- Si no se activó ningún patrón ---
        jugada_activa_txt.value = ""
        patron_activo_txt.value = ""
        estado_script = "ANALIZANDO"
        giros_restantes = 0
        aciertos_txt.value = "—"
        mensajes_txt.value = f"Continuamos Analizando Ultimos Patrones."
        numeros_activos_txt.value = ""
        page.update()
        return

    def procesar_numero(numero):
        global historial_numeros, historial_colores, historial_paridad, historial_combinado, historial_powerby, \
            giros_restantes, estado_script

        # 1. Actualizar historiales
        historial_numeros.append(numero)
        historial_colores.append(MAPA_COLORES_LOGICA.get(numero,'G')[:1])
        historial_paridad.append(MAPA_COLORES_LOGICA.get(numero, 'G')[1:][:1])
        historial_combinado.append(MAPA_COLORES_LOGICA.get(numero, 'G')[1:][:1] + MAPA_COLORES_LOGICA.get(numero, 'G')[:1])
        historial_powerby.append(MAPA_COLORES_LOGICA.get(numero, 'G')[1:][:1] +
                              MAPA_COLORES_LOGICA.get(numero, 'G')[:1] +
                              MAPA_COLORES_LOGICA.get(numero, 'G')[2:])

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

    def limpiar_secuencia(e=None):
        global estado_script, patron_activo, numeros_prediccion, giros_restantes, historial_numeros, historial_colores,\
            historial_combinado, historial_powerby

        seq_row.controls.clear()
        secuencia.clear()
        qty_text.content = ft.Text("Secuencia", color="black")
        qty_text.bgcolor = "white"

        estado_script = "ESPERANDO"
        patron_activo = "-"
        numeros_prediccion = set()
        giros_restantes = 0
        historial_numeros = deque(maxlen=20)
        historial_colores = deque(maxlen=7)
        historial_combinado = deque(maxlen=7)# Los patrones combinados tienen 14 caracteres (7 pares de 2)
        historial_powerby = deque(maxlen=7)  # Los patrones combinados tienen 21 caracteres (7 pares de 3)

        jugada_activa_txt.value = ""
        patron_activo_txt.value = ""
        estado_script = "ESPERANDO"
        giros_restantes = 7
        mensajes_txt.value = f"Esperando las proximas {giros_restantes} jugadas."
        # REEMPLAZA POR
        numeros_activos_txt.value = ""
        aciertos_txt.value = "—"
        page.update()

    def on_ruleta_change(e):
        sel = ruleta_dd.value
        info = meta.get(sel, {})
        # si tienes mensajes_txt:
        mensajes_txt.value = f"Ruleta: {sel}  ·  max_numeros={info.get('max_numeros', '-')}"
        page.update()

    def reed_URL(TARGET, URL_1, URL_2):
        import time
        import csv
        import math
        import requests
        from datetime import datetime
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

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
                "startedAt": started_at[:10]+ " " + started_at[11:][:8],
                "numero": outcome
            }

        HEADERS = {
            "User-Agent": "Mozilla/5.0",
        }
        url_end = URL_1 + "0" + URL_2
        qs = parse_qs(urlparse(url_end).query)
        page0 = 0
        size = int(qs.get("size", [50])[0])
        need_pages = math.ceil(TARGET / size)

        all_rows = []
        seen = set()
        i = 0
        orden = 0
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
                page.update()
                return
                #break

            for it in items:
                norm = normalize(it)

                if norm['numero'] == 0:
                    color = "V"
                    decena = "0"
                    columna = "0"
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
                            decena = "D3"

                    paridad = "P" if norm['numero'] % 2 == 0 else "I"
                    posicion = "A" if norm['numero'] > 18 else "B"

                    r = norm['numero'] % 3
                    columna = "C1" if r == 1 else ("C2" if r == 2 else "C3")


                valores = [norm['numero'], norm['startedAt'], orden, color, decena, paridad, columna, posicion]
                orden += 1

                all_rows.append(valores)
                mensajes_txt.value = f"Recolectando Jugadas -> acumuladas: {len(all_rows)}"
                page.update()
                if len(all_rows) >= TARGET:
                    break
            time.sleep(0.5)

        time.sleep(0.3)

        # Ordenar ascendente por fecha/hora
        all_rows.sort(key=lambda x: x[2], reverse=True)

        #Generaldo patrones de Colores

        res_color = construir_patrones.analizar_patrones_color_rows(all_rows)  # <- de tu módulo anterior
        data_json = construir_patrones.construir_json_estrategia_colores(res_color)
        with open("estrategia_colores.json", "w", encoding="utf-8") as f:
             json.dump(data_json, f, indent=2, ensure_ascii=False)

        # Guardar en CSV
        with open("ultimos_numeros.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["numero", "startedAt", "item_no"])
            writer.writerows(all_rows)

        mensajes_txt.value = f"✅Recoleccion de datos satifactoria con {len(all_rows)} jugadas."


        for it in all_rows:
            agregar_a_secuencia(it[0])

    def recopilar_jugadas(e):
        sel = ruleta_dd.value
        info = meta.get(sel)
        if not sel or not meta:
            mensajes_txt.value = "Seleccione una ruleta válida."
        else:
            # Aquí ya tienes la URL de la API por si luego la usas
            mensajes_txt.value = f"Recopilando jugadas de {sel} (máx: {info.get('max_numeros')})"
            reed_URL(info.get('max_numeros'), info.get("API_1"), info.get("API_2"))
            # api_url = meta.get("API")
            # ... tu lógica de recopilación (requests, etc.) ...
        page.update()

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
                "API_2": d.get("API_2")
            }

    ruleta_dd.options = [ft.dropdown.Option(n) for n in nombres]
    ruleta_dd.disabled = True
    if nombres:
        ruleta_dd.value = nombres[0]

    ruleta_block = ft.Container(
        content=ft.Row(
            [
                ruleta_dd,
                ft.ElevatedButton("Conectar API", on_click=recopilar_jugadas, disabled=True),
            ],
            spacing=4,
            alignment=ft.MainAxisAlignment.START,
        ),
        padding=4,
        bgcolor=ft.Colors.GREY_50,
        border=ft.border.all(1, ft.Colors.GREY_300),
        border_radius=10,
    )

    # --- Bloque botones: Recopilar + Generar + Limpiar ---
    top_controls_block = ft.Container(
        content=ft.Row(
            [
                ft.ElevatedButton("Recopilar", on_click=recopilar_jugadas),
                ft.ElevatedButton("Generar", on_click=generar_analisis, disabled=True),
                ft.OutlinedButton("Limpiar", on_click=limpiar_secuencia)
            ],
            spacing=4,
            alignment=ft.MainAxisAlignment.START,
        ),
        padding=4,
        bgcolor=ft.Colors.GREY_50,
        border=ft.border.all(1, ft.Colors.GREY_300),
        border_radius=10,
    )

    # --- Bloque de Mensajes (línea actualizable) ---
    mensajes_txt = ft.Text("Esperando las proximas 7 jugadas", size=12)  # inicia en blanco
    mensajes_block = ft.Container(
        content=ft.Row([ft.Text("Mensajes:", weight="bold"), mensajes_txt], spacing=8),
        padding=4,
        bgcolor=ft.Colors.GREY_50,
        border=ft.border.all(1, ft.Colors.GREY_300),
        border_radius=10,
    )

    # Secuencia inferior (chips)
    seq_row = ft.Row(
        spacing=4,
        wrap=False,
        scroll=ft.ScrollMode.ALWAYS,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    seq_box = ft.Container(
        content = seq_row,
        padding=4,
        bgcolor=ft.Colors.GREY_50,
        border=ft.border.all(1, ft.Colors.GREY_300),
        border_radius=10,
    )

    qty_text = ft.Text("Secuencia (0):", weight="bold")
    secuencia = []

    # --- Patron Activo ---
    patron_activo_txt = ft.Text("-", size=12)
    patron_activo_block = ft.Container(
        content=ft.Row(
            [ft.Text("Patron Activo:", weight="bold"), patron_activo_txt],
            spacing=4,
        ),
        padding=4,
        bgcolor=ft.Colors.GREY_50,
        border=ft.border.all(1, ft.Colors.GREY_300),
        border_radius=10,
    )

    # --- Jugada Activa ---
    jugada_activa_txt = ft.Text("-", size=12)
    jugada_activa_block = ft.Container(
        content=ft.Column(
            [ft.Text("Jugada Activa:", weight="bold"), jugada_activa_txt],
            spacing=4,
        ),
        padding=4,
        bgcolor=ft.Colors.GREY_50,
        border=ft.border.all(1, ft.Colors.GREY_300),
        border_radius=10,
    )

    # --- Numeros Activos ---
    numeros_activos_txt = ft.Text("-", size=12)
    numeros_activos_block = ft.Container(
        content=ft.Column(
            [ft.Text("Numeros Activos:", weight="bold"), numeros_activos_txt],
            spacing=4,
        ),
        padding=4,
        bgcolor=ft.Colors.GREY_50,
        border=ft.border.all(1, ft.Colors.GREY_300),
        border_radius=10,
    )

    # --- Aciertos ---
    aciertos_txt = ft.Text("-", size=12)

    aciertos_block = ft.Container(
        content=ft.Column(
            [
                ft.Row([ft.Text("Ventana de Aciertos:", weight="bold"), aciertos_txt], spacing=8),
            ],
            spacing=4,
        ),
        padding=4,
        bgcolor=ft.Colors.GREY_50,
        border=ft.border.all(1, ft.Colors.GREY_300),
        border_radius=10,
    )


    def agregar_a_secuencia(n: int):
        chip = ft.Container(
            width=25, height=25,
            bgcolor=color_bg(n),
            border_radius=999,
            alignment=ft.alignment.center,
            border=ft.border.all(1, ft.Colors.BLACK12),
            content=ft.Text(str(n), color=color_fg(n), size=11, weight="bold"),
            tooltip=f"Número {n}",
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
            content=ft.Text(str(n), color=color_fg(n), weight="bold"),
            on_click=lambda e, v=n: agregar_a_secuencia(v),
            tooltip=f"Clic: {n}",
        )

    # --- Columna 0 (alto = 3 filas) ---
    cero_columna = ft.Container(
        width=TILE_W,
        height=TILE_H * 3 + GAP * 2,
        bgcolor=color_bg(0),
        border=ft.border.all(1, ft.Colors.BLACK),
        border_radius=6,
        alignment=ft.alignment.center,
        content=ft.Text("0", color=color_fg(0), weight="bold"),
        on_click=lambda e: agregar_a_secuencia(0),
        tooltip="Clic: 0",
    )

    columnas_numeros = []
    for c in range(12):  # 12 columnas
        b = c * 3  # base: 0,3,6,...,33
        col = ft.Column(
            controls=[tile_num(b + 3), tile_num(b + 2), tile_num(b + 1)],
            spacing=GAP,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        columnas_numeros.append(col)

    tablero_scroll = ft.Row(
        controls=[cero_columna] + [ft.Container(content=col, padding=0) for col in columnas_numeros],
        spacing=GAP,
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
                    padding=8,
                    bgcolor=ft.Colors.GREY_100,
                    border=ft.border.all(1, ft.Colors.GREY_300),
                    border_radius=10,
                    height=TILE_H * 3 + GAP * 2 + 16,  # altura para encajar bien las 3 filas + padding
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
                aciertos_block,
            ],
            spacing=4,
            expand=True,
        )
    )

def log_uso():
    fecha_hora = datetime.now(timezone.utc)
    osname = platform.system()
    hostname = socket.gethostname()
    user = getpass.getuser()
    dispositivo = f"{osname} - {hostname} (user {user})"

    try:
        ip_publica = requests.get("https://api.ipify.org", timeout=5).text
    except:
        ip_publica = "N/A"

    # Registro en Logs de Render
    print(f"📝 Registro de uso -> {fecha_hora} | {dispositivo} | IP: {ip_publica}")


ft.app(target=main)
