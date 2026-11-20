# Detección de credential stuffing distribuido (demo local)

Una aplicación de curso para **un solo PC**. El login verifica cuentas ficticias con Argon2id. El simulador genera directamente eventos virtuales; no hace solicitudes al login ni ensaya contraseñas. Sus orígenes se muestran como IPv4 ficticias: `192.0.2.1` a `192.0.2.24` para actividad normal, `192.0.2.200` para el origen legítimo compartido y `198.51.100.1` a `198.51.100.6` para la actividad distribuida. La elección de origen para cada evento es aleatoria, pero reproducible con las semillas documentadas; una misma dirección identifica al mismo origen dentro de cada corrida. Ninguna dirección recibe tráfico.

## Ejecutar en Linux

Desde esta carpeta:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm ci --prefix frontend
npm run build --prefix frontend
.venv/bin/python demo.py
.venv/bin/python app.py
```

La instalación de npm y la compilación se hacen una vez, o después de modificar `frontend/`. El día de la exposición basta con `.venv/bin/python demo.py` para regenerar datos cuando quieras y `.venv/bin/python app.py` para arrancar la aplicación completa. **No hace falta `npm run dev` ni un segundo servidor.** Flask sirve los archivos compilados de `static/ui/`.
Si ya tienes `app.py` abierto en otra terminal, detén esa instancia y vuelve a iniciarla para cargar los cambios de Python.

Abre **http://127.0.0.1:5000/**. Cuenta de demostración: `usuario_01` / `ClaveDemo2026!`. Prueba también una contraseña errónea. Abre **http://127.0.0.1:5000/resultados** para ver el monitor. Para repetir la demo usa `.venv/bin/python demo.py`; conserva los intentos manuales y reemplaza solo la última simulación.

El monitor muestra tres tarjetas calculadas desde la fila de Isolation Forest en `resultados/metricas.csv`: intentos evaluados = TP + FP + TN + FN, alertas = TP + FP y falsas alertas = FP. La tabla separa intentos manuales y eventos sintéticos, permite filtrar alertas y paginar. Al seleccionar una fila, el círculo muestra su decisión guardada; un intento sin puntaje aparece como «Sin evaluar». El puntaje es de anomalía, no un porcentaje de fraude. Flask entrega a React solo los campos necesarios mediante JSON escapado en la plantilla. No se envían contraseñas ni hashes al frontend.

Los CSV `resultados/predicciones.csv` y `resultados/metricas.csv` y la figura `resultados/matriz_confusion.png` se generan con la demo. La base `demo.sqlite3` y el modelo local `resultados/modelo.pkl` se generan también. El historial de intentos no guarda contraseñas, hashes de autenticación, cookies ni cuerpos de solicitudes; la tabla `users` sí guarda hashes Argon2id. El servidor escucha solo en 127.0.0.1 y arranca sin depuración.

## Método

Cada fila tiene hora virtual, cuenta ficticia, origen lógico y resultado simulado. En cada corrida, las características de un evento usan solo intentos previos de los últimos cinco minutos: intentos del origen, cuentas distintas del origen, orígenes distintos de la cuenta, fracción de fallos de la cuenta y otros orígenes que comparten cuentas ya visitadas por el origen. El intento actual se incorpora después del cálculo. El login manual usa el mismo extractor y modelo, con `localhost` como único origen. Sin `modelo.pkl`, el login sigue funcionando y muestra «Sin modelo».

Isolation Forest (`random_state=42`, 150 árboles) se entrena con corridas legítimas de semillas **110–114**. El umbral es el percentil 95 de los puntajes de corridas legítimas separadas, semillas **210–211**. Un puntaje mayor significa más anomalía, no probabilidad de ataque. El contador de referencia alerta si los fallos previos del origen superan **2**; este umbral es el techo del percentil 95 de los conteos de validación. La evaluación usa corridas nuevas con semillas **310–312**, sin ajustar umbrales. La etiqueta real se usa solo al evaluar.

El generador mezcla actividad legítima durante el episodio sospechoso. Incluye un origen legítimo compartido por varias cuentas, errores de digitación y éxitos posteriores posibles, además de seis orígenes sospechosos con cuentas parcialmente compartidas. Todos los intentos de esos seis orígenes reciben etiqueta sospechosa para medir la detección, incluso cuando la verificación simulada resulta aceptada. Es una simplificación conocida del experimento.

## Resultados observados

La ejecución inicial evaluó **1.260 eventos** (300 sospechosos, 960 legítimos):

| Método | TP | FP | TN | FN | Precisión | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Contador por origen | 197 | 48 | 912 | 103 | 0,804 | 0,657 | 0,723 |
| Isolation Forest | 206 | 184 | 776 | 94 | 0,528 | 0,687 | 0,597 |

El bosque encontró 9 sospechosos más que el contador, pero produjo 136 falsas alertas más. Aquí el contador tiene mejor precisión y F1. El CSV conserva cada predicción para explicar aciertos y errores concretos. Las cifras de «orígenes previos sobre la cuenta» y «otros orígenes con cuentas en común» en la página son contexto observado, no una explicación causal exacta del bosque.

## Pruebas y guion de tres minutos

```bash
.venv/bin/python -m unittest discover -s tests -v
npm test --prefix frontend
```

1. Ejecuta `.venv/bin/python demo.py` y señala los dos métodos, los umbrales y los conteos de la terminal.
2. Ejecuta `.venv/bin/python app.py`; en el navegador entra como `usuario_01`, primero con la contraseña correcta y luego con una errónea. Muestra en `/resultados` que ambos intentos están registrados y no aparece la contraseña.
3. En `/resultados`, cambia a «Última simulación», activa «Solo alertas» y selecciona una fila. El círculo muestra la decisión de esa fila; debajo aparecen el puntaje, el umbral de esa simulación y dos observaciones previas. Al final están la comparación y la matriz. Abre `resultados/predicciones.csv` para señalar un falso positivo (`real=0`, `alerta_bosque=1`) o un falso negativo (`real=1`, `alerta_bosque=0`). Explica que el bosque recuperó más sospechosos, a costa de muchas alertas falsas.

El sistema solo **observa y alerta**. La aceptación del login depende de la contraseña, nunca del puntaje. Los intentos distribuidos y sus verificaciones son datos artificiales; no existe tráfico de ataque ni bloqueo automático.
