"""Punto de entrada de la app Kivy Presupuestos de Obra."""
import json
import os
from datetime import datetime

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.core.window import Window

from motor_calculo import calcular_arquitecto, calcular_maestro


FONDO = (0.055, 0.075, 0.11, 1)
PANEL = (0.11, 0.15, 0.21, 1)
ACENTO = (0.12, 0.55, 0.84, 1)
TEXTO = (0.94, 0.96, 0.98, 1)


def boton(texto, accion, color=ACENTO, alto=dp(48)):
    b = Button(
        text=texto,
        size_hint_y=None,
        height=alto,
        background_normal="",
        background_color=color,
        color=TEXTO,
        font_size="16sp",
    )
    b.bind(on_release=accion)
    return b


def etiqueta(texto, alto=dp(34), tamano="15sp", color=TEXTO):
    label = Label(
        text=texto,
        size_hint_y=None,
        height=alto,
        color=color,
        font_size=tamano,
        halign="left",
        valign="middle",
        text_size=(None, None),
    )
    label.bind(width=lambda widget, width: setattr(widget, "text_size", (width, widget.height)))
    return label


class PresupuestosApp(App):
    title = "Presupuestos de Obra"

    def build(self):
        Window.clearcolor = FONDO
        self.records_path = os.path.join(self.user_data_dir, "presupuestos.json")
        self.preferences_path = os.path.join(self.user_data_dir, "preferencias.json")
        self.records = self._load_json(self.records_path, [])
        self.preferences = self._load_json(self.preferences_path, {})
        self.version = "maestro"
        self.latest = None
        self.inputs = {}

        self.sm = ScreenManager()
        self.sm.add_widget(self._home_screen())
        self.sm.add_widget(self._form_screen())
        self.sm.add_widget(self._result_screen())
        self.sm.add_widget(self._history_screen())
        return self.sm

    @staticmethod
    def _load_json(path, default):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return default

    @staticmethod
    def _save_json(path, value):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        temp = path + ".tmp"
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
        os.replace(temp, path)

    def _page(self, name):
        screen = Screen(name=name)
        scroll = ScrollView(do_scroll_x=False)
        layout = GridLayout(cols=1, spacing=dp(9), padding=dp(18), size_hint_y=None)
        layout.bind(minimum_height=layout.setter("height"))
        scroll.add_widget(layout)
        screen.add_widget(scroll)
        screen.content = layout
        return screen

    def _home_screen(self):
        screen = self._page("inicio")
        layout = screen.content
        layout.add_widget(etiqueta("PRESUPUESTOS DE OBRA", dp(68), "24sp"))
        layout.add_widget(etiqueta("Prototipo · funciona sin conexión", dp(38), "15sp", (0.72, 0.8, 0.9, 1)))
        layout.add_widget(etiqueta(
            "Calcula materiales, costo total y mano de obra. Guarda tus presupuestos localmente.",
            dp(76), "16sp",
        ))
        layout.add_widget(boton("MAESTRO · sencillo", lambda *_: self.open_form("maestro")))
        layout.add_widget(etiqueta("Cálculo de materiales, precios unitarios y ganancia neta.", dp(58), "14sp", (0.72, 0.8, 0.9, 1)))
        layout.add_widget(boton("ARQUITECTO PRO", lambda *_: self.open_form("arquitecto"), color=(0.16, 0.42, 0.34, 1)))
        layout.add_widget(etiqueta("Incluye utilidad sobre costo total, IVA, cliente y obra.", dp(58), "14sp", (0.72, 0.8, 0.9, 1)))
        layout.add_widget(boton("Presupuestos guardados", self.show_history, color=PANEL))
        layout.add_widget(etiqueta(
            "Las cantidades son estimaciones editables; verifica especificaciones y precios de tu zona.",
            dp(90), "13sp", (0.95, 0.78, 0.44, 1),
        ))
        return screen

    def _form_screen(self):
        screen = self._page("formulario")
        self.form_layout = screen.content
        return screen

    def open_form(self, version):
        self.version = version
        layout = self.form_layout
        layout.clear_widgets()
        nombre = "ARQUITECTO PRO" if version == "arquitecto" else "MAESTRO"
        layout.add_widget(etiqueta(nombre, dp(52), "22sp"))
        
        # Medidas
        layout.add_widget(etiqueta("MEDIDAS DE LA BARDA", dp(32), "15sp", (0.5, 0.76, 0.95, 1)))
        pref = self._best_preferences(version)
        fields = [
            ("largo", "Largo de la barda (m)", "10"),
            ("alto", "Altura (m)", "2.5" if version == "arquitecto" else "2"),
            ("pago_peon", "Pago diario por peón (MXN)", pref.get("pago_peon", "400" if version == "arquitecto" else "350")),
            ("cobro_m2", "Cobro mano de obra por m² (MXN)", pref.get("cobro_m2", "380" if version == "arquitecto" else "300")),
        ]
        
        # Precios unitarios
        layout.add_widget(etiqueta("PRECIOS UNITARIOS DE MATERIALES (MXN)", dp(32), "15sp", (0.5, 0.76, 0.95, 1)))
        fields += [
            ("precio_block", "Precio por pieza de block", "15"),
            ("precio_cemento", "Precio por saco de cemento", "220"),
            ("precio_arena", "Precio por m³ de arena", "600"),
            ("precio_varilla", "Precio por tramo de varilla 3/8", "120"),
            ("precio_alambre", "Precio por kg de alambre recocido", "35"),
        ]

        # Datos extra para versión Arquitecto
        if version == "arquitecto":
            layout.add_widget(etiqueta("DATOS DEL PRESUPUESTO", dp(32), "15sp", (0.5, 0.76, 0.95, 1)))
            fields += [
                ("cliente", "Cliente", ""),
                ("obra", "Nombre de la obra", "Barda perimetral"),
                ("elaboro", "Elaboró", ""),
                ("pct_utilidad", "Utilidad (%)", "15"),
                ("pct_iva", "IVA (%)", "16"),
            ]

        self.inputs = {}
        for key, title, default in fields:
            layout.add_widget(etiqueta(title, dp(28), "14sp"))
            entry = TextInput(
                text=str(default),
                multiline=False,
                size_hint_y=None,
                height=dp(46),
                padding=(dp(10), dp(12)),
                font_size="16sp",
                foreground_color=(0.08, 0.1, 0.14, 1),
                background_color=(0.93, 0.95, 0.97, 1),
            )
            if key not in ("cliente", "obra", "elaboro"):
                entry.input_filter = "float"
            self.inputs[key] = entry
            layout.add_widget(entry)

        layout.add_widget(boton("CALCULAR PRESUPUESTO", self.calculate))
        layout.add_widget(boton("Volver al inicio", lambda *_: setattr(self.sm, "current", "inicio"), color=PANEL))
        self.sm.current = "formulario"

    def _best_preferences(self, version):
        data = self.preferences.get(version, {})
        out = {}
        for key in ("pago_peon", "cobro_m2"):
            choices = data.get(key, {})
            if choices:
                out[key] = max(choices, key=lambda val: (choices[val], float(val)))
        return out

    def calculate(self, *_):
        data = {key: widget.text.strip() for key, widget in self.inputs.items()}
        try:
            calculate = calcular_arquitecto if self.version == "arquitecto" else calcular_maestro
            result = calculate(data)
        except ValueError as exc:
            self._show_message(str(exc))
            return
        self.latest = {
            "version": self.version,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "cliente": data.get("cliente", ""),
            "obra": data.get("obra", ""),
            "resultado": result,
        }
        self._learn_preferences(self.version, result)
        self._save_json(self.preferences_path, self.preferences)
        self._render_result()
        self.sm.current = "resultado"

    def _learn_preferences(self, version, result):
        data = self.preferences.setdefault(version, {})
        for source_key, preference_key in (("pago_peon_diario", "pago_peon"), ("cobro_m2", "cobro_m2")):
            choices = data.setdefault(preference_key, {})
            value = f"{result[source_key]:g}"
            choices[value] = min(127, int(choices.get(value, 0)) + 1)

    def _result_screen(self):
        screen = self._page("resultado")
        self.result_layout = screen.content
        return screen

    def _render_result(self):
        layout = self.result_layout
        layout.clear_widgets()
        result = self.latest["resultado"]
        title = "PRESUPUESTO ARQUITECTO PRO" if self.version == "arquitecto" else "PRESUPUESTO MAESTRO"
        layout.add_widget(etiqueta(title, dp(54), "21sp"))
        if self.latest.get("cliente"):
            layout.add_widget(etiqueta(f"Cliente: {self.latest['cliente']}", dp(32), "15sp"))
        if self.latest.get("obra"):
            layout.add_widget(etiqueta(f"Obra: {self.latest['obra']}", dp(32), "15sp"))
            
        rows = [
            ("Área de muro", f"{result['area_m2']:,.2f} m²"),
            ("Block (incluye 5% merma)", f"{result['piezas_block']:,} pzas ({self._money(result['costo_block'])})"),
            ("Cemento gris", f"{result['sacos_cemento']:,.1f} sacos ({self._money(result['costo_cemento'])})"),
            ("Arena", f"{result['m3_arena']:,.2f} m³ ({self._money(result['costo_arena'])})"),
            ("Varilla 3/8", f"{result['tramos_varilla']:,.1f} tramos ({self._money(result['costo_varilla'])})"),
            ("Alambre recocido", f"{result['kg_alambre']:,.1f} kg ({self._money(result['costo_alambre'])})"),
            ("TOTAL MATERIALES", self._money(result["costo_total_materiales"])),
            ("Días estimados", f"{result['dias_trabajo']:,.1f}"),
            ("Gasto peones (interno)", self._money(result["gasto_total_peones"])),
            ("Cobro mano de obra", self._money(result["cobro_mano_obra"])),
            ("SUBTOTAL (Mat. + M.O.)", self._money(result["costo_total_obra"])),
        ]
        
        if self.version == "arquitecto":
            rows.extend([
                ("Utilidad aplicada", self._money(result["monto_utilidad"])),
                ("IVA (separado)", self._money(result["monto_iva"])),
                ("TOTAL CON IVA", self._money(result["total_con_iva"])),
            ])
        else:
            rows.append(("Ganancia neta estimada", self._money(result["ganancia_neta"])))

        for name, value in rows:
            layout.add_widget(etiqueta(f"{name}:  {value}", dp(34), "15sp"))
            
        layout.add_widget(etiqueta(
            "Estimación orientativa. Confirma rendimientos, estructura, precios locales e impuestos.",
            dp(72), "13sp", (0.95, 0.78, 0.44, 1),
        ))
        layout.add_widget(boton("GUARDAR PRESUPUESTO", self.save_budget, color=(0.16, 0.42, 0.34, 1)))
        layout.add_widget(boton("Nuevo cálculo", lambda *_: self.open_form(self.version)))
        layout.add_widget(boton("Inicio", lambda *_: setattr(self.sm, "current", "inicio"), color=PANEL))

    @staticmethod
    def _money(amount):
        return f"${amount:,.2f} MXN"

    def save_budget(self, *_):
        if not self.latest:
            return
        self.records.insert(0, self.latest)
        self.records = self.records[:100]
        self._save_json(self.records_path, self.records)
        self._show_message("Presupuesto guardado en este dispositivo.")

    def _history_screen(self):
        screen = self._page("historial")
        self.history_layout = screen.content
        return screen

    def show_history(self, *_):
        layout = self.history_layout
        layout.clear_widgets()
        layout.add_widget(etiqueta("PRESUPUESTOS GUARDADOS", dp(52), "21sp"))
        if not self.records:
            layout.add_widget(etiqueta("Todavía no hay presupuestos guardados.", dp(50), "15sp"))
        for record in self.records:
            res = record["resultado"]
            detail = res["total_con_iva"] if record["version"] == "arquitecto" else res["costo_total_obra"]
            title = "ARQUITECTO PRO" if record["version"] == "arquitecto" else "MAESTRO"
            layout.add_widget(etiqueta(
                f"{title} · {record.get('obra') or 'Barda'} · {record['fecha']} · {self._money(detail)}",
                dp(64), "14sp",
            ))
        layout.add_widget(boton("Volver", lambda *_: setattr(self.sm, "current", "inicio"), color=PANEL))
        self.sm.current = "historial"

    def _show_message(self, message):
        from kivy.uix.popup import Popup

        content = GridLayout(cols=1, padding=dp(12), spacing=dp(8))
        content.add_widget(Label(text=message, color=(0.08, 0.1, 0.14, 1)))
        popup = Popup(title="Presupuestos de Obra", content=content, size_hint=(0.85, None), height=dp(190))
        content.add_widget(boton("Entendido", lambda *_: popup.dismiss(), alto=dp(42)))
        popup.open()


if __name__ == "__main__":
    PresupuestosApp().run()
