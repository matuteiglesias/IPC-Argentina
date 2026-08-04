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
python computar_inflacion.py
```

La regeneración depende de fuentes externas y de un entorno Python que no fue revalidado en esta actualización del README.

## Interpretación correcta

Esta serie es un **artefacto analítico**, no el IPC oficial de una jurisdicción. Antes de utilizarla:

1. separar períodos observados de períodos proyectados;
2. verificar la disponibilidad y metodología de cada fuente;
3. revisar cambios de base y cobertura;
4. registrar el commit y el archivo exactos utilizados.

La versión diaria es una interpolación de observaciones mensuales; no representa relevamientos diarios.

## Alcance de mantenimiento

Una revisión anual debería comprobar fuentes, fecha de corte, ejecución del pipeline y coherencia entre CSV y figuras. Hasta completar esa revisión, citar la serie como snapshot versionado y no como indicador corriente.

## Cita

> Iglesias, M. (2021–). *IPC-Argentina*. Repositorio de GitHub.

La metodología se inspira en Zack, Schteingart y Favata, “Pobreza e indigencia en Argentina: construcción de una serie completa y metodológicamente homogénea”.
