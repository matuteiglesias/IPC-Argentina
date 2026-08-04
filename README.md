# IPC Argentina — índice compuesto de precios

Serie analítica que enlaza índices de precios provinciales y nacionales para construir una trayectoria mensual comparable desde 2000.

> **Estado:** mantenimiento. El último cambio automático visible en los artefactos es del 15 de julio de 2025. Este repositorio no debe interpretarse como una fuente actualizada a 2026.

## Resultado principal

Los productos derivados se encuentran en `data/info/`:

- `indice_precios_M.csv`: índice y variación mensual;
- `indice_precios_d.csv`: interpolación diaria del índice;
- `indice_precios_Q.csv`: agregación trimestral;
- `figuras/`: visualizaciones derivadas.

El archivo mensual actualmente versionado contiene valores hasta diciembre de 2025. Las filas de agosto a diciembre repiten la misma tasa mensual y corresponden al mecanismo de proyección descrito por el proyecto; **no son observaciones oficiales mensuales**. La fecha exacta de corte de los insumos observados debe verificarse antes de utilizar la serie.

## Fuentes y construcción

La serie combina, según disponibilidad temporal:

- INDEC histórico, hasta 2007;
- INDEC moderno, desde diciembre de 2016;
- IPC de CABA;
- IPC de Córdoba;
- IPC de San Luis.

El pipeline alinea las series por fecha, calcula variaciones mensuales, ajusta diferencias de base en escala logarítmica y construye un índice combinado normalizado a enero de 2016 = 100.

## Uso rápido

Para usar el snapshot comprometido en el repositorio:

```python
import pandas as pd

ipc = pd.read_csv(
    "data/info/indice_precios_M.csv",
    parse_dates=[0],
    index_col=0,
)
print(ipc.tail())
```

Para intentar regenerar los datos y las figuras:

```bash
python computarInflacion.py
```

La regeneración depende de fuentes externas y de un entorno Python que no fue revalidado en esta actualización del README.

## Verificación de frescura

El estado declarado del snapshot vive en [`DATA_STATUS.json`](DATA_STATUS.json). Se puede comprobar sin acceso a red con:

```bash
python scripts/verify_snapshot.py
```

La verificación confirma el corte del archivo comprometido y la frontera entre observaciones y meses proyectados. **No prueba** que las fuentes externas sigan disponibles ni que el workflow diario esté funcionando.

Una regeneración válida debe actualizar primero `DATA_STATUS.json` con evidencia del nuevo corte observado y de la ejecución exitosa.

## Interpretación correcta

Esta serie es un **artefacto analítico**, no el IPC oficial de una jurisdicción. Antes de utilizarla:

1. separar períodos observados de períodos proyectados;
2. verificar la disponibilidad y metodología de cada fuente;
3. revisar cambios de base y cobertura;
4. registrar el commit y el archivo exactos utilizados.

La versión diaria es una interpolación de observaciones mensuales; no representa relevamientos diarios.

## Alcance de mantenimiento

Una revisión anual debería comprobar fuentes, fecha de corte, ejecución del pipeline y coherencia entre CSV y figuras. Hasta completar esa revisión, citar la serie como snapshot versionado y no como indicador corriente.

## Contratos de linaje

La [lista de familias de productos](docs/PRICE_PRODUCT_FAMILIES.md) separa fuentes observadas, compuestos, interpolaciones y proyecciones. El [grafo de transformación](contracts/price-transformation-graph.json), el [contrato de release](docs/PRICE_RELEASE_CONTRACT.md), la [investigación monetaria EPH](docs/EPH_MONETARY_REFERENCE_INVESTIGATION.md) y las [decisiones pendientes](docs/PRICE_METHOD_DECISIONS_REQUIRED.md) son evidencia de preparación: no cambian la serie ni garantizan datos recientes.

## Cita

> Iglesias, M. (2021–). *IPC-Argentina*. Repositorio de GitHub.

La metodología se inspira en Zack, Schteingart y Favata, “Pobreza e indigencia en Argentina: construcción de una serie completa y metodológicamente homogénea”.
