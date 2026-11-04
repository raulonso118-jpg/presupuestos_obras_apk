"""Cálculo local, determinista y compartido por Maestro y Arquitecto Pro."""
import math


LIMITES = {
    "largo": (0.1, 10000.0),
    "alto": (0.1, 30.0),
    "dinero": (0.0, 10_000_000.0),
    "porcentaje": (0.0, 100.0),
}


def _numero(datos, clave, defecto, categoria):
    valor = datos.get(clave)
    try:
        numero = float(defecto if valor in (None, "") else valor)
    except (TypeError, ValueError):
        raise ValueError(f"El valor de «{clave}» debe ser numérico.")
    if not math.isfinite(numero):
        raise ValueError(f"El valor de «{clave}» no es válido.")
    minimo, maximo = LIMITES[categoria]
    if not minimo <= numero <= maximo:
        raise ValueError(f"«{clave}» debe estar entre {minimo:g} y {maximo:g}.")
    return numero


def calcular_materiales(largo, alto, precios=None):
    if precios is None:
        precios = {}
    area = largo * alto
    num_castillos = int(largo / 2.5) + 1
    tramos_varilla = num_castillos * (alto + 0.5) * 4 / 6.0
    
    piezas_block = round(area * 12.5 * 1.05)
    sacos_cemento = round(area * 0.22, 1)
    m3_arena = round(area * 0.025, 2)
    tramos_varilla_val = round(tramos_varilla, 1)
    kg_alambre = round(tramos_varilla * 0.5, 1)

    # Precios unitarios por defecto (MXN)
    p_block = precios.get("precio_block", 15.0)
    p_cemento = precios.get("precio_cemento", 220.0)
    p_arena = precios.get("precio_arena", 600.0)
    p_varilla = precios.get("precio_varilla", 120.0)
    p_alambre = precios.get("precio_alambre", 35.0)

    costo_block = piezas_block * p_block
    costo_cemento = sacos_cemento * p_cemento
    costo_arena = m3_arena * p_arena
    costo_varilla = tramos_varilla_val * p_varilla
    costo_alambre = kg_alambre * p_alambre
    costo_total_materiales = costo_block + costo_cemento + costo_arena + costo_varilla + costo_alambre

    return {
        "area_m2": round(area, 2),
        "piezas_block": piezas_block,
        "sacos_cemento": sacos_cemento,
        "m3_arena": m3_arena,
        "tramos_varilla": tramos_varilla_val,
        "kg_alambre": kg_alambre,
        "dias_trabajo": round(area / 7.0, 1),
        "costo_block": round(costo_block, 2),
        "costo_cemento": round(costo_cemento, 2),
        "costo_arena": round(costo_arena, 2),
        "costo_varilla": round(costo_varilla, 2),
        "costo_alambre": round(costo_alambre, 2),
        "costo_total_materiales": round(costo_total_materiales, 2),
    }


def calcular_maestro(datos):
    largo = _numero(datos, "largo", 10.0, "largo")
    alto = _numero(datos, "alto", 2.0, "alto")
    pago_peon = _numero(datos, "pago_peon", 350, "dinero")
    cobro_m2 = _numero(datos, "cobro_m2", 300, "dinero")
    
    precios = {
        "precio_block": _numero(datos, "precio_block", 15.0, "dinero"),
        "precio_cemento": _numero(datos, "precio_cemento", 220.0, "dinero"),
        "precio_arena": _numero(datos, "precio_arena", 600.0, "dinero"),
        "precio_varilla": _numero(datos, "precio_varilla", 120.0, "dinero"),
        "precio_alambre": _numero(datos, "precio_alambre", 35.0, "dinero"),
    }

    resultado = calcular_materiales(largo, alto, precios)
    gasto = largo * alto / 7.0 * pago_peon
    cobro = largo * alto * cobro_m2
    
    # Costo total de la obra = Materiales + Mano de obra cobrada
    costo_total_obra = resultado["costo_total_materiales"] + cobro

    resultado.update({
        "pago_peon_diario": pago_peon,
        "cobro_m2": cobro_m2,
        "cobro_mano_obra": round(cobro, 2),
        "gasto_total_peones": round(gasto, 2),
        "ganancia_neta": round(cobro - gasto, 2),
        "costo_total_obra": round(costo_total_obra, 2),
    })
    return resultado


def calcular_arquitecto(datos):
    resultado = calcular_maestro(datos)
    utilidad_pct = _numero(datos, "pct_utilidad", 15, "porcentaje")
    iva_pct = _numero(datos, "pct_iva", 16, "porcentaje")
    
    subtotal = resultado["costo_total_obra"]
    utilidad = subtotal * utilidad_pct / 100
    base = subtotal + utilidad
    iva = base * iva_pct / 100
    
    resultado.update({
        "subtotal_obra": round(subtotal, 2),
        "pct_utilidad": utilidad_pct,
        "monto_utilidad": round(utilidad, 2),
        "subtotal_mas_utilidad": round(base, 2),
        "pct_iva": iva_pct,
        "monto_iva": round(iva, 2),
        "total_con_iva": round(base + iva, 2),
    })
    return resultado
