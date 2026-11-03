"""Generación de Excel (.xlsx) para las dos versiones."""
import io
from datetime import datetime

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

_AZUL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
_SUB = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
_BORDE = Border(*(Side(style="thin"),) * 4)
_SECCIONES = {"CONCEPTO", "MATERIALES REQUERIDOS", "TIEMPO Y MANO DE OBRA", "MANO DE OBRA Y COSTOS", "RESUMEN FINANCIERO"}


def _mxn(valor):
    return f"${valor:,.2f}"


def _materiales(d):
    return [
        ["MATERIALES REQUERIDOS", "", "", ""],
        ["Block 12x20x40 (incluye 5% merma)", d["piezas_block"], "Pzas", ""],
        ["Cemento gris 50 kg", d["sacos_cemento"], "Sacos", ""],
        ["Arena de mina", d["m3_arena"], "m³", ""],
        ["Varilla 3/8 (tramo 6 m)", d["tramos_varilla"], "Tramos", ""],
        ["Alambre recocido", d["kg_alambre"], "kg", ""],
    ]


def _filas(d, version):
    filas = [["CONCEPTO", "CANTIDAD", "UNIDAD", "IMPORTE"], ["Área total de muro", d["area_m2"], "m²", ""]]
    filas += _materiales(d)
    filas += [
        ["MANO DE OBRA Y COSTOS", "", "", ""],
        ["Días estimados", d["dias_trabajo"], "Días", ""],
        ["Pago diario peón", _mxn(d["pago_peon_diario"]), "MXN/día", _mxn(d["gasto_total_peones"])],
        ["Cobro mano de obra", f"{_mxn(d['cobro_m2'])} x m²", "MXN", _mxn(d["cobro_mano_obra"])],
    ]
    if version == "arquitecto":
        filas += [
            ["RESUMEN FINANCIERO", "", "", ""],
            ["Subtotal mano de obra", "", "", _mxn(d["subtotal_mo"])],
            [f"Utilidad ({d['pct_utilidad']:g}%)", "", "", _mxn(d["monto_utilidad"])],
            ["Subtotal + utilidad", "", "", _mxn(d["subtotal_mas_utilidad"])],
            [f"IVA ({d['pct_iva']:g}%) - separado", "", "", _mxn(d["monto_iva"])],
            ["TOTAL CON IVA", "", "", _mxn(d["total_con_iva"])],
        ]
    filas.append(["GANANCIA NETA ESTIMADA (sin IVA)", "", "MXN", _mxn(d["ganancia_neta"])])
    return filas


def generar_excel(datos, version, meta=None):
    """Devuelve los bytes del .xlsx. `meta`: cliente, obra, elaboro, folio (arquitecto)."""
    meta = meta or {}
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Presupuesto"
    ws.merge_cells("A1:D1")
    if version == "arquitecto":
        ws["A1"] = f"PRESUPUESTO DE OBRA - {str(meta.get('cliente') or 'Cliente General').upper()}"
        ws.append(["Obra:", meta.get("obra") or "Barda perimetral", "Fecha:", datetime.now().strftime("%d/%m/%Y")])
        ws.append(["Elaboró:", meta.get("elaboro") or "", "Folio:", meta.get("folio") or ""])
        ws.append([])
    else:
        ws["A1"] = "PRESUPUESTO DETALLADO DE EDIFICACIÓN"
    ws["A1"].font = Font(name="Calibri", size=14, bold=True, color="1F4E79")
    ws["A1"].alignment = Alignment(horizontal="center")

    inicio = ws.max_row + 1
    for fila in _filas(datos, version):
        ws.append(fila)
    for r in range(inicio, ws.max_row + 1):
        concepto = ws.cell(row=r, column=1).value
        for c in range(1, 5):
            celda = ws.cell(row=r, column=c)
            celda.border = _BORDE
            if concepto in _SECCIONES:
                celda.fill = _AZUL if concepto == "CONCEPTO" else _SUB
                celda.font = Font(bold=True, color="FFFFFF" if concepto == "CONCEPTO" else "000000")
            elif str(concepto).startswith(("TOTAL", "GANANCIA")):
                celda.font = Font(bold=True, color="006100")
    for col, ancho in zip("ABCD", (38, 18, 15, 22)):
        ws.column_dimensions[col].width = ancho
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
