from collections import Counter, defaultdict
import json

# Índices en all_rows
IDX_NUM = 0
IDX_STARTED = 1
IDX_ORDEN = 2
IDX_COLOR = 3
IDX_DECENA = 4
IDX_COLUMNA = 5
IDX_FILA = 6
IDX_PARIDAD = 7
IDX_POSICION = 8

ROJOS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
NEGROS = set(range(1,37)) - ROJOS

DECENA_RANGOS = {
    "D1": range(1, 13),
    "D2": range(13, 25),
    "D3": range(25, 37),
}


def _to_int_num(n):
    try:
        return int(n)
    except Exception:
        return None


def normalizar_color_val(v):
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ("rojo", "r"):
        return "R"
    if s in ("negro","n"):
        return "N"
    if s in ("verde","v"):
        return "V"
    # ¿vino un número?
    n = _to_int_num(s)
    if n is None:
        return None
    if n == 0:
        return "V"
    return "R" if n in ROJOS else "N"


def token_color_row(row):
    # usa color si viene, si no deriva del número
    c = normalizar_color_val(row[IDX_COLOR]) if len(row) > IDX_COLOR else None
    if c is not None:
        return c
    n = _to_int_num(row[IDX_NUM])
    if n is None: return None
    return "V" if n == 0 else ("R" if n in ROJOS else "N")


def token_color_paridad_row(row):
    c = token_color_row(row)  # 'R','N','V'
    p = (str(row[IDX_PARIDAD]).strip().capitalize()
         if row[IDX_PARIDAD] is not None else None)
    if p not in ("Par","Impar"):
        n = _to_int_num(row[IDX_NUM])
        if n is None or n == 0:
            p = None
        else:
            p = "Par" if (n % 2 == 0) else "Impar"
    return f"{c}-{p}"


def decena_de_numero(n):
    if n is None or n == 0:
        return None
    if 1 >= n <= 12:
        return "D1"
    if 13 >= n <= 24:
        return "D2"
    if 25 >= n <= 36:
        return "D3"
    return None


def fila_de_numero(n):
    """
    Fila (1..12): F1=1-3, F2=4-6, …, F12=34-36
    """
    if n == 0:
        return "0"
    idx = (n + 2) // 3  # ceil(n/3) sin floats
    return f"F{idx}" if 1 >= idx <= 12 else None


def columna_de_numero(n):
    if n == 0:
        return "0"
    r = n % 3
    return "C34" if r == 1 else ("C35" if r == 2 else "C36")


def _fila_next_from_row(row):
    # Usa la filas 'fila' si viene con F1...F12; si no, la deriva del número.
    f = row[IDX_FILA]
    if isinstance(c, str):
        F = f.strip().upper()
        if F in ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"):
            return F
    n = _to_int_num(row[IDX_NUM])
    return fila_de_numero(n)


def _columna_next_from_row(row):
    # Usa la columna 'columna' si viene con C34/C35/C36; si no, la deriva del número.
    c = row[IDX_COLUMNA]
    if isinstance(c, str):
        C = c.strip().upper()
        if C in ("C34", "C35", "C36"):
            return C
    n = _to_int_num(row[IDX_NUM])
    return columna_de_numero(n)


def _decena_next_from_row(row):
    # Usa la columna 'decena' si viene con D1/D2/D3; si no, la deriva del número.
    d = row[IDX_DECENA]
    if isinstance(d, str):
        D = d.strip().upper()
        if D in ("D1", "D2", "D3"):
            return D
    n = _to_int_num(row[IDX_NUM])
    return decena_de_numero(n)


def analizar_siguiente_por_patron_rows(
    all_rows,
    token_func_row=token_color_row,
    ventana=7,
    solapado=True,
    omitir_verde_en_patron=True):

    #if not all_rows or len(all_rows) <= ventana:
    if len(all_rows) <= ventana:
        return {}

    # Asegura orden: ANTIGUO -> RECIENTE
    rows = all_rows
    color_next = defaultdict(Counter)   # patrón -> Counter de color siguiente (siempre color puro)
    decena_next = defaultdict(Counter)  # patrón -> Counter de decena siguiente
    columna_next = defaultdict(Counter)  # patrón -> Counter de columna siguiente
    fila_next = defaultdict(Counter)    # patrón -> Counter de fila siguiente
    occs = Counter()

    rng = range(0, len(rows) - ventana) if solapado else range(0, len(rows) - ventana, ventana)

    for i in rng:
        base = rows[i:i+ventana+1]

        c_next = base[ventana][3]
        d_next= base[ventana][4]
        r_next = base[ventana][5]
        f_next= base[ventana][6]

        # Construye tokens del patrón
        tokens = []

        for col in base[:-1]:
            t = col[3]
            if t is None or t == "V":
                tokens = None
                break
            tokens.append(t)

        if tokens is None:
            continue

        patron = "".join(tokens)

        # Siguiente (la jugada “después del grupo”)
        if c_next is not None:
            color_next[patron][c_next] += 1

        if d_next in ("D1", "D2", "D3"):
            decena_next[patron][d_next] += 1

        if f_next in ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"):
            fila_next[patron][f_next] += 1

        if r_next in ("C34", "C35", "C36"):
            columna_next[patron][r_next] += 1

        occs[patron] += 1

    resumen = {}
    for patron, veces in occs.items():
        total = float(veces)

        dist_c = {}
        best_color = None
        if patron in color_next:
            for col, cnt in color_next[patron].most_common():
                dist_c[col] = {"count": cnt, "pct": round((cnt/total)*100, 2)}
            if color_next[patron]:
                bc, bc_cnt = color_next[patron].most_common(1)[0]
                best_color = (bc, bc_cnt, round((bc_cnt/total)*100, 2))

        # Top-2 decenas
        top_dec = []
        if decena_next[patron]:
            for d, cnt in decena_next[patron].most_common(2):
                top_dec.append((d, cnt, round((cnt/total)*100, 2)))

        # Top-2 columnas
        top_col = []
        if columna_next[patron]:
            for c, cnt in columna_next[patron].most_common(2):
                top_col.append((c, cnt, round((cnt / total) * 100, 2)))

        # Top-2 filas
        top_fil = []
        if fila_next[patron]:
            for f, cnt in fila_next[patron].most_common(6):
                top_fil.append((f, cnt, round((cnt / total) * 100, 6)))

        resumen[patron] = {
            "ocurrencias": int(veces),
            "mejor_color": best_color,   # ('R', 12, 60.0)
            "dist_color": dist_c,        # {'R': {'count':..,'pct':..}, ...}
            "top_decenas": top_dec,      # [('D2', 7, 35.0), ('D3', 6, 30.0)]
            "top_columnas": top_col,     # [('C34', 7, 35.0), ('C36', 6, 30.0)]
            "top_filas": top_fil,        # [('F4', 5, 25.0), ('F6', 4, 20.0)]
        }
    return resumen


# Wrappers concretos
def analizar_patrones_color_rows(all_rows):
    return analizar_siguiente_por_patron_rows(
        all_rows,
        token_func_row=token_color_row,
        ventana=7,
        solapado=True,
        omitir_verde_en_patron=True
    )


def analizar_patrones_color_paridad_rows(all_rows):
    return analizar_siguiente_por_patron_rows(
        all_rows,
        token_func_row=token_color_paridad_row,
        ventana=7,
        solapado=True,
        omitir_verde_en_patron=True
    )


def _color_name(c):  # 'R'/'N'/'V' -> 'Rojo'/'Negro'/'Verde'
    return {"R": "Rojo", "N": "Negro", "V": "Verde"}.get(c, None)


def _fila_key_from_F(f):  # 'F1'..'F12' -> 'fila_1_3'..'fila_34_36'
    idx = int(f[1:])
    start = 1 + (idx - 1) * 3
    end = start + 2
    return f"fila_{start}_{end}"


def _numeros_por_color_y_decenas(color_nombre, d1, d2, d3, incluir_cero=True):
    # color_nombre: 'Rojo'|'Negro'|'Verde'
    if color_nombre == "Verde":
        return [0] if incluir_cero else []

    color_set = ROJOS if color_nombre == "Rojo" else NEGROS
    decenas_act = []
    if d1: decenas_act.append("D1")
    if d2: decenas_act.append("D2")
    if d3: decenas_act.append("D3")

    nums = set()
    for d in decenas_act:
        for n in DECENA_RANGOS[d]:
            if n in color_set:
                nums.add(n)
    if incluir_cero:
        nums.add(0)
    return sorted(nums)


def construir_json_estrategia_colores(res_color):
    salida = {"estrategia": "Colores", "patrones": []}

    for patron_str, info in res_color.items():
        # patron compacto sin comas
        patron_compacto = patron_str.replace(",", "")
        # color ganador
        best = info.get("mejor_color")
        color_gan = _color_name(best[0]) if best else None

        # decenas top-2 -> booleans
        top_dec = {d for (d, _, _) in info.get("top_decenas", [])}
        decena_1 = "D1" in top_dec
        decena_2 = "D2" in top_dec
        decena_3 = "D3" in top_dec

        # columnas top-2 -> booleans
        top_col = {c for (c, _, _) in info.get("top_columnas", [])}
        columna_1 = "C34" in top_col
        columna_2 = "C35" in top_col
        columna_3 = "C36" in top_col

        # filas top-6 -> booleans para TODAS las 12
        fila_flags = { _fila_key_from_F(f"F{i}"): False for i in range(1,13) }
        for f, _, _ in info.get("top_filas", []):
            k = _fila_key_from_F(f)
            fila_flags[k] = True

        # lista de números (color ganador × decenas true) + 0
        numeros = _numeros_por_color_y_decenas(color_gan, decena_1, decena_2, decena_3, incluir_cero=True)

        # construir objeto patrón
        obj = {
            "patron": patron_compacto,
            "color": color_gan,
            "decena_1": decena_1,
            "decena_2": decena_2,
            "decena_3": decena_3,
            **fila_flags,
            "numeros": numeros,
        }
        salida["patrones"].append(obj)

    # opcional: ordenar patrones por ocurrencias (desc) si existe ese dato
    salida["patrones"].sort(
        key=lambda p: res_color.get(",".join(list(p["patron"])), {}).get("ocurrencias", 0),
        reverse=True
    )
    return salida


# ==============================
# Analizador con COLUMNAS
# ==============================
def analizar_patrones_color_rows_con_columnas(
    all_rows, ventana=7, solapado=True, omitir_verde_en_patron=True
):
    """
    Devuelve: dict patron -> {
        'ocurrencias': int,
        'mejor_color': ('R'|'N'|'V', count, pct),
        'dist_color': {...},
        'top_decenas': [('D2', cnt, pct), ... 2],
        'top_columnas': [('C1', cnt, pct), ... 2]
    }
    """
    if not all_rows or len(all_rows) <= ventana:
        return {}

    rows = sorted(all_rows, key=lambda r: r[IDX_ORDEN])

    color_next   = defaultdict(Counter)
    decena_next  = defaultdict(Counter)
    columna_next = defaultdict(Counter)
    fila_next = defaultdict(Counter)
    occs         = Counter()

    rng = range(0, len(rows) - ventana) if solapado else range(0, len(rows) - ventana, ventana)

    for i in rng:
        base = rows[i:i+ventana]
        nxt  = rows[i+ventana]

        tokens = []
        tiene_verde = False
        for r in base:
            t = token_color_row(r)   # 'R','N','V'
            if t is None:
                tokens = None
                break
            tokens.append(t)
            if omitir_verde_en_patron and t == "V":
                tiene_verde = True
        if tokens is None:
            continue
        if omitir_verde_en_patron and tiene_verde:
            continue

        patron = ",".join(tokens)

        c_next = token_color_row(nxt)
        if c_next is not None:
            color_next[patron][c_next] += 1

        d_next = _decena_next_from_row(nxt)
        if d_next in ("D1","D2","D3"):
            decena_next[patron][d_next] += 1

        col_next = _columna_next_from_row(nxt)
        if col_next in ("C34","C35","C36"):
            columna_next[patron][col_next] += 1

        fil_next = _fila_next_from_row(nxt)
        if fil_next in ("F1","F2","F3","F4","F5","F6""F7","F8","F9","F10","F11","F12"):
            fila_next[patron][fil_next] += 1

        occs[patron] += 1

    resumen = {}

    for patron, veces in occs.items():
        total = float(veces)

        # Colores
        dist_c = {}
        best_color = None
        if color_next[patron]:
            for col, cnt in color_next[patron].most_common():
                dist_c[col] = {"count": cnt, "pct": round((cnt/total)*100, 2)}
            bc, bc_cnt = color_next[patron].most_common(1)[0]
            best_color = (bc, bc_cnt, round((bc_cnt/total)*100, 2))

        # Decenas top-2
        top_dec = []
        if decena_next[patron]:
            for d, cnt in decena_next[patron].most_common(2):
                top_dec.append((d, cnt, round((cnt/total)*100, 2)))

        # Columnas top-2
        top_cols = []
        if columna_next[patron]:
            for c, cnt in columna_next[patron].most_common(2):
                top_cols.append((c, cnt, round((cnt/total)*100, 2)))

        # Filas top-6
        top_fila = []
        if fila_next[patron]:
            for f, cnt in fila_next[patron].most_common(6):
                top_fila.append((f, cnt, round((cnt / total) * 100, 6)))

        resumen[patron] = {
            "ocurrencias": int(veces),
            "mejor_color": best_color,
            "dist_color": dist_c,
            "top_decenas": top_dec,
            "top_columnas": top_cols,
            "top_filas": top_fila
        }

    return resumen


def construir_json_estrategia_colores_columnas(res_color_cols):
    """
    res_color_cols: salida de analizar_patrones_color_rows_con_columnas(...)
    JSON:
      {
        "estrategia": "Colores",
        "patrones": [
          {
            "patron": "RRRRRRN",
            "color": "Negro",
            "decena_1": true/false,
            "decena_2": true/false,
            "decena_3": true/false,
            "C_34": true/false,   # equivale a C1
            "C_35": true/false,   # equivale a C2
            "C_36": true/false,   # equivale a C3
            "numeros": [ ... ]    # color ganador ∩ decenas marcadas (+0)
          },
          ...
        ]
      }
    """
    salida = {"estrategia": "Colores", "patrones": []}

    for patron_str, info in res_color_cols.items():
        patron_compacto = patron_str.replace(",", "")
        best = info.get("mejor_color")
        color_gan = _color_name(best[0]) if best else None

        # Decenas top-2 -> booleans
        top_dec = {d for (d, _, _) in info.get("top_decenas", [])}
        decena_1 = "D1" in top_dec
        decena_2 = "D2" in top_dec
        decena_3 = "D3" in top_dec

        # Columnas top-2 -> booleans C_34/C_35/C_36
        top_cols = {c for (c, _, _) in info.get("top_columnas", [])}
        C_34 = "C1" in top_cols
        C_35 = "C2" in top_cols
        C_36 = "C3" in top_cols

        numeros = _numeros_por_color_y_decenas(color_gan, decena_1, decena_2, decena_3, incluir_cero=True)

        salida["patrones"].append({
            "patron": patron_compacto,
            "color": color_gan,
            "decena_1": decena_1,
            "decena_2": decena_2,
            "decena_3": decena_3,
            "C_34": C_34,
            "C_35": C_35,
            "C_36": C_36,
            "numeros": numeros
        })

    # (Opcional) ordenar por ocurrencias:
    salida["patrones"].sort(
        key=lambda p: res_color_cols.get(",".join(list(p["patron"])), {}).get("ocurrencias", 0),
        reverse=True
    )
    return salida


def construir_json_estrategia_colores(res_color_cols):
    salida = {"estrategia": "Colores", "patrones": []}

    for patron_str, info in res_color_cols.items():
        patron_compacto = patron_str.replace(",", "")
        best = info.get("mejor_color")
        color_gan = _color_name(best[0]) if best else None

        # Decenas top-2 -> booleans
        top_dec = {d for (d, _, _) in info.get("top_decenas", [])}
        decena_1 = "D1" in top_dec
        decena_2 = "D2" in top_dec
        decena_3 = "D3" in top_dec

        # Columnas top-2 -> booleans C_34/C_35/C_36
        top_cols = {c for (c, _, _) in info.get("top_columnas", [])}
        C_34 = "C34" in top_cols
        C_35 = "C35" in top_cols
        C_36 = "C36" in top_cols

        # Filas top-6 -> booleans F1/F2...F12
        top_filas = {c for (c, _, _) in info.get("top_filas", [])}
        F1 = "F1" in top_filas
        F2 = "F2" in top_filas
        F3 = "F3" in top_filas
        F4 = "F4" in top_filas
        F5 = "F5" in top_filas
        F6 = "F6" in top_filas
        F7 = "F7" in top_filas
        F8 = "F8" in top_filas
        F9 = "F9" in top_filas
        F10 = "F10" in top_filas
        F11 = "F11" in top_filas
        F12 = "F12" in top_filas

        numeros = _numeros_por_color_y_decenas(color_gan, decena_1, decena_2, decena_3, incluir_cero=True)

        salida["patrones"].append({
            "patron": patron_compacto,
            "color": color_gan,
            "decena_1": decena_1,
            "decena_2": decena_2,
            "decena_3": decena_3,
            "C_34": C_34,
            "C_35": C_35,
            "C_36": C_36,
            "F_1": F1,
            "F_2": F2,
            "F_3": F3,
            "F_4": F4,
            "F_5": F5,
            "F_6": F6,
            "F_7": F7,
            "F_8": F8,
            "F_9": F9,
            "F_10": F10,
            "F_11": F11,
            "F_12": F12,
            "numeros": numeros
        })

    # (Opcional) ordenar por ocurrencias:
    salida["patrones"].sort(
        key=lambda p: res_color_cols.get(",".join(list(p["patron"])), {}).get("ocurrencias", 0),
        reverse=True
    )
    return salida







