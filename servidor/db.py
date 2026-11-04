"""SQLite: licencias, auditoría, pagos idempotentes y hábitos aprendidos (IA)."""
import os
import sqlite3
from contextlib import closing
from datetime import datetime


def _db_path():
    return os.environ.get("DB_PATH", "obras_licencias.db")


def _ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _conn():
    return sqlite3.connect(_db_path(), timeout=15)


def init_db():
    with closing(_conn()) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS licencias (
                codigo TEXT PRIMARY KEY,
                email TEXT,
                version TEXT NOT NULL,
                fecha_inicio TEXT NOT NULL,
                fecha_expiracion TEXT NOT NULL,
                activa INTEGER DEFAULT 1,
                usos INTEGER DEFAULT 0,
                ultima_validacion TEXT
            );
            CREATE TABLE IF NOT EXISTS validaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                licencia TEXT, dispositivo TEXT, resultado TEXT, ip TEXT, fecha TEXT
            );
            CREATE TABLE IF NOT EXISTS pagos (
                payment_id TEXT PRIMARY KEY,
                external_reference TEXT,
                email TEXT, plan TEXT, version TEXT, dias INTEGER,
                licencia TEXT NOT NULL, fecha TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS habitos (
                licencia TEXT NOT NULL,
                clave TEXT NOT NULL,
                valor TEXT NOT NULL,
                veces INTEGER NOT NULL DEFAULT 1,
                actualizado TEXT NOT NULL,
                PRIMARY KEY (licencia, clave, valor)
            );
            """
        )
        conn.commit()


def guardar_licencia(codigo, email, version, inicio, expiracion):
    try:
        with closing(_conn()) as conn:
            conn.execute(
                "INSERT INTO licencias (codigo, email, version, fecha_inicio, fecha_expiracion) "
                "VALUES (?, ?, ?, ?, ?)",
                (codigo, email, version, inicio, expiracion),
            )
            conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error guardando licencia: {e}")
        return False


def licencia_desactivada(codigo):
    """True solo si la licencia existe en BD y fue desactivada manualmente."""
    with closing(_conn()) as conn:
        fila = conn.execute("SELECT activa FROM licencias WHERE codigo = ?", (codigo,)).fetchone()
    return bool(fila) and not fila[0]


def registrar_validacion(codigo, dispositivo, resultado, ip):
    try:
        with closing(_conn()) as conn:
            conn.execute(
                "INSERT INTO validaciones (licencia, dispositivo, resultado, ip, fecha) VALUES (?,?,?,?,?)",
                (codigo, dispositivo, resultado, ip, _ahora()),
            )
            conn.execute(
                "UPDATE licencias SET usos = usos + 1, ultima_validacion = ? WHERE codigo = ?",
                (_ahora(), codigo),
            )
            conn.commit()
    except sqlite3.Error as e:
        print(f"Error registrando validación: {e}")


def obtener_pago(payment_id):
    with closing(_conn()) as conn:
        fila = conn.execute(
            "SELECT payment_id, external_reference, email, plan, version, dias, licencia, fecha "
            "FROM pagos WHERE payment_id = ?",
            (str(payment_id),),
        ).fetchone()
    if not fila:
        return None
    return dict(zip(("payment_id", "external_reference", "email", "plan", "version", "dias", "licencia", "fecha"), fila))


def guardar_pago(payment_id, referencia, email, plan, version, dias, licencia):
    with closing(_conn()) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO pagos (payment_id, external_reference, email, plan, version, dias, licencia, fecha) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (str(payment_id), referencia, email, plan, version, int(dias), licencia, _ahora()),
        )
        conn.commit()


def aprender_habito(licencia, clave, valor):
    with closing(_conn()) as conn:
        conn.execute(
            "INSERT INTO habitos (licencia, clave, valor, veces, actualizado) VALUES (?,?,?,1,?) "
            "ON CONFLICT(licencia, clave, valor) DO UPDATE SET veces = veces + 1, actualizado = excluded.actualizado",
            (licencia, clave, valor, _ahora()),
        )
        conn.commit()


def habito_mas_frecuente(licencia, clave):
    """Valor más repetido; en empate gana el más reciente."""
    with closing(_conn()) as conn:
        fila = conn.execute(
            "SELECT valor FROM habitos WHERE licencia = ? AND clave = ? "
            "ORDER BY veces DESC, actualizado DESC LIMIT 1",
            (licencia, clave),
        ).fetchone()
    return fila[0] if fila else None
