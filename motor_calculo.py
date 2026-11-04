"""Cálculo local, determinista y compartido por Maestro y Arquitecto Pro."""
import math


LIMITES = {
    "largo": (0.1, 10000.0),
    "alto": (0.1, 30.0),
    "dinero": (0.0, 1_000_000.0),
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


def calcular_materiales(largo, alto):
    area = largo * alto
    num_castillos = int(largo / 2.5) + 1
    tramos_varilla = num_castillos * (alto + 0.5) * 4 / 6.0
    return {
        "area_m2": round(area, 2),
        "piezas_block": round(area * 12.5 * 1.05),
        "sacos_cemento": round(area * 0.22, 1),
        "m3_arena": round(area * 0.025, 2),
        "tramos_varilla": round(tramos_varilla, 1),
        "kg_alambre": round(tramos_varilla * 0.5, 1),
        "dias_trabajo": round(area / 7.0, 1),
    }


def calcular_maestro(datos):
    largo = _numero(datos, "largo", 10.0, "largo")
    alto = _numero(datos, "alto", 2.0, "alto")
    pago_peon = _numero(datos, "pago_peon", 350, "dinero")
    cobro_m2 = _numero(datos, "cobro_m2", 300, "dinero")
    resultado = calcular_materiales(largo, alto)
    gasto = largo * alto / 7.0 * pago_peon
    cobro = largo * alto * cobro_m2
    resultado.update({
        "pago_peon_diario": pago_peon,
        "cobro_m2": cobro_m2,
        "cobro_mano_obra": round(cobro, 2),
        "gasto_total_peones": round(gasto, 2),
        "ganancia_neta": round(cobro - gasto, 2),
    })
    return resultado


def calcular_arquitecto(datos):
    resultado = calcular_maestro(datos)
    utilidad_pct = _numero(datos, "pct_utilidad", 15, "porcentaje")
    iva_pct = _numero(datos, "pct_iva", 16, "porcentaje")
    subtotal = resultado["cobro_mano_obra"]
    utilidad = subtotal * utilidad_pct / 100
    base = subtotal + utilidad
    iva = base * iva_pct / 100
    resultado.update({
        "subtotal_mo": round(subtotal, 2),
        "pct_utilidad": utilidad_pct,
        "monto_utilidad": round(utilidad, 2),
        "subtotal_mas_utilidad": round(base, 2),
        "pct_iva": iva_pct,
        "monto_iva": round(iva, 2),
        "total_con_iva": round(base + iva, 2),
    })
    return resultado
