# IPC-Argentina
Serie de tiempo del Índice de Precios al Consumidor (IPC) para la República Argentina, promedio índices San Luis, Córdoba, CABA e INDEC (hasta Feb 2007, desde Dic 2016).

## Modo de uso:

Clonar repositorio:

`$ git clone https://github.com/matuteiglesias/IPC-Argentina.git`

O descargarlo como archivo zip. Los datos del índice de precios al consumidor se encuentran en la carpeta `data/info`.

Una vez clonado el repositorio, tiene la opción de correr el archivo `computar_inflacion.py`

`$ cd IPC-Argentina`

`$ python computar_inflacion.py`

Este comando actualiza la información de índices de precios y figuras en su computadora. El repositorio se actualiza diariamente, incorporando nueva información provista para los índices de precios al consumidor de San Luis, Córdoba, CABA y Nacional, en el sistema de almacenamiento de archivos y catálogos de infra.datos.gob.ar.

## Series de tiempo: inflacion mensual

<img src="/figuras/figura2.png" width="800">

## Series de tiempo: cambio de precios último año

<img src="/figuras/figura3.png" width="800">

## Citas

Usar citando este repositorio: *Iglesias, M., IPC-Argentina, (2021), GitHub repository, https://github.com/matuteiglesias/IPC-Argentina*.

La metodología se basa en lo sugerido por *Zack, G., Schteingart, D., & Favata, F. Pobreza e indigencia en Argentina: construcción de una serie completa y metodológicamente homogénea. Sociedad y Economía. https://doi.org/10.25100/SYE.V0I40.7990*


# Construcción de un Índice de Precios al Consumidor

Este proyecto consolida series provinciales y nacionales de índices de precios al consumidor (IPC) para construir un índice promedio, robusto y continuo, que permite estimar la inflación mensual y anual en Argentina desde el año 2000 hasta el presente.

## 1. Fuentes de Datos

Las series utilizadas provienen de fuentes oficiales y provinciales:

* **INDEC (serie histórica)**: hasta 2007.
* **INDEC (serie moderna)**: desde 2016, base diciembre 2016.
* **IPC de la Ciudad de Buenos Aires (CABA)**.
* **IPC de la Provincia de Córdoba**.
* **IPC de la Provincia de San Luis**.

Cada serie es descargada y procesada para obtener una columna con fechas como índice y valores numéricos representando el nivel del índice.

## 2. Metodología de Construcción del Índice Promedio

- Concatenación

Las series se concatenan horizontalmente usando `pandas.concat`, alineadas por fecha.

- Variación Porcentual Mensual Promedio

Se calcula la variación porcentual mensual de cada serie y se promedia entre columnas disponibles en cada mes (ignorando valores cero o `NaN`).

- Transformación Logarítmica

Para permitir comparabilidad entre series con diferentes bases, se aplica logaritmo base 10 sobre cada serie.

- Alineación mediante Offset

Se alinean las series ajustando un offset aditivo entre ellas. El objetivo es reducir saltos artificiales y permitir una unión suave.

- Promedio Logarítmico

Se obtiene un índice unificado mediante el promedio horizontal de todas las series ya alineadas.

- Normalización

El índice resultante se normaliza para que tome el valor 100 en enero de 2016.

## 3. Interpolación y Proyección

* Se proyectan **6 meses hacia adelante** utilizando el promedio reciente de variaciones logarítmicas.
* Se genera una versión **diaria** del índice usando interpolación cuadrática.
* Se construye una versión **trimestral** mediante promedio agrupado por trimestre.

## 4. Exportación y Visualización

* Se exportan los índices diarios (`indice_precios_d.csv`), mensuales (`indice_precios_M.csv`) y trimestrales (`indice_precios_Q.csv`).
* Se generan figuras:

  * Inflación mensual con comparación entre series y promedio.
  * Inflación anual acumulada (rolling de 365 días) con eventos históricos destacados.

## 5. Propósito del Proyecto

Este índice:

* Provee una estimación robusta de la inflación argentina desde 2000.
* Mitiga sesgos o manipulaciones en fuentes oficiales al combinar múltiples jurisdicciones.
* Permite continuidad temporal y proyecciones razonables.
* Sirve como insumo para modelos económicos, análisis sociales y comparaciones intertemporales.

