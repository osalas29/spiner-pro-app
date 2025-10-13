import flet as ft
from collections import deque
from typing import List, Set, Tuple, Optional, Dict
from datetime import datetime
import itertools
import os

# =======================================================================
# LÓGICA DEL MOTOR DE RULETA
# (SIN CAMBIOS EN ESTA SECCIÓN PARA PRESERVAR LA LÓGICA DE ANÁLISIS)
# =======================================================================

# --- MAPAS Y DICCIONARIOS GLOBALES (SIN CAMBIOS) ---
MAPA_COLORES = {
    0: 'G', 1: 'R', 2: 'N', 3: 'R', 4: 'N', 5: 'R', 6: 'N', 7: 'R', 8: 'N', 9: 'R',
    10: 'N', 11: 'N', 12: 'R', 13: 'N', 14: 'R', 15: 'N', 16: 'R', 17: 'N', 18: 'R',
    19: 'R', 20: 'N', 21: 'R', 22: 'N', 23: 'R', 24: 'N', 25: 'R', 26: 'N', 27: 'R',
    28: 'N', 29: 'N', 30: 'R', 31: 'N', 32: 'R', 33: 'N', 34: 'R', 35: 'N', 36: 'R'
}
ALGORITMOS = {
    0: {0, 1, 2, 3, 5, 7, 8, 10, 11, 12, 13, 14, 17, 19, 20, 21, 23, 26, 27, 28, 29, 30, 32, 33},
    1: {0, 1, 2, 4, 5, 7, 9, 10, 11, 12, 14, 15, 19, 20, 21, 23, 24, 26, 28, 31, 32, 33, 36},
    2: {0, 1, 2, 4, 7, 9, 11, 12, 14, 15, 18, 20, 21, 22, 25, 26, 28, 29, 30, 31, 32, 35, 36},
    3: {0, 1, 2, 3, 4, 8, 10, 11, 12, 13, 15, 16, 19, 21, 23, 26, 27, 28, 30, 32, 33, 35, 36},
    5: {0, 2, 3, 5, 8, 9, 10, 12, 14, 15, 17, 19, 20, 21, 23, 24, 25, 26, 28, 31, 32, 34, 35},
    6: {0, 1, 3, 4, 5, 6, 7, 9, 11, 13, 15, 16, 18, 19, 22, 24, 26, 27, 29, 31, 32, 33, 34, 36},
    9: {0, 1, 2, 3, 4, 6, 8, 9, 10, 11, 15, 16, 19, 24, 25, 27, 28, 30, 31, 34, 35, 36},
}
COMBINACIONES_COLOR_PREDICCION = [
    {"patrones": ["NNNNNNN"], "resultado_color": 'N'},
    {"patrones": ["RNNNNNN", "NRNNNNN", "NNRNNNN", "NNNRNNN", "NNNNRNN", "NNNNNRN", "NNNNNNR"], "resultado_color": 'R'},
    {"patrones": ["RRNNNNN", "RNRNNNN", "RNNRNNN", "RNNNRNN", "RNNNNRN", "RNNNNNR", "NRRNNNN", "NRNRNNN", "NRNNRNN", "NRNNNRN", "NRNNNNR", "NNRRNNN", "NNRNRNN", "NNRNNRN", "NNRNNNR", "NNNRRNN", "NNNRNRN", "NNNRNNR", "NNNNRRN", "NNNNRNR", "NNNNNRR"], "resultado_color": 'N'},
    {"patrones": ["RRRNNNN", "RRNRNNN", "RRNNRNN", "RRNNNRN", "RRNNNNR", "RNRRNNN", "RNRNRNN", "RNRNNRN", "RNRNNNR", "RNNRRNN", "RNNRNRN", "RNNRNNR", "RNNNRRN", "RNNNRNR", "RNNNNRR", "NRRRNNN", "NRRNRNN", "NRRNNRN", "NRRNNNR", "NRNRRNN", "NRNRNRN", "NRNRNNR", "NRNNRRN", "NRNNRNR", "NRNNNRR", "NNRRRNN", "NNRRNRN", "NNRRNNR", "NNRNRRN", "NNRNRNR", "NNRNNRR", "NNNRRRN", "NNNRRNR", "NNNRNRR", "NNNNRRR"], "resultado_color": 'R'},
    {"patrones": ["RRRRNNN", "RRRNRNN", "RRRNNRN", "RRRNNNR", "RRNRRNN", "RRNRNRN", "RRNRNNR", "RRNNRRN", "RRNNRNR", "RRNNNRR", "RNRRRNN", "RNRRNRN", "RNRRNNR", "RNRNRRN", "RNRNRNR", "RNRNNRR", "RNNRRRN", "RNNRRNR", "RNNRNRR", "RNNNRRR", "NRRRRNN", "NRRRNRN", "NRRRNNR", "NRRNRRN", "NRRNRNR", "NRRNNRR", "NRNRRRN", "NRNRRNR", "NRNRNRR", "NRNNRRR", "NNRRRRN", "NNRRRNR", "NNRRNRR", "NNRNRRR", "NNNRRRR"], "resultado_color": 'N'},
    {"patrones": ["RRRRRNN", "RRRRNRN", "RRRRNNR", "RRRNRRN", "RRRNRNR", "RRRNNRR", "RRNRRRN", "RRNRRNR", "RRNRNRR", "RRNNRRR", "RNRRRRN", "RNRRRNR", "RNRRNRR", "RNRNRRR", "RNNRRRR", "NRRRRRN", "NRRRRNR", "NRRRNRR", "NRRNRRR", "NRNRRRR", "NNRRRRR"], "resultado_color": 'R'},
    {"patrones": ["RRRRRRN", "RRRRRNR", "RRRRNRR", "RRRNRRR", "RRNRRRR", "RNRRRRR", "NRRRRRR"], "resultado_color": 'N'}, 
    {"patrones": ["RRRRRRR"], "resultado_color": 'R'} 
]
COMBINACIONES_AB_PREDICCION = [
{"patrones": [
        "BBBBBBB"
    ], 
"resultado_ab" : "BAJOS"
},
{"patrones": [
        "ABBBBBB", "BABBBBB", "BBABBBB", "BBBABBB", "BBBBABB", "BBBBBAB", "BBBBBBA"
    ], 
"resultado_ab" : "ALTOS" 
},
{"patrones": [
        "AABBBBB", "ABABBBB", "ABBABBB", "ABBBABB", "ABBBBAB", "ABBBBBA", "BAABBBB",
        "BABABBB", "BABBABB", "BABBBAB", "BABBBBA", "BBAABBB", "BBABABB", "BBABBAB",
        "BBABBBA", "BBBAABB", "BBBABAB", "BBBABBA", "BBBBAAB", "BBBBABA", "BBBBBAA"
    ], 
"resultado_ab" : "BAJOS"
}, 
{"patrones": [
        "AAABBBB", "AABABBB", "AABBABB", "AABBBAB", "AABBBBA", "ABAABBB", "ABABABB",
        "ABABBAB", "ABABBBA", "ABBAABB", "ABBABAB", "ABBABBA", "ABBBAAB", "ABBBABA",
        "ABBBBAA", "BAAABBB", "BAABABB", "BAABBAB", "BAABBBA", "BABAABB", "BABABAB",
        "BABABBA", "BABBAAB", "BABBABA", "BABBBAA", "BBAAABB", "BBAABAB", "BBAABBA",
        "BBABAAB", "BBABABA", "BBABBAA", "BBBAAAB", "BBBAABA", "BBBABAA", "BBBBAAA"
    ], 
"resultado_ab" : "ALTOS"
},
{"patrones": [
        "AAAABBB", "AAABABB", "AAABBAB", "AAABBBA", "AABAABB", "AABABAB", "AABABBA",
        "AABBAAB", "AABBABA", "AABBBAA", "ABAAABB", "ABAABAB", "ABAABBA", "ABABAAB",
        "ABABABA", "ABABBAA", "ABBAAAB", "ABBAABA", "ABBABAA", "ABBBAAA", "BAAAABB",
        "BAAABAB", "BAAABBA", "BAABAAB", "BAABABA", "BAABBAA", "BABAAAB", "BABAABA",
        "BABABAA", "BABBAAA", "BBAAAAB", "BBAAABA", "BBAABAA", "BBABAAA", "BBBAAAA"
    ], 
"resultado_ab" : "BAJOS"
},
{"patrones": [
        "AAAAABB", "AAAABAB", "AAAABBA", "AAABAAB", "AAABABA", "AAABBAA", "AABAAAB",
        "AABAABA", "AABABAA", "AABBAAA", "ABAAAAB", "ABAAABA", "ABAABAA", "ABABAAA",
        "ABBAAAA", "BAAAAAB", "BAAAABA", "BAAABAA", "BAABAAA", "BABAAAA", "BBAAAAA"
    ], 
"resultado_ab" : "ALTOS"
},
{"patrones": [
        "AAAAAAB", "AAAAABA", "AAAABAA", "AAABAAA", "AABAAAA", "ABAAAAA", "BAAAAAA"
    ], 
"resultado_ab" : "BAJOS"
},
{"patrones": [
        "AAAAAAA"
    ], 
"resultado_ab" : "ALTOS"
}
]
LONGITUD_BLOQUE = 7

def color_token(n: int) -> str:
    return MAPA_COLORES.get(n, 'G')

def alto_bajo_token(n: int) -> str:
    """Mapea un número de ruleta a 'A' (Alto) o 'B' (Bajo). 0 se trata como Bajo."""
    if 1 <= n <= 18:
        return 'B'
    elif 19 <= n <= 36:
        return 'A'
    else: # n == 0
        return 'B' 

def patron_inicial_12(tokens_bloque: List[str]) -> Tuple[Optional[str], Optional[str]]:
    N = LONGITUD_BLOQUE
    if len(tokens_bloque) < N: return None, None 
    patron_string = "".join(tokens_bloque[-N:])
    for entry in COMBINACIONES_COLOR_PREDICCION:
        if patron_string in entry["patrones"]:
            return entry["resultado_color"], patron_string
    return None, None

def patron_altos_bajos(bloque: List[int]) -> Tuple[Optional[str], Optional[str], Tuple[int, int]]:
    N = LONGITUD_BLOQUE
    
    # Usamos solo los últimos N números para el análisis de patrón, incluso si el bloque es más largo (historial)
    analisis_bloque = bloque[-N:]
    
    if len(analisis_bloque) < N:
        # Lógica para mostrar el conteo parcial (si no está completo)
        bajos_parcial = sum(1 for n in analisis_bloque if 1 <= n <= 18 or n == 0)
        altos_parcial = sum(1 for n in analisis_bloque if 19 <= n <= 36)
        return None, None, (bajos_parcial, altos_parcial) 
    
    # Crear la cadena de patrón (ej: "AABBBBB")
    tokens_ab = [alto_bajo_token(n) for n in analisis_bloque]
    patron_string = "".join(tokens_ab)
    
    bajos_final = sum(1 for token in tokens_ab if token == 'B')
    altos_final = sum(1 for token in tokens_ab if token == 'A')

    for entry in COMBINACIONES_AB_PREDICCION:
        if patron_string in entry["patrones"]:
            # El resultado es "ALTOS" o "BAJOS"
            return entry["resultado_ab"], patron_string, (bajos_final, altos_final)
            
    # Si el bloque está completo pero el patrón no está en el diccionario
    return None, None, (bajos_final, altos_final)


def detectar_algoritmos(bloque: List[int]) -> List[int]:
    ULTIMOS_RELEVANTES = 3
    RANGO_VECINOS = 1
    MIN_COINCIDENCIAS = 3
    
    rueda = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23,
             10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]
    inversos_fijos = {1, 2, 3, 6, 9, 10, 11, 12, 13, 20, 21, 22, 23, 30, 31, 32, 33}

    def obtener_vecinos_local(n, rango=1):
        try: idx = rueda.index(n)
        except ValueError: return set()
        return {rueda[(idx + i) % len(rueda)] for i in range(-rango, rango + 1) if i != 0}

    if len(bloque) < ULTIMOS_RELEVANTES: return []

    ultimos = bloque[-ULTIMOS_RELEVANTES:] 
    control = set()
    for num in ultimos:
        vecinos = obtener_vecinos_local(num, rango=RANGO_VECINOS)
        control |= {num} | vecinos
    control |= {n for n in control if n in inversos_fijos}

    algoritmos_validos = [alg for alg, nums in ALGORITMOS.items() if all(n in nums for n in ultimos)]
    if not algoritmos_validos: return []

    activos = []
    for alg in algoritmos_validos:
        nums = ALGORITMOS[alg]
        if len(control.intersection(nums)) < MIN_COINCIDENCIAS: continue
        if sum(1 for n in bloque if n in nums) < MIN_COINCIDENCIAS: continue
        activos.append(alg)

    return sorted(activos)[:1] 

def calcular_jugada(bloque: List[int]) -> dict:
    # Solo usamos el bloque más reciente (últimos N giros) para la predicción de color/algoritmo
    bloque_relevante = bloque[-LONGITUD_BLOQUE:]
    
    colores = [color_token(n) for n in bloque_relevante]
    
    pred_color, _ = patron_inicial_12(colores) 

    if pred_color == 'R':
        color_sel = 'Rojo'
        base_color = {n for n, c in MAPA_COLORES.items() if c == 'R'}
    elif pred_color == 'N':
        color_sel = 'Negro'
        base_color = {n for n, c in MAPA_COLORES.items() if c == 'N'}
    else:
        color_sel = 'N/A'
        base_color = set()

    activos = detectar_algoritmos(bloque_relevante)
    base_alg = set().union(*(ALGORITMOS[alg] for alg in activos)) if activos else set()
    
    MINIMO_ALGORITMOS_REQUERIDOS = 1 
    
    if len(activos) < MINIMO_ALGORITMOS_REQUERIDOS or not base_alg or pred_color is None:
        return {
             "bloque": bloque,
             "jugada_detectada": color_sel, 
             "algoritmos_activos": activos,
             "jugada_final": [],
             "base_alg": sorted(base_alg)
        }

    universo_valido = base_alg & base_color
    jugada_final: Set[int] = universo_valido

    return {
        "bloque": bloque,
        "jugada_detectada": color_sel,
        "algoritmos_activos": activos,
        "jugada_final": sorted(jugada_final),
        "base_alg": sorted(base_alg)
    }


# --- CLASE MOTOR DE ESTADO PARA FLET (SIN CAMBIOS) ---
class RuletaEngine:
    def __init__(self, long_bloque: int = 7):
        self.N = long_bloque
        self.state = "COLLECT_BLOCK"
        self.block: List[int] = [] 
        self.jugada_set: Set[int] = set()
        self.post_count = 0
        # post_tail tiene una longitud máxima de N para asegurar que se mantiene el historial 
        self.post_tail = deque(maxlen=long_bloque) 
        self.MAPA_COLORES = MAPA_COLORES
        self.prediccion_ab = "N/A" 

    def get_full_history(self) -> List[int]:
        """Combina el bloque base con los giros post-apuesta para obtener el historial completo y reciente."""
        return list(self.block) + list(self.post_tail)

    def process_spin(self, numero: int) -> Dict:
        
        if numero == 0:
            self.state = "COLLECT_BLOCK"
            self.block = []
            self.jugada_set = set()
            self.post_count = 0
            self.post_tail.clear()
            self.prediccion_ab = "N/A" 
            return {"status": "RESET", "message": "CERO detectado. Reinicio completo."}

        if self.state == "COLLECT_BLOCK":
            # El bloque crece hasta N, luego desliza
            if len(self.block) == self.N:
                self.block.pop(0) # Elimina el más antiguo
            self.block.append(numero)
            
            current_history = self.get_full_history() # Simplemente self.block aquí, pero mantiene la consistencia
            
            # --- ANÁLISIS INDEPENDIENTE DE ALTOS/BAJOS USANDO PATRONES ---
            prediccion_ab, _, (bajos, altos) = patron_altos_bajos(current_history)
            
            if prediccion_ab:
                self.prediccion_ab = f"{prediccion_ab.upper()} ({bajos}B, {altos}A)"
            else:
                self.prediccion_ab = f"N/A ({bajos}B, {altos}A)"
            
            if len(self.block) < self.N:
                return {"status": "COLLECTING", "message": f"Faltan {self.N - len(self.block)} para el bloque."}
            
            # Si el bloque está completo, calculamos jugada y decidimos el siguiente estado
            res = calcular_jugada(self.block)
            
            if res["algoritmos_activos"] and res["jugada_final"]:
                self.jugada_set = set(res["jugada_final"])
                self.state = "WAIT_ACIERTO"
                self.post_count = 0
                self.post_tail.clear()
                return {"status": "JUGADA_ACTIVA", "result": res}
            else:
                # Si no hay jugada, mantenemos el estado COLLECT_BLOCK y el bloque ya deslizó
                return {"status": "NO_JUGADA", "result": res}

        elif self.state == "WAIT_ACIERTO":
            self.post_count += 1
            self.post_tail.append(numero) # Agrega el número a la cola post-apuesta
            
            if numero in self.jugada_set:
                # ACIERTO: Recortamos el block base y reiniciamos
                keep = min(max(self.post_count, 1), self.N) # Mantener hasta N elementos, pero mínimo 1
                self.block = list(self.post_tail)[-keep:] 
                self.jugada_set = set() 
                self.state = "COLLECT_BLOCK"
                self.post_count = 0 # Reiniciar la cola post-apuesta para que esté vacía en el siguiente giro COLLECT
                self.post_tail.clear()
                self.prediccion_ab = "N/A" # Se actualizará en el siguiente giro (COLLECTING)
                return {"status": "ACIERTO", "message": f"¡ACIERTO! Número {numero} Ganador. Nuevo Bloque base.", "acierto_num": numero}
            
            # WAITING: Actualizamos Altos/Bajos para el estado WAITING (usa los últimos N del historial completo)
            current_history = self.get_full_history()
            prediccion_ab, _, (bajos, altos) = patron_altos_bajos(current_history)

            if prediccion_ab:
                self.prediccion_ab = f"{prediccion_ab.upper()} ({bajos}B, {altos}A)"
            else:
                self.prediccion_ab = f"N/A ({bajos}B, {altos}A)"
            
            return {"status": "WAITING", "message": f"Esperando acierto (post={self.post_count})."}
            
        return {"status": "INTERNAL_ERROR", "message": "Estado desconocido."}

    def reset_all(self):
        """Función para limpiar todo el estado del motor."""
        self.state = "COLLECT_BLOCK"
        self.block = []
        self.jugada_set = set()
        self.post_count = 0
        self.post_tail.clear()
        self.prediccion_ab = "N/A"

# =======================================================================
# INTERFAZ FLET (CORRECCIÓN DEFINITIVA DE COMPATIBILIDAD Y SCROLL HORIZONTAL)
# =======================================================================

def main(page: ft.Page):
    page.title = "Bot de Ruleta - Flet Expert Mode 🚀"
    page.vertical_alignment = ft.MainAxisAlignment.START
    
    # --- CONSTANTES DE PÁGINA ---
    page.window_width = 380 
    page.window_height = 650 
    page.bgcolor = ft.Colors.BLUE_GREY_900

    engine = RuletaEngine(long_bloque=LONGITUD_BLOQUE)

    # --- CONSTANTES DE TAMAÑO (COMPACTADAS) ---
    FONT_SIZE_SMALL = 11 
    FONT_SIZE_MEDIUM = 13
    CHIP_SIZE = 26 
    BUTTON_SIZE = 38 
    ZERO_HEIGHT = BUTTON_SIZE * 3 + 2 
    CONTROLS_WIDTH = page.window_width - 20 

    # --- Componentes de la Interfaz (Definidos antes de su uso) ---
    
    txt_status = ft.Text("Listo para empezar. Ingresa 7 números.", color=ft.Colors.YELLOW_ACCENT_100, size=FONT_SIZE_MEDIUM)
    
    # Vista del Bloque Actual
    block_view = ft.Row(
        controls=[],
        wrap=True,
        spacing=2, 
        alignment=ft.MainAxisAlignment.START,
    )
    txt_block_label = ft.Text(f"Bloque Actual ({engine.N} giros):", color=ft.Colors.WHITE70, size=FONT_SIZE_SMALL) 

    # Vista de los últimos 2 números con color
    ultimos_dos_view = ft.Row(
        controls=[],
        spacing=2, 
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.CENTER
    )
    
    # Predicción Altos/Bajos
    txt_altos_bajos = ft.Text(
        "Análisis Altos/Bajos: N/A",
        color=ft.Colors.PURPLE_ACCENT_100,
        weight=ft.FontWeight.BOLD,
        size=FONT_SIZE_MEDIUM
    )
    
    # Vista de chips de la Jugada Final
    numbers_view = ft.Row(
        controls=[],
        wrap=True, 
        spacing=3, 
        alignment=ft.MainAxisAlignment.START, 
        vertical_alignment=ft.CrossAxisAlignment.START,
    )
    
    # Botón de Reset (CORREGIDO)
    btn_reset = ft.ElevatedButton(
        text="🔴 RESET", 
        on_click=lambda e: reset_app(e), 
        icon=ft.Icons.RESTART_ALT, 
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.RED_900,
            color=ft.Colors.WHITE,
            padding=ft.padding.symmetric(horizontal=15, vertical=5) 
        ),
        width=CONTROLS_WIDTH 
    )
    
    jugada_container = ft.Container(
        content=numbers_view,
        padding=5, 
        border_radius=8, 
        border=ft.border.all(2, ft.Colors.BLUE_GREY_700),
        bgcolor=ft.Colors.BLUE_GREY_900,
        alignment=ft.alignment.top_left,
        width=CONTROLS_WIDTH 
    )

    # --- Funciones de UI ---
    
    def get_number_color(number: int) -> str:
        token = engine.MAPA_COLORES.get(number, 'G')
        if token == 'R': return ft.Colors.RED_700
        if token == 'N': return ft.Colors.BLACK87
        return ft.Colors.GREEN_700
        
    def create_number_chip(number: int, size: int = CHIP_SIZE) -> ft.Container: 
        color = get_number_color(number)
        return ft.Container(
            content=ft.Text(str(number), weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=FONT_SIZE_SMALL - 1), 
            width=size,
            height=size,
            alignment=ft.alignment.center,
            bgcolor=color,
            border_radius=ft.border_radius.all(CHIP_SIZE / 2),
        )

    def submit_spin(num: int):
        result = engine.process_spin(num)
        update_ui(result)
        
    def reset_app(e):
        engine.reset_all()
        update_ui({"status": "RESET", "message": "Reinicio manual completado."}) 

    def create_roulette_button(number: int) -> ft.Container:
        color = get_number_color(number)
        
        width = BUTTON_SIZE 
        height = BUTTON_SIZE
        
        if number == 0:
             height = ZERO_HEIGHT 
             width = BUTTON_SIZE + 10 
        
        btn = ft.ElevatedButton(
            text=str(number),
            on_click=lambda e: submit_spin(number), 
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=5),
                bgcolor=color,
                color=ft.Colors.WHITE,
                padding=ft.padding.all(3) 
            ),
            width=width,
            height=height,
        )
        return ft.Container(btn, padding=ft.padding.all(1))
    
    # REFERENCIA GLOBAL AL CONTENIDO DEL ft.Container DE ESTADO
    status_content_column = ft.Column([ 
        ft.Text("ESTADO:", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=FONT_SIZE_MEDIUM), 
        
        # El status_row_controls se llena en update_ui (ft.Column contiene ft.Row)
        ft.Column([txt_status]), 
        
        ft.Divider(height=2, color=ft.Colors.WHITE10), 
        
        # Bloque Actual con chips de color 
        ft.Column([
            txt_block_label,
            block_view
        ]),
        
        ft.Divider(height=2, color=ft.Colors.WHITE10), 
        txt_altos_bajos, 
    ])
    
    def update_ui(result: Dict):
        status = result.get("status", "...")
        message = result.get("message", "")
        
        full_history = engine.get_full_history()
        
        # 1. ACTUALIZACIÓN DEL BLOQUE (CHIPS DE COLORES)
        block_view.controls.clear()
        display_history = list(full_history)
        display_history.reverse() 
        block_view.controls.extend(
            create_number_chip(n, size=CHIP_SIZE) for n in display_history 
        )
        
        # 2. ACTUALIZACIÓN DE "ÚLTIMOS 2"
        ultimos_dos_view.controls.clear()
        ultimos_dos_nums = full_history[-2:]
        ultimos_dos_nums.reverse()
        
        if ultimos_dos_nums: 
            ultimos_dos_view.controls.append(ft.Text("Últimos 2:", color=ft.Colors.WHITE70, size=FONT_SIZE_SMALL, weight=ft.FontWeight.BOLD)) 
            ultimos_dos_view.controls.extend(
                create_number_chip(n, size=CHIP_SIZE - 4) for n in ultimos_dos_nums 
            )
        
        # 3. Lógica de Actualización de Status
        status_row_container = status_content_column.controls[1]
        
        if status == "RESET" or status == "ACIERTO":
            txt_status.value = f"🎉 {message}" if status == "ACIERTO" else f"🟢 {message}"
            txt_status.color = ft.Colors.GREEN_ACCENT_700
            status_row_container.controls.clear()
            status_row_container.controls.append(txt_status)
            
        elif status in ["COLLECTING", "NO_JUGADA", "JUGADA_ACTIVA", "WAITING"]:
            
            if status == "COLLECTING":
                txt_status.value = f"🟡 RECOLECTANDO: {message}"
                txt_status.color = ft.Colors.YELLOW_ACCENT_100
            elif status == "NO_JUGADA":
                txt_status.value = f"🔴 Sin jugada detectada. Bloque avanzado."
                txt_status.color = ft.Colors.RED_ACCENT_700
            elif status == "JUGADA_ACTIVA":
                jugada = result['result']
                # Compactar la línea de jugada
                txt_status.value = (
                    f"✅ JUGADA: Apostar {jugada['jugada_detectada']}! Algoritmo(s): {jugada['algoritmos_activos']}"
                )
                txt_status.color = ft.Colors.BLUE_ACCENT_100
            elif status == "WAITING":
                txt_status.value = f"⏳ ESPERANDO ACIERTO (Giro post {engine.post_count})"
                txt_status.color = ft.Colors.ORANGE_500

            # NO PERMITIR WRAP para forzar el scroll horizontal en el contenedor
            status_row_controls = ft.Row([
                txt_status, 
                ultimos_dos_view
            ], spacing=2, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=False) 
            
            status_row_container.controls.clear()
            status_row_container.controls.append(status_row_controls)
            
        # 4. Lógica para mostrar la Jugada Final
        numbers_view.controls.clear()
        jugada_display = list(engine.jugada_set) if status in ["JUGADA_ACTIVA", "WAITING"] else []
        numbers_view.controls.extend(
            create_number_chip(n, size=CHIP_SIZE) for n in sorted(jugada_display) 
        )
        
        if not jugada_display and status in ["JUGADA_ACTIVA", "WAITING"]:
            numbers_view.controls.append(ft.Text("Jugada vacía o no activa.", color=ft.Colors.RED_500, size=FONT_SIZE_MEDIUM)) 

        # 5. Actualización del análisis de Altos/Bajos
        txt_altos_bajos.value = f"Análisis Altos/Bajos: {engine.prediccion_ab}"
        
        if "ALTOS" in engine.prediccion_ab:
            txt_altos_bajos.color = ft.Colors.RED_ACCENT_100
        elif "BAJOS" in engine.prediccion_ab:
            txt_altos_bajos.color = ft.Colors.WHITE
        elif "N/A" in engine.prediccion_ab:
            txt_altos_bajos.color = ft.Colors.PURPLE_ACCENT_100

        page.update()

    # --- Creación de UI (Parrilla de la Ruleta) ---

    cero_col = ft.Column([create_roulette_button(0)], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.START, alignment=ft.MainAxisAlignment.CENTER)
    
    row_3_nums = [n for n in range(1, 37) if n % 3 == 0]
    row_3_btns = [create_roulette_button(n) for n in row_3_nums]
    row_3 = ft.Row(row_3_btns, spacing=0, alignment=ft.MainAxisAlignment.START)

    row_2_nums = [n for n in range(1, 37) if n % 3 == 2]
    row_2_btns = [create_roulette_button(n) for n in row_2_nums]
    row_2 = ft.Row(row_2_btns, spacing=0, alignment=ft.MainAxisAlignment.START)
    
    row_1_nums = [n for n in range(1, 37) if n % 3 == 1]
    row_1_btns = [create_roulette_button(n) for n in row_1_nums]
    row_1 = ft.Row(row_1_btns, spacing=0, alignment=ft.MainAxisAlignment.START)

    roulette_grid_of_rows = ft.Column([row_3, row_2, row_1], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.START)

    # Componente principal de la parrilla (alineado a START)
    full_board_row = ft.Row(
        controls=[cero_col, roulette_grid_of_rows],
        spacing=0, 
        alignment=ft.MainAxisAlignment.START, 
        vertical_alignment=ft.CrossAxisAlignment.START 
    )
    
    # SCROLL HORIZONTAL DEL TABLERO: Usamos ft.ListView con horizontal=True
    scrollable_board = ft.ListView(
        controls=[full_board_row],
        height=ZERO_HEIGHT + 10,
        # Nota: horizontal=True es la propiedad para scroll horizontal en ListView
        horizontal=True 
    )
    
    # SCROLL HORIZONTAL DEL BLOQUE DE ESTADO: Usamos ft.ListView con horizontal=True
    # Forzamos que el contenido interno sea más ancho que la pantalla para activar el scroll.
    wide_status_row = ft.Row(
        controls=[status_content_column],
        width=CONTROLS_WIDTH * 2, 
        alignment=ft.MainAxisAlignment.START
    )

    status_content_container = ft.Container(
        content=ft.ListView(
            controls=[wide_status_row],
            height=180, 
            horizontal=True 
        ),
        padding=5, 
        border_radius=8,
        bgcolor=ft.Colors.BLUE_GREY_800,
        width=CONTROLS_WIDTH, 
    )

    # Agrega todos los componentes a la página
    page.add(
        ft.Container(height=5), 
        ft.Row([btn_reset], alignment=ft.MainAxisAlignment.START), 
        ft.Container(height=5), 
        scrollable_board, 
        ft.Divider(height=5, color=ft.Colors.WHITE38), 
        status_content_container, 
        ft.Divider(height=5, color=ft.Colors.WHITE38), 
        ft.Text("🎯 JUGADA FINAL (Cruce Algoritmo/Color):", size=FONT_SIZE_MEDIUM, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, text_align=ft.TextAlign.LEFT), 
        jugada_container
    )
    
    # Inicializamos la UI
    update_ui({"status": "COLLECTING", "message": f"Listo para empezar. Ingresa {engine.N} números."})
    
# =======================================================================
# INICIO DE LA APLICACIÓN
# =======================================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    
    ft.app(
        target=main, 
        view=ft.AppView.WEB_BROWSER, 
        port=port, 
        host="0.0.0.0"
    )

