
import pandas as pd
import numpy as np



## IPC San Luis

# Pagina de estadisticas de San Luis
url = 'https://www.ieric.org.ar/series_estadisticas/san-luis/'

import bs4 as bs
import requests

sauce = requests.get(url)
soup = bs.BeautifulSoup(sauce.content,'html.parser')

for a in soup.find_all('a', href=True):
    if 'IPC-Prov-San-Luis.xlsx' in a['href']:
        url = a['href'] # Resultado
        print("Encontrado el URL:", url)
        
# url = 'https://www.ieric.org.ar/wp-content/uploads/2021/09/IPC-Prov-San-Luis.xlsx'
data = pd.read_excel(url, sheet_name = 'Serie', skiprows=3).dropna(subset = ['Nivel General'])

ipc_SanLuis = data[['Periodo', 'Nivel General']]
ipc_SanLuis.columns = ['indice_tiempo', 'ipc_SanLuis']
ipc_SanLuis.index = pd.to_datetime(ipc_SanLuis['indice_tiempo']);
ipc_SanLuis = ipc_SanLuis[['ipc_SanLuis']].astype(float)

100*ipc_SanLuis.pct_change().tail()

## IPC Cordoba

url = 'https://datosestadistica.cba.gov.ar/dataset/fedc5285-5517-41aa-9095-bb62c6dbc485/resource/2b4a7c60-1c8a-45b1-be8f-2bd59bfe2364/download/ipc-cba-enero-.xlsx'
data = pd.read_excel(url, sheet_name = 'IPC-Cba base 2014', skiprows=5, index_col = [0, 1, 2]
                    ).dropna().T

ipc_Cordoba = data[0]['Código'].reset_index()
ipc_Cordoba.columns = ['indice_tiempo', 'ipc_Cordoba']
ipc_Cordoba.index = pd.to_datetime(ipc_Cordoba['indice_tiempo']);
ipc_Cordoba = ipc_Cordoba[['ipc_Cordoba']].astype(float)

100*ipc_Cordoba.pct_change().tail()

## IPC CABA
url = 'https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2022/02/Principales_aperturas_indices.xlsx'
data = pd.read_excel(url, sheet_name = 'Principales_aperturas_indices', skiprows=2, index_col = [0]
                    ).dropna().T.iloc[:-1]

ipc_CABA = data[['Nivel General']].reset_index()
ipc_CABA.columns = ['indice_tiempo', 'ipc_CABA']
ipc_CABA.index = pd.to_datetime(ipc_CABA['indice_tiempo']);
ipc_CABA = ipc_CABA[['ipc_CABA']].astype(float)

100*ipc_CABA.pct_change().tail()

## IPC Indec 1
url = 'https://www.indec.gob.ar/ftp/nuevaweb/cuadros/10/sh_ipc_2008.xls'
data = pd.read_excel(url, sheet_name = 'Serie Histórica', skiprows=4, index_col = [0, 1]
                    ).dropna(subset = ['Nivel general'])

ipc_INDEC1 = data[['Nivel general']].iloc[:-1].reset_index()

ipc_INDEC1.columns = ['year', 'month', 'ipc_INDEC1']; ipc_INDEC1['day'] = 1
ipc_INDEC1.index = pd.to_datetime(ipc_INDEC1[['year', 'month', 'day']])
ipc_INDEC1['ipc_INDEC1'] = ipc_INDEC1['ipc_INDEC1'].astype(str).str.replace(',', '.')
ipc_INDEC1 = ipc_INDEC1[['ipc_INDEC1']].astype(float)
ipc_INDEC1 = ipc_INDEC1.loc['2000':'2007-02']

100*ipc_INDEC1.pct_change().tail()

## IPC Indec 3
url = 'https://infra.datos.gob.ar/catalog/sspm/dataset/145/distribution/145.3/download/indice-precios-al-consumidor-nivel-general-base-diciembre-2016-mensual.csv'
data = pd.read_csv(url)#.astype(float)

ipc_INDEC3 = data[['indice_tiempo', 'ipc_ng_nacional']]
ipc_INDEC3.columns = ['indice_tiempo', 'ipc_INDEC3'];
ipc_INDEC3.index = pd.to_datetime(ipc_INDEC3['indice_tiempo'], format = '%Y-%m-%d')
ipc_INDEC3 = ipc_INDEC3[['ipc_INDEC3']].astype(float)

100*ipc_INDEC3.pct_change().tail()

## Las series se promedian en cada mes para dar un solo indice:
## Concatenar series:

ipc = pd.concat([ipc_INDEC3, ipc_CABA, ipc_Cordoba, ipc_SanLuis, ipc_INDEC1], axis = 1)
# mean_pct = 100*ipc.pct_change().replace(0, np.nan).mean(1)
mean_pct = 100*ipc.pct_change(fill_method=None).replace(0, np.nan).mean(1)
ipc = np.log10(ipc)

## Offset para alinear los indices de distintas series:
offset = [0]
for i, column in enumerate(ipc.columns[1:]):
    info = ipc.iloc[:, [i + 1, i]].dropna()
    # off = info.diff(1, axis = 1).mean()[1]
    off = info.diff(1, axis = 1).mean().iloc[1]
    offset += [off]
    
offset = np.cumsum(np.array(offset))
ipc_union = ipc + offset


ipc_union_m = pd.DataFrame(ipc_union.mean(1), columns = ['log_index'])
fechanivel100 = ipc_union_m.loc['2016-01'].values
ipc_union_m = ipc_union_m - fechanivel100
ipc_union_m['index'] = 100*10**ipc_union_m.log_index
ipc_union_m['log_index_diff'] = ipc_union_m.log_index.diff(1)
# ipc_union_m['pct_m'] = 100*ipc_union_m['index'].pct_change() # Sensible a ciertos errores numericos
ipc_union_m['pct_m'] = mean_pct


### Completo meses presente


ipc_tail = ipc_union_m.tail(6)
tail_mean = ipc_tail.mean()

# meses_presente = pd.date_range(ipc_union_m.index[-1], 
#               ipc_union_m.index[-1] + pd.DateOffset(months=6), freq = 'M') + pd.DateOffset(days=1)
meses_presente = pd.date_range(ipc_union_m.index[-1],
              ipc_union_m.index[-1] + pd.DateOffset(months=6), freq = 'ME') + pd.DateOffset(days=1)


ipc_union_m_ = ipc_union_m.reindex(ipc_union.index.append(meses_presente))

ipc_union_m_.iloc[-6:, 2] = tail_mean['log_index_diff']
ipc_union_m_.iloc[-6:, 3] = tail_mean['pct_m']

ipc_union_m_.iloc[-6:, 0] = ipc_union_m['log_index'].values[-1] + ipc_union_m_.tail(6)['log_index_diff'].cumsum().values
ipc_union_m_.iloc[-6:, 1] = ipc_union_m['index'].values[-1] * (1 + ipc_union_m_.tail(6)['pct_m']/100).cumprod().values

ipc_union_m_.tail(10)


### Resampleo a frecuencia diaria y a frecuencia trimestral.

#### GUARDO RESULTADOS EN CSV
import os

## Indice de precios Diario (Interpolador cuadratico)
ipc_diario = ipc_union_m_[['log_index', 'index']].resample('1d').interpolate('quadratic')
ipc_diario = ipc_diario.dropna()
ipc_diario.index.name = 'd'
ipc_diario.to_csv('./data/info/indice_precios_d.csv')

## Indice de precios Mensual
ipc_union_m_.to_csv('./data/info/indice_precios_M.csv')

## Indice de precios Trimestral
# ipc_ = ipc_union_m_.groupby(pd.Grouper(freq='Q')).mean().loc['2000':][['index']]#.to_csv(...)
ipc_ = ipc_union_m_.groupby(pd.Grouper(freq='QE')).mean().loc['2000':][['index']]

### Convenciones para fijar fecha de trimestre.
from pandas.tseries.offsets import DateOffset
ipc_.index = pd.Series(ipc_.index).dt.to_period('M').dt.to_timestamp() + DateOffset(days=14, months = -1)
ipc_.index.name = 'Q'
ipc_.to_csv('./data/info/indice_precios_Q.csv')


######## FIGURAS
import matplotlib.pyplot as plt

if not os.path.exists('./figuras/'):
    os.mkdir('./figuras/')
    

fig, ax = plt.subplots(1, figsize = (12, 6))

ax.set_title('Inflacion Mensual.\nIndices provinciales e INDEC vs indice promedio.')
ax.set_ylabel('Inflacion Mensual [%]')

# (100*(10**ipc_union).pct_change().replace(0, np.nan)).plot(marker = '.', alpha = .2, ax = ax)
(100*(10**ipc_union).pct_change(fill_method=None).replace(0, np.nan)).plot(marker = '.', alpha = .2, ax = ax)

(ipc_union_m.pct_m).plot(color = 'k', lw = 1, ax = ax)

plt.grid(True, color = '.8', linestyle = '--')
ax.grid(which='minor', color='.8', linestyle=':', linewidth=0.5)
ax.minorticks_on()
plt.savefig('./figuras/figura2.png')

####

rolling_anual = 100*(-1 + ipc_diario/ipc_diario.shift(365))['index'].dropna()

fig, ax = plt.subplots(1, figsize = (12, 6))

ax.set_title('Inflacion ultimo año.')
ax.set_ylabel('Cambio de precios ultimos 365 dias. [%]')

rolling_anual.plot(ax = ax)

ax.axvline('2001-12', color = '.5', lw = 1)
ax.axvline('2003-05', color = 'k', lw = 1)
ax.axvline('2007-12', color = 'k', lw = 1)
ax.axvline('2011-12', color = '.5', lw = 1)
ax.axvline('2015-12', color = 'k', lw = 1)
ax.axvline('2019-12', color = 'k', lw = 1)

plt.grid(True, color = '.8', linestyle = '--')
ax.grid(which='minor', color='.8', linestyle=':', linewidth=0.5)
ax.minorticks_on()
plt.savefig('./figuras/figura3.png')




