import numpy as np
import json
import os
import time
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# =================================================================
# 1. NÚCLEO NATIVO NVNB G4.3 (INT8)
# =================================================================
DTYPE_INT = np.int8
BASE_THRESHOLD = 1.0

class NVNB_HabitosObra:
    """Nodo Neuromórfico NVNB reducido para aprendizaje de hábitos en obra."""
    def __init__(self, depth=500):
        self.depth = depth
        self.file_weights = "nvnb_obras_mtj.npy"
        self.file_mapa = "nvnb_obras_mapa.json"
        
        self.mapa_vocal, self.mapa_inverso = self._cargar_mapa()
        self.W_rrv = self._cargar_pesos()

    def _cargar_mapa(self):
        if os.path.exists(self.file_mapa):
            try:
                with open(self.file_mapa, 'r', encoding='utf-8') as f:
                    mapa = json.load(f)
                return mapa, {int(v): k for k, v in mapa.items()}
            except: pass
        return {"<NULL>": 0}, {0: "<NULL>"}

    def _cargar_pesos(self):
        if os.path.exists(self.file_weights):
            try:
                pesos = np.load(self.file_weights)
                if pesos.shape == (3, self.depth, self.depth):
                    return [pesos[i] for i in range(3)]
            except: pass
        return [np.zeros((self.depth, self.depth), dtype=DTYPE_INT) for _ in range(3)]

    def aprender_asociacion(self, clave, valor_str):
        """Aprende secuencias clave->valor (ej: 'peon' -> '400')"""
        tokens = [clave.lower(), valor_str.lower()]
        for token in tokens:
            if token not in self.mapa_vocal:
                # Verificación de límite de profundidad para evitar colapso
                if len(self.mapa_vocal) >= self.depth:
                    print(f"[NVNB Aviso] Capacidad máxima alcanzada ({self.depth} tokens). Token omitido: {token}")
                    return
                
                # Búsqueda segura del primer índice libre
                idx = None
                for i in range(1, self.depth):
                    if i not in self.mapa_inverso:
                        idx = i
                        break
                
                if idx is not None:
                    self.mapa_vocal[token] = idx
                    self.mapa_inverso[idx] = token
                else:
                    return
        
        idx_pre = self.mapa_vocal[tokens[0]]
        idx_act = self.mapa_vocal[tokens[1]]
        
        # Incremento directo sináptico int8
        for W in self.W_rrv:
            if W[idx_pre, idx_act] < 127:  # Límite superior para int8
                W[idx_pre, idx_act] += 1

    def predecir_habito(self, clave):
        """Inferencia rápida usando la fila activa (Zero-Skipping)"""
        idx = self.mapa_vocal.get(clave.lower(), 0)
        if idx == 0:
            return None
        
        # Zero-Skipping: Solo evaluamos la fila de la palabra clave
        votos = np.zeros(self.depth, dtype=int)
        for W in self.W_rrv:
            votos += W[idx, :]
        
        best_idx = np.argmax(votos)
        if votos[best_idx] > 0:
            return self.mapa_inverso.get(best_idx)
        return None

    def guardar(self):
        np.save(self.file_weights, np.array(self.W_rrv, dtype=DTYPE_INT))
        with open(self.file_mapa, 'w', encoding='utf-8') as f:
            json.dump(self.mapa_vocal, f, ensure_ascii=False, indent=4)

# =================================================================
# 2. MOTOR LÓGICO Y GENERADOR DE HOJA DE CÁLCULO (EXCEL)
# =================================================================

def generar_excel_presupuesto(datos_calculados, nombre_archivo="Presupuesto_Barda.xlsx"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Presupuesto de Obra"
    
    # Estilos visuales
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    sub_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    bold_font = Font(name="Calibri", size=11, bold=True)
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                         top=Side(style='thin'), bottom=Side(style='thin'))

    # Encabezado principal
    ws.merge_cells("A1:D1")
    ws["A1"] = "PRESUPUESTO DETALLADO DE EDIFICACIÓN"
    ws["A1"].font = Font(name="Calibri", size=14, bold=True, color="1F4E79")
    ws["A1"].alignment = Alignment(horizontal="center")

    # Filas de datos
    filas = [
        ["CONCEPTO", "CANTIDAD", "UNIDAD", "ESTIMACIÓN"],
        ["Área total de muro", datos_calculados["area_m2"], "m²", "-"],
        ["MATERIALES REQUERIDOS", "", "", ""],
        ["Block (12x20x40 cm)", datos_calculados["piezas_block"], "Piezas", "Incluye 5% merma"],
        ["Cemento Gris", datos_calculados["sacos_cemento"], "Sacos (50kg)", "Mezcla mortero + colado"],
        ["Arena de mina", datos_calculados["m3_arena"], "m³", "Asentado y junteo"],
        ["Varilla de 3/8\"", datos_calculados["tramos_varilla"], "Tramos (6m)", "Castillos a 2.5m"],
        ["Alambre recocido", datos_calculados["kg_alambre"], "kg", "Amarres estructurales"],
        ["TIEMPO Y MANO DE OBRA", "", "", ""],
        ["Días estimados de trabajo", datos_calculados["dias_trabajo"], "Días hábiles", "Cuadrilla estándar"],
        ["Costo diario peón/apoyo", datos_calculados["pago_peon_diario"], "MXN", "Pago aprendido por NVNB"],
        ["Cobro total mano de obra", datos_calculados["cobro_mano_obra"], "MXN", "Precio por m²"],
        ["Gasto total peones", datos_calculados["gasto_total_peones"], "MXN", "Costo operativo"],
        ["GANANCIA NETA ESTIMADA", datos_calculados["ganancia_neta"], "MXN", "Utilidad del maestro"]
    ]

    for r_idx, fila in enumerate(filas, start=3):
        ws.append(fila)
        if fila[0] in ["CONCEPTO", "MATERIALES REQUERIDOS", "TIEMPO Y MANO DE OBRA"]:
            for col_idx in range(1, 5):
                cell = ws.cell(row=r_idx, column=col_idx)
                cell.font = header_font if fila[0] == "CONCEPTO" else bold_font
                cell.fill = header_fill if fila[0] == "CONCEPTO" else sub_fill
        else:
            for col_idx in range(1, 5):
                cell = ws.cell(row=r_idx, column=col_idx)
                cell.border = thin_border
                if col_idx == 2 and isinstance(cell.value, (int, float)):
                    cell.number_format = '#,##0.00'

    # Destacar ganancia neta
    ultima_fila = ws.max_row
    ws.cell(row=ultima_fila, column=1).font = bold_font
    ws.cell(row=ultima_fila, column=2).font = Font(name="Calibri", size=12, bold=True, color="006100")

    # Ajuste de anchura de columnas
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 25

    wb.save(nombre_archivo)
    return nombre_archivo

# =================================================================
# 3. ORQUESTADOR PRINCIPAL (INTERFAZ DE USUARIO)
# =================================================================

def ejecutar_asistente():
    nvnb = NVNB_HabitosObra()
    
    print("=========================================================")
    print("   ASISTENTE DE PRESUPUESTOS + MOTOR NVNB G4.3 (OFFLINE)")
    print("=========================================================")
    
    # 1. Recuperar hábitos aprendidos mediante NVNB
    peon_sugerido = nvnb.predecir_habito("peon") or "350"
    m2_sugerido = nvnb.predecir_habito("costo_m2") or "300"
    
    print(f"\n[NVNB G4.3 Memory] Hábitos detectados del usuario:")
    print(f" -> Pago diario a peón habitual: ${peon_sugerido} MXN")
    print(f" -> Cobro habitual por m²: ${m2_sugerido} MXN")
    
    # 2. Captura de datos para el presupuesto
    print("\n--- INGRESA LOS DATOS DE LA BARDA ---")
    m_largos = float(input("Metros de largo de la barda: ") or "10.0")
    alto = float(input("Altura de la barda (metros): ") or "2.0")
    
    peon_str = input(f"Pago diario al peón [Enter para usar sugerido ${peon_sugerido}]: ").strip()
    if not peon_str: peon_str = peon_sugerido
    
    m2_str = input(f"Cobro mano de obra por m² [Enter para usar sugerido ${m2_sugerido}]: ").strip()
    if not m2_str: m2_str = m2_sugerido

    # 3. Aprendizaje NVNB en tiempo real
    nvnb.aprender_asociacion("peon", peon_str)
    nvnb.aprender_asociacion("costo_m2", m2_str)
    nvnb.guardar()
    print("[NVNB G4.3] Pesos MTJ actualizados con tus preferencias.")

    # 4. Cálculo matemático exacto
    area_m2 = m_largos * alto
    piezas_block = area_m2 * 12.5 * 1.05  # 5% desperdicio
    sacos_cemento = area_m2 * 0.22
    m3_arena = area_m2 * 0.025
    
    num_castillos = int(m_largos / 2.5) + 1
    metros_varilla = num_castillos * (alto + 0.5) * 4
    tramos_varilla = metros_varilla / 6.0
    kg_alambre = tramos_varilla * 0.5
    
    dias_trabajo = area_m2 / 7.0  # Rendimiento aprox: 7 m2 por día
    costo_peon = float(peon_str)
    cobro_m2 = float(m2_str)
    
    gasto_total_peones = dias_trabajo * costo_peon
    cobro_mano_obra = area_m2 * cobro_m2
    ganancia_neta = cobro_mano_obra - gasto_total_peones

    datos = {
        "area_m2": round(area_m2, 2),
        "piezas_block": round(piezas_block),
        "sacos_cemento": round(sacos_cemento, 1),
        "m3_arena": round(m3_arena, 2),
        "tramos_varilla": round(tramos_varilla, 1),
        "kg_alambre": round(kg_alambre, 1),
        "dias_trabajo": round(dias_trabajo, 1),
        "pago_peon_diario": costo_peon,
        "cobro_mano_obra": round(cobro_mano_obra, 2),
        "gasto_total_peones": round(gasto_total_peones, 2),
        "ganancia_neta": round(ganancia_neta, 2)
    }

    # 5. Generar Excel
    t0 = time.perf_counter_ns()
    archivo_creado = generar_excel_presupuesto(datos)
    t1 = time.perf_counter_ns()

    print("\n=========================================================")
    print(f" PRESUPUESTO GENERADO EN EXCEL: {archivo_creado}")
    print(f" Tiempo de generación: {(t1 - t0) / 1e6:.2f} ms")
    print("=========================================================")
    print(f" Área Total: {area_m2:.2f} m² | Días de obra: {dias_trabajo:.1f}")
    print(f" Ganancia Neta para ti: ${ganancia_neta:,.2f} MXN")
    print("=========================================================")

if __name__ == "__main__":
    ejecutar_asistente()
