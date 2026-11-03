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
        self.assertEqual(r["subtotal_mo"], 9500)
        self.assertEqual(r["monto_utilidad"], 1425)
        self.assertEqual(r["monto_iva"], 1748)
        self.assertEqual(r["total_con_iva"], 12673)
        self.assertEqual(r["ganancia_neta"], round(9500 - 25 / 7 * 400, 2))

    def test_rechaza_entradas_invalidas(self):
        for datos in ({"largo": -1}, {"alto": "abc"}, {"pago_peon": "nan"}, {"pct_iva": 101}):
            with self.subTest(datos=datos), self.assertRaises(ValueError):
                calcular_arquitecto(datos)


if __name__ == "__main__":
    unittest.main()
