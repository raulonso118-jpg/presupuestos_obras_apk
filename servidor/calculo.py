"""Núcleo de cálculo compartido por las versiones Maestro y Arquitecto (barda)."""

LIMITES = {"largo": (0.1, 10000.0), "alto": (0.1, 30.0), "dinero": (0.0, 1_000_000.0), "pct": (0.0, 100.0)}


def _num(datos, clave, defecto, limite):
    crudo = datos.get(clave)
    try:
        valor = float(defecto if crudo in (None, "") else crudo)
    except (TypeError, ValueError):
        raise ValueError(f"Valor numérico inválido en '{clave}'")
    bajo, alto = LIMITES[limite]
    if not bajo <= valor <= alto:
        raise ValueError(f"'{clave}' fuera de rango ({bajo} a {alto})")
    return valor


def calcular_materiales(largo, alto):
    area = largo * alto
    castillos = int(largo / 2.5) + 1
    tramos_varilla = castillos * (alto + 0.5) * 4 / 6.0
    return {
        "area_m2": round(area, 2),
        "piezas_block": round(area * 12.5 * 1.05),
        "sacos_cemento": round(area * 0.22, 1),
        "m3_arena": round(area * 0.025, 2),
        "tramos_varilla": round(tramos_varilla, 1),
        "kg_alambre": round(tramos_varilla * 0.5, 1),
        "dias_trabajo": round(area / 7.0, 1),
    }


def calcular_maestro(datos, peon_defecto=350, m2_defecto=300):
    largo = _num(datos, "largo", 10.0, "largo")
    alto = _num(datos, "alto", 2.0, "alto")
    peon = _num(datos, "pago_peon", peon_defecto, "dinero")
    cobro_m2 = _num(datos, "cobro_m2", m2_defecto, "dinero")
    r = calcular_materiales(largo, alto)
    area = largo * alto
    gasto = (area / 7.0) * peon
    cobro = area * cobro_m2
    r.update(
        pago_peon_diario=peon,
        cobro_m2=cobro_m2,
        cobro_mano_obra=round(cobro, 2),
        gasto_total_peones=round(gasto, 2),
        ganancia_neta=round(cobro - gasto, 2),
    )
    return r


def calcular_arquitecto(datos):
    r = calcular_maestro(datos, peon_defecto=400, m2_defecto=380)
    pct_utilidad = _num(datos, "pct_utilidad", 15, "pct")
    pct_iva = _num(datos, "pct_iva", 16, "pct")
    subtotal = r["cobro_mano_obra"]
    utilidad = subtotal * pct_utilidad / 100
    base = subtotal + utilidad
    iva = base * pct_iva / 100
    r.update(
        subtotal_mo=round(subtotal, 2),
        pct_utilidad=pct_utilidad,
        monto_utilidad=round(utilidad, 2),
        subtotal_mas_utilidad=round(base, 2),
        pct_iva=pct_iva,
        monto_iva=round(iva, 2),
        total_con_iva=round(base + iva, 2),
    )
    return r
