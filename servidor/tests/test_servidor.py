"""Pruebas de extremo a extremo (sin Mercado Pago): python -m unittest discover -s tests"""
import base64
import io
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "t.db")
os.environ["LIC_SECRET_SEED"] = "semilla-de-prueba"

import openpyxl  # noqa: E402
import db  # noqa: E402
import licencias  # noqa: E402
import server  # noqa: E402


def post(base, ruta, datos):
    req = urllib.request.Request(base + ruta, json.dumps(datos).encode(), {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


class Pruebas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()
        cls.srv = server.socketserver.ThreadingTCPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        cls.maestro = licencias.generar_licencia("maestro", 30, "m@x.com")["codigo"]
        cls.arq = licencias.generar_licencia("arquitecto", 30, "a@x.com")["codigo"]

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_licencia_valida_alterada_y_expirada(self):
        self.assertEqual(post(self.base, "/api/validar_licencia", {"licencia": self.maestro})[0], 200)
        self.assertEqual(post(self.base, "/api/validar_licencia", {"licencia": self.maestro[:-1] + "0"})[0], 403)
        ayer = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        cuerpo = f"OBRM-{ayer}-ABC123"
        expirada = f"{cuerpo}-{licencias._firmar(cuerpo)}"
        st, r = post(self.base, "/api/validar_licencia", {"licencia": expirada})
        self.assertEqual(st, 403)
        self.assertIn("expirada", r["mensaje"])

    def test_maestro_no_usa_version_arquitecto(self):
        st, _ = post(self.base, "/api/presupuesto/arquitecto", {"licencia": self.maestro})
        self.assertEqual(st, 403)
        self.assertEqual(post(self.base, "/api/presupuesto/maestro", {"licencia": self.arq, "largo": 5, "alto": 2})[0], 200)

    def test_calculo_coincide_con_prototipo(self):
        st, r = post(self.base, "/api/presupuesto/maestro", {"licencia": self.maestro, "largo": 10, "alto": 2, "pago_peon": 350, "cobro_m2": 300})
        self.assertEqual(st, 200)
        res = r["resultado"]
        self.assertEqual((res["area_m2"], res["piezas_block"], res["sacos_cemento"]), (20.0, 262, 4.4))
        self.assertEqual(res["ganancia_neta"], round(6000 - 20 / 7 * 350, 2))
        wb = openpyxl.load_workbook(io.BytesIO(base64.b64decode(r["excel_base64"])))
        self.assertEqual(wb.active.title, "Presupuesto")

    def test_arquitecto_iva(self):
        st, r = post(self.base, "/api/presupuesto/arquitecto", {"licencia": self.arq, "largo": 10, "alto": 2.5, "cliente": "Ana"})
        self.assertEqual(st, 200)
        res = r["resultado"]
        self.assertAlmostEqual(res["total_con_iva"], 25 * 380 * 1.15 * 1.16, places=1)

    def test_datos_invalidos(self):
        self.assertEqual(post(self.base, "/api/presupuesto/maestro", {"licencia": self.maestro, "largo": -3})[0], 400)
        self.assertEqual(post(self.base, "/api/presupuesto/maestro", {"licencia": self.maestro, "largo": "abc"})[0], 400)

    def test_ia_aprende_habitos(self):
        lic = licencias.generar_licencia("maestro", 30, "h@x.com")["codigo"]
        for _ in range(3):
            post(self.base, "/api/presupuesto/maestro", {"licencia": lic, "pago_peon": 450, "cobro_m2": 320})
        post(self.base, "/api/presupuesto/maestro", {"licencia": lic, "pago_peon": 500})
        _, s = post(self.base, "/api/habitos/sugerir", {"licencia": lic})
        self.assertEqual(s["pago_peon"], "450")
        _, r = post(self.base, "/api/presupuesto/maestro", {"licencia": lic, "largo": 4, "alto": 2})
        self.assertEqual(r["resultado"]["pago_peon_diario"], 450)

    def test_sin_semilla_no_emite(self):
        anterior = os.environ["LIC_SECRET_SEED"]
        os.environ["LIC_SECRET_SEED"] = ""
        try:
            with self.assertRaises(RuntimeError):
                licencias.generar_licencia("maestro", 30, "x@x.com")
        finally:
            os.environ["LIC_SECRET_SEED"] = anterior


if __name__ == "__main__":
    unittest.main()
