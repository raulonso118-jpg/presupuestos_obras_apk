import unittest

from motor_calculo import calcular_arquitecto, calcular_maestro


class MotorCalculoTests(unittest.TestCase):
    def test_maestro_usa_formulas_del_prototipo(self):
        r = calcular_maestro({"largo": "10", "alto": "2", "pago_peon": "350", "cobro_m2": "300"})
        self.assertEqual(r["area_m2"], 20)
        self.assertEqual(r["piezas_block"], 262)
        self.assertEqual(r["sacos_cemento"], 4.4)
        self.assertEqual(r["cobro_mano_obra"], 6000)
        self.assertEqual(r["ganancia_neta"], round(6000 - 20 / 7 * 350, 2))

    def test_arquitecto_desglosa_utilidad_e_iva(self):
        r = calcular_arquitecto({"largo": 10, "alto": 2.5, "pago_peon": 400, "cobro_m2": 380})
        self.assertEqual(r["subtotal_obra"], r["costo_total_materiales"] + 9500)
        self.assertEqual(r["monto_utilidad"], round(r["subtotal_obra"] * 0.15, 2))
        self.assertEqual(r["monto_iva"], round(r["subtotal_mas_utilidad"] * 0.16, 2))
        self.assertEqual(r["total_con_iva"], round(r["subtotal_mas_utilidad"] + r["monto_iva"], 2))
        self.assertEqual(r["ganancia_neta"], round(9500 - 25 / 7 * 400, 2))

    def test_precios_unitarios_editables_cambian_costo_materiales(self):
        precios = {
            "precio_block": 20,
            "precio_cemento": 300,
            "precio_arena": 800,
            "precio_varilla": 150,
            "precio_alambre": 50,
        }
        r = calcular_maestro({"largo": 10, "alto": 2, **precios})
        self.assertEqual(r["costo_block"], r["piezas_block"] * 20)
        self.assertEqual(r["costo_total_materiales"], sum(
            r[k] for k in ("costo_block", "costo_cemento", "costo_arena", "costo_varilla", "costo_alambre")
        ))

    def test_rechaza_entradas_invalidas(self):
        for datos in ({"largo": -1}, {"alto": "abc"}, {"pago_peon": "nan"}, {"pct_iva": 101}):
            with self.subTest(datos=datos), self.assertRaises(ValueError):
                calcular_arquitecto(datos)


if __name__ == "__main__":
    unittest.main()
