# Presupuestos de Obra

Prototipo Android/Kivy con dos modalidades:

- **Maestro:** cantidades orientativas, mano de obra, costo de peones y ganancia neta.
- **Arquitecto Pro:** lo anterior, más cliente/obra, utilidad e IVA desglosados.

El cálculo es local y funciona sin conexión. Los presupuestos se guardan en el dispositivo. Las sugerencias de pago al peón y cobro por m² cuentan los valores más usados en esa instalación; no son predicciones de una IA entrenada. Las fórmulas de materiales son las del prototipo y deben validarse para cada sistema constructivo y precios locales.

## Probar

```sh
python -m unittest discover -s tests -v
buildozer android debug
```

El workflow de GitHub Actions compila un APK de depuración al subir cambios a una rama `feature/**` o al ejecutarlo manualmente. El APK de depuración no es una versión firmada para distribución.

La integración de licencias y Mercado Pago requiere desplegar el backend de `servidor/` y configurar credenciales; no forma parte del flujo sin conexión de este prototipo.
