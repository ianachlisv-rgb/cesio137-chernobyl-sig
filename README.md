# Fallout de Chernobyl (Cs-137): flujo de trabajo reproducible en Python

Código que reconstruye el flujo de trabajo del artículo
**"Reconstrucción geoespacial del fallout atmosférico de Chernobyl (1986–2020): análisis morfoestructural y de riesgo"**
(Ian A. Sandoval-Valderrábano, BUAP, Facultad de Ingeniería). El PDF está en [`paper/Chernobyl_Cs137_IEEE.pdf`](paper/Chernobyl_Cs137_IEEE.pdf) (6 páginas, formato IEEE).

El artículo se hizo con herramientas SIG de escritorio. Este repositorio no es el proyecto original: es una
**reconstrucción del proceso a partir de lo que el artículo describe**, escrita en Python y comprobada contra
las cifras publicadas (ver [Verificación](#verificación)).

## Qué hace el flujo de trabajo

```
Atlas de Cs-137 (Bq/m²) ──┐
                          ├─► proyección equivalente (LAEA, EPSG:3035)
Límites de países (NE 10m)┘          │
                                     ├─► estadística zonal: intensidad promedio por país ──┐
Chernobyl 51.389 N, 30.100 E ──► distancia geodésica a cada centroide (WGS84) ─────────────┤
                                                                                           ├─► Tabla I + mapa de clases (Fig. 3)
Clases: <6,000 | 6,000–28,000 | 28,000–120,000 Bq/m²  ◄───────────────────────────────────┘

Decaimiento  A(t) = A0 · 2^(−t/30.05)  ──► Tabla II, Fig. 4 (python decaimiento.py --figura), año en que el pico baja de 37 kBq/m² (≈ 2037)

ETOPO1 (10') ──► perfiles cada 2 km, interpolación bilineal:
                 · Alpes orientales: 12°E, de 49°N a 45.3°N
                 · Laguna Verde: acimut 252° hacia el Cofre de Perote      ──► Tabla III, Fig. 6
```

| Script (`codigo/`) | Qué hace | ¿Necesita datos externos? |
|---|---|---|
| `parametros.py` | Constantes del artículo (fuente, semivida, clases, CNLV, zonas PERE…) | No |
| `decaimiento.py` | Ec. (1), Tabla II y año en que el pico cruza el umbral de 37 kBq/m² | No |
| `distancias_paises.py` | Tabla I: distancia geodésica Chernobyl → centroide de cada país | Natural Earth (se descarga solo) |
| `zonal_cs137.py` | Intensidad promedio por país, clase y mapa (Tabla I, Fig. 3) | **Matriz de Cs-137** en Bq/m² (GeoTIFF; ver Datos) |
| `perfiles_laguna_verde.py` | Tabla III y perfiles topográficos Alpes vs. Laguna Verde (Fig. 6) | DEM para los perfiles (ETOPO1 o SRTM) |
| `puntos_a_raster.py` | Interpola observaciones puntuales (IDW) a un GeoTIFF para el paso zonal | CSV de observaciones (p. ej. NILU) |
| `verificar_paper.py` | Comprueba que el código reproduce las Tablas I, II y III | Natural Earth |
| `demo_sintetico.py` | Corre el flujo completo con datos **inventados**, solo para probar el código | Natural Earth |

## Cómo usarlo

```bash
pip install -r codigo/requirements.txt
cd codigo

python verificar_paper.py            # comprueba las cifras del artículo (no requiere el atlas)
python decaimiento.py                # Tabla II
python perfiles_laguna_verde.py --solo-tabla   # Tabla III

# Con el atlas real (ver "Datos"):
python zonal_cs137.py --atlas atlas_cs137.tif --prefijo ../resultados/europa

# Con un DEM (lat/lon, metros):
python perfiles_laguna_verde.py --dem etopo1_10min.tif --salida ../resultados/perfiles.png

# Probar todo sin datos reales:
python demo_sintetico.py
```

## Datos (no incluidos)

Los datos originales no se redistribuyen aquí. Fuentes citadas en el artículo:

- **Atlas de deposición de Cs-137 en Europa:** De Cort, M. et al. (1998), *Atlas of Caesium Deposition on Europe after the
  Chernobyl Accident*, EUR 16733, Comisión Europea / JRC. **Ojo:** el atlas oficial se publicó como mapas impresos y, según
  el grupo de NILU (Evangeliou et al.), no está disponible en formato digital. El artículo no detalla cómo se obtuvo la
  matriz en Bq/m² que se usó, así que `zonal_cs137.py` pide que tú aportes esa matriz como GeoTIFF (Bq/m², cualquier CRS; el
  script la reproyecta). Una alternativa pública y digital, pero **distinta del atlas** (otra interpolación, por lo que no
  reproduciría la Tabla I), es la base reconstruida de NILU: Evangeliou (2025), DOI 10.34355/NILU.00321.
- **SRTM GL3 (3″, ≈ 90 m):** NASA JPL, OpenTopography, <https://doi.org/10.5069/G9SRTMGL3>.
- **ETOPO1 (1′):** Amante y Eakins (2009), NOAA NGDC. En el artículo se reescala a 10′ para los perfiles.
- **Límites de países:** Natural Earth 1:10m (lo descarga `distancias_paises.py`).

## Verificación

`python verificar_paper.py` calcula todo lo que se puede calcular **sin** el atlas y lo compara con el artículo:

| Qué | Resultado |
|---|---|
| Tabla I: 9 distancias Chernobyl → centroide (km) | 9/9 coinciden al km |
| Tabla II: decaimiento 1986 / 2020 / 2026 (4 referencias × 2 años) | 8/8 coinciden al Bq/m² |
| Texto: 45.6 % del inventario en 2020; pico < 37 kBq/m² hacia 2037 (51 años) | coincide |
| Tabla III: distancia, acimut y zona PERE de 4 sitios de Laguna Verde | 4/4 coinciden |

Lo que **no** se puede verificar sin el atlas: las intensidades promedio por país (columna "Clase" de la Tabla I) y los
valores de la validación (Austria 21.0 kBq/m², etc.). Ese paso está implementado y probado solo con datos sintéticos.

## Prueba con datos reales (NILU, no es el atlas)

Con la base puntual de Evangeliou (2025), DOI [10.34355/NILU.00321](https://doi.org/10.34355/NILU.00321) (11,334 observaciones
de 137Cs; los datos **no** se redistribuyen aquí), se interpoló por IDW a una malla de 5 km (`puntos_a_raster.py`, k = 8,
potencia 2, radio 75 km, tope 120,000 Bq/m²) y se corrió `zonal_cs137.py`:

| País | Distancia (km) | Puntos en el país | Media (Bq/m²) | Clase obtenida | Clase del artículo |
|---|---:|---:|---:|---|---|
| República Checa | 1,061 | 101 | 6,768 | 6,000–28,000 | 28,000–120,000 |
| Austria | 1,230 | 113 | 30,246 | 28,000–120,000 | 28,000–120,000 ✓ |
| Eslovenia | 1,265 | **1** | 27,426 | 6,000–28,000 | 28,000–120,000 |
| Alemania | 1,375 | 304 | 6,929 | 6,000–28,000 | 6,000–28,000 ✓ |
| Italia | 1,660 | 443 | 9,727 | 6,000–28,000 | < 6,000 |
| Suiza | 1,671 | 57 | 5,313 | < 6,000 | 6,000–28,000 |
| Luxemburgo | 1,704 | **1** | 6,215 | 6,000–28,000 | < 6,000 |
| Bélgica | 1,779 | 48 | 7,964 | 6,000–28,000 | < 6,000 |
| Francia | 2,079 | 93 | 8,493 | 6,000–28,000 | < 6,000 |

Coinciden 2 de 9 clases (resultados en `resultados_nilu/`). **Esto no valida ni contradice el artículo:**
la base de NILU no es el atlas (otros puntos, otra interpolación) y está centrada en la antigua Unión Soviética;
en Europa occidental tiene pocos puntos (Eslovenia y Luxemburgo, uno cada uno), así que el IDW depende de muy
pocos datos. Lo que sí demuestra es que la cadena completa (puntos → malla → zonal → clase → mapa) corre con datos reales.
El promedio de Austria (≈ 30 kBq/m²) queda por arriba del valor publicado por Bossew et al. (21.0 kBq/m²), coherente
con el sesgo al alza que el propio artículo describe cuando solo se promedian celdas con dato.

## Lo que se dedujo (y por qué)

El artículo no da todos los parámetros. Estos se **dedujeron comprobando que reproducen las tablas publicadas**:

- **Proyección:** el texto dice "GRS_1980 Lambert Azimuthal Equal Area". Con EPSG:3035 (ETRS89-LAEA) y el centroide
  de cada país salen las 9 distancias de la Tabla I.
- **Francia:** el artículo dice "territorio metropolitano". Solo con Francia continental **sin Córcega** sale 2,079 km
  (con Córcega: 2,074 km).
- **Coordenadas de la central de Laguna Verde:** 19.7206 N, 96.4064 O, que reproducen la Tabla III. Los sitios de
  referencia (Xalapa, Veracruz, Cofre de Perote, Pico de Orizaba) usan coordenadas aproximadas.
- **Tiempo de decaimiento:** t = 34 años para 2020 y 40 años para 2026, contados desde mayo de 1986.

## Sesgo que el artículo declara

La simbología del atlas empieza en 1,000 Bq/m²; lo que está por debajo queda como "sin dato". Si esas celdas se ignoran,
el promedio nacional solo considera zonas contaminadas y **sale sobrestimado**; además, el techo de 120,000 Bq/m² viene de
la simbología, no de una medición. Por eso `zonal_cs137.py` entrega dos promedios:
`media_validas` (ignora celdas sin dato, como describe el artículo) y `media_con_cero` (las cuenta como 0, cota inferior).
El valor real queda entre ambos. En el demo sintético, Bélgica pasa de ≈ 1,100 a ≈ 4 Bq/m² según el criterio.

## Limitaciones

- Solo decaimiento físico: sin migración vertical en el suelo, erosión ni absorción por vegetación.
- Efecto orográfico evaluado por **correlación visual** con la precipitación; no se usan datos de lluvia de 1986.
- Los perfiles de Laguna Verde son un análogo **cualitativo** del caso alpino, no un modelo de dispersión.
  Como trabajo futuro el artículo propone modelos lagrangianos (HYSPLIT, FLEXPART).

## No incluido

- Los datos originales (atlas, SRTM, ETOPO1) ni el proyecto SIG original.
- El script de la Fig. 2 (atlas semitransparente sobre sombreado del SRTM).
- `figuras/decaimiento_cs137.png` es cálculo real (decaimiento); la carpeta `ejemplo_sintetico/` contiene **datos inventados**: sus cifras no son del atlas ni del artículo.

## Licencia

MIT (ver `LICENSE`).
