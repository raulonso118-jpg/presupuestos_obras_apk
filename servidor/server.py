"""Servidor HTTP de Presupuestos de Obra: licencias, pagos Mercado Pago, cálculo, Excel e IA de hábitos."""
import base64
import hashlib
import hmac
import html
import http.server
import json
import os
import secrets
import socketserver
import threading
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import calculo
import db
import excel
import licencias
import pagos_mp

PORT = int(os.environ.get("PORT", 8080))
MAX_BODY = 1 * 1024 * 1024
PAGOS_LOCK = threading.Lock()


def procesar_pago(payment_id, referencia=None):
    """Consulta el pago y, si está aprobado, emite la licencia una sola vez."""
    with PAGOS_LOCK:
        guardado = db.obtener_pago(payment_id)
        if guardado:
            if referencia and guardado["external_reference"] != referencia:
                raise ValueError("La referencia no coincide con el pago")
            return {"status": "approved", **guardado}
        pago = pagos_mp.extraer_data_pago(pagos_mp.obtener_pago(payment_id))
        if referencia and pago["external_reference"] != referencia:
            raise ValueError("La referencia no coincide con el pago")
        if pago["status"] != "approved":
            return {"status": pago["status"]}
        if not str(pago.get("external_reference") or "").startswith("orden_"):
            raise ValueError("El pago no pertenece a una orden de licencia")
        email = pago.get("email") or ""
        lic = licencias.generar_licencia(pago["version"], pago["dias"], email)
        db.guardar_pago(payment_id, pago["external_reference"], email, pago["plan"], pago["version"], pago["dias"], lic["codigo"])
        return {
            "status": "approved", "payment_id": str(payment_id), "external_reference": pago["external_reference"],
            "email": email, "plan": pago["plan"], "version": pago["version"], "dias": pago["dias"], "licencia": lic["codigo"],
        }


def firma_webhook_valida(headers, data_id):
    secreto = os.environ.get("MP_WEBHOOK_SECRET", "").strip()
    if not secreto:
        return True
    firma = headers.get("x-signature", "")
    partes = dict(p.strip().split("=", 1) for p in firma.split(",") if "=" in p)
    manifest = f"id:{str(data_id).lower()};request-id:{headers.get('x-request-id', '')};ts:{partes.get('ts', '')};"
    esperado = hmac.new(secreto.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperado, partes.get("v1", ""))


def pagina_html(titulo, mensaje, licencia=None):
    bloque = f"<p>Tu licencia (guárdala):</p><p style='font-size:24px;font-weight:bold;word-break:break-all'>{html.escape(licencia)}</p>" if licencia else ""
    return (
        "<!doctype html><html lang='es'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(titulo)}</title></head>"
        "<body style='font-family:sans-serif;max-width:480px;margin:40px auto;padding:0 16px'>"
        f"<h1>{html.escape(titulo)}</h1><p>{html.escape(mensaje)}</p>{bloque}</body></html>"
    ).encode("utf-8")


def sugerencias(licencia):
    return {
        "pago_peon": db.habito_mas_frecuente(licencia, "pago_peon"),
        "cobro_m2": db.habito_mas_frecuente(licencia, "cobro_m2"),
    }


def generar_presupuesto(version, datos, licencia):
    """Aplica hábitos aprendidos a los campos omitidos, calcula, genera Excel y aprende."""
    datos = dict(datos)
    sug = sugerencias(licencia)
    for clave in ("pago_peon", "cobro_m2"):
        if datos.get(clave) in (None, "") and sug[clave]:
            datos[clave] = sug[clave]
    calcular = calculo.calcular_arquitecto if version == "arquitecto" else calculo.calcular_maestro
    resultado = calcular(datos)
    meta = {k: str(datos.get(k) or "")[:80] for k in ("cliente", "obra", "elaboro")}
    meta["folio"] = f"OBR-{datetime.now():%y%m%d}-{secrets.token_hex(2).upper()}"
    xlsx = excel.generar_excel(resultado, version, meta)
    # Solo aprende después de un cálculo válido
    db.aprender_habito(licencia, "pago_peon", f"{resultado['pago_peon_diario']:g}")
    db.aprender_habito(licencia, "cobro_m2", f"{resultado['cobro_m2']:g}")
    return {
        "estatus": "ok", "version": version, "folio": meta["folio"], "resultado": resultado,
        "archivo": f"Presupuesto_{version}_{meta['folio']}.xlsx",
        "excel_base64": base64.b64encode(xlsx).decode("ascii"),
    }


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, formato, *args):
        print(f"[{datetime.now().isoformat()}] {self.address_string()} {formato % args}")

    def _json(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(data)

    def _html(self, contenido, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(contenido)))
        self.end_headers()
        self.wfile.write(contenido)

    def do_OPTIONS(self):
        self._json({}, 204)

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        if url.path in ("/", "/health"):
            self._json({"estatus": "ok", "servicio": "presupuestos-obras", "licencias_firmadas": licencias.firma_habilitada()})
        elif url.path == "/pago-exito":
            pid = (q.get("payment_id") or q.get("collection_id") or [""])[0]
            ref = (q.get("external_reference") or [""])[0]
            if not pid or not ref:
                return self._html(pagina_html("Pago", "Faltan datos del pago."), 400)
            try:
                res = procesar_pago(pid, ref)
            except Exception as e:
                print(f"Error en pago-exito: {e}")
                return self._html(pagina_html("Pago", "No pudimos confirmar tu pago. Escríbenos con tu comprobante."), 500)
            if res.get("licencia"):
                self._html(pagina_html("¡Pago aprobado!", "Gracias por tu compra. Ingresa esta licencia en la app.", res["licencia"]))
            else:
                self._html(pagina_html("Pago en proceso", "Tu pago aún no está aprobado. Recarga en unos minutos."))
        elif url.path == "/pago-pendiente":
            self._html(pagina_html("Pago pendiente", "Cuando se acredite tu pago recibirás tu licencia."))
        elif url.path == "/pago-fallo":
            self._html(pagina_html("Pago no completado", "No se realizó el cobro. Puedes intentarlo de nuevo."))
        elif url.path == "/api/planes":
            self._json({"estatus": "ok", "planes": pagos_mp.PLANES})
        else:
            self._json({"estatus": "error", "mensaje": "Ruta no encontrada"}, 404)

    def _licencia(self, datos, version):
        codigo = str(datos.get("licencia", "")).strip().upper()
        ok, msg, dias, ver = licencias.validar(
            codigo, version, datos.get("device_id"), self.client_address[0]
        )
        return ok, msg, dias, ver, codigo

    def do_POST(self):
        try:
            url = urlparse(self.path)
            ruta, q = url.path, parse_qs(url.query)
            largo = int(self.headers.get("Content-Length", "0"))
            webhook = ruta == "/api/pagos/webhook"
            if largo > MAX_BODY or (largo <= 0 and not webhook):
                return self._json({"estatus": "error", "mensaje": "Solicitud vacía o demasiado grande"}, 400)
            raw = self.rfile.read(largo).decode("utf-8") if largo > 0 else ""
            datos = json.loads(raw) if raw.strip() else {}
            if not isinstance(datos, dict):
                raise ValueError("JSON inválido")

            if ruta == "/api/validar_licencia":
                ok, msg, dias, ver, _ = self._licencia(datos, str(datos.get("version") or "maestro"))
                return self._json({"estatus": "ok" if ok else "error", "mensaje": msg, "dias_restantes": dias, "version": ver}, 200 if ok else 403)

            if ruta == "/api/pagos/crear_preferencia":
                return self._json({"estatus": "ok", **pagos_mp.crear_preferencia(datos.get("email", ""), datos.get("plan", ""))})

            if webhook:
                tipo = (q.get("type") or q.get("topic") or [None])[0] or datos.get("type") or datos.get("topic")
                pid = str((q.get("data.id") or q.get("id") or [None])[0] or (datos.get("data") or {}).get("id") or datos.get("id") or "")
                if tipo != "payment" or not pid:
                    return self._json({"estatus": "ok", "mensaje": "Evento ignorado"})
                if not firma_webhook_valida(self.headers, pid):
                    return self._json({"estatus": "error", "mensaje": "Firma inválida"}, 401)
                res = procesar_pago(pid)
                return self._json({"estatus": "ok", "mensaje": "Licencia generada" if res.get("licencia") else f"Pago no aprobado ({res['status']})"})

            if ruta == "/api/pagos/estado_orden":
                pid, ref = str(datos.get("payment_id", "")).strip(), str(datos.get("external_reference", "")).strip()
                if not pid or not ref:
                    return self._json({"estatus": "error", "mensaje": "Faltan payment_id y external_reference"}, 400)
                return self._json({"estatus": "ok", **procesar_pago(pid, ref)})

            if ruta == "/api/pagos/consultar":
                ref = str(datos.get("external_reference", "")).strip()
                if not ref.startswith("orden_"):
                    return self._json({"estatus": "error", "mensaje": "Referencia inválida"}, 400)
                pid = pagos_mp.buscar_pago_aprobado(ref)
                if not pid:
                    return self._json({"estatus": "ok", "mensaje": "Tu pago aún no aparece aprobado. Intenta en un minuto."})
                res = procesar_pago(pid, ref)
                return self._json({"estatus": "ok", "licencia": res.get("licencia"), "plan": res.get("plan"), "version": res.get("version"), "dias": res.get("dias")})

            if ruta == "/api/habitos/sugerir":
                ok, msg, _d, _v, codigo = self._licencia(datos, "maestro")
                if not ok:
                    return self._json({"estatus": "error", "mensaje": msg}, 403)
                return self._json({"estatus": "ok", **sugerencias(codigo)})

            if ruta in ("/api/presupuesto/maestro", "/api/presupuesto/arquitecto"):
                version = ruta.rsplit("/", 1)[1]
                ok, msg, _d, _v, codigo = self._licencia(datos, version)
                if not ok:
                    return self._json({"estatus": "error", "mensaje": msg}, 403)
                return self._json(generar_presupuesto(version, datos, codigo))

            self._json({"estatus": "error", "mensaje": "Endpoint no existe"}, 404)
        except (ValueError, json.JSONDecodeError) as e:
            self._json({"estatus": "error", "mensaje": str(e)}, 400)
        except Exception as e:
            print(f"Error interno: {e}")
            self._json({"estatus": "error", "mensaje": "Error interno del servidor"}, 500)


def main():
    db.init_db()
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    socketserver.ThreadingTCPServer.daemon_threads = True
    with socketserver.ThreadingTCPServer(("", PORT), Handler) as srv:
        print(f"Servidor de presupuestos escuchando en puerto {PORT}")
        srv.serve_forever()


if __name__ == "__main__":
    main()
