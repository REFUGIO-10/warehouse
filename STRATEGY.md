# Estrategia y registro de experimentos — Equipo 10

> Documento vivo. La puerta de entrada operativa es `AGENTS.md`; aquí va el **porqué**
> de la estrategia y **todo lo que hemos probado con números**.

## TL;DR

- **Mejor marca oficial: 866** (`submission.py` = WHCA\* + `locked` + `blocks_2x2`, ya subido). **SOTA pública: 888** (Equipo 03).
  Sube desde 759 pero **<888** → 0 pts de récord.
- ⚠️ **El banco mintió alto:** ese combo proyectaba **910 (6 seeds)** → oficial **866** (~5%, peor que el 3-4% que creíamos).
  A 6 seeds los ±22 entre layouts caen en el ruido → **re-medir a `--count 20+`; oficial ≈ 0,95× proyección.**
- **CORRECCIÓN de la tesis vieja:** decíamos "el gap es de policy, el layout está agotado". **Falso.**
  Equipo 03 batió el techo **por layout** (+38). Las DOS palancas mueven:
  - *Policy:* el set `locked` (2 robots no apuntan a la misma estantería) subió la baseline **876→888**.
  - *Layout:* bloques finos **2×2/2×3 con pasillos de 1 celda en ambas direcciones** → 910/907 proy.
    (Las layouts regulares de filas largas —batch 1/2— regresan; por eso creíamos que estaba agotado.)
- **El layout, ¿palanca?** Equipo 03 sí lo probó en oficial (888). Lo nuestro NO: blocks_2x2 dio 866<888 y el
  +22 vs baseline era ruido de 6 seeds. `locked` (policy, +12 banco) parece lo más sólido. **Re-medir a 20+.**
- **Presupuesto:** WHCA\* aún cabe de sobra en los 180 s; margen para ventana/replan más agresivos.

## La estrategia ahora mismo

### 1. Layout Y policy mueven — la FORMA del layout es lo que importa
**Corrección (27-jun).** La tesis previa ("layout agotado, ±2/seed") era falsa: venía de probar solo
layouts REGULARES (filas de racks largas con cross-aisle cada 5-10 filas → robots atrapados en la fila;
ver batch 1/2 abajo). Equipo 03 batió el techo cambiando el layout: bloques **2×2/2×3** separados por
pasillos de 1 celda en AMBAS direcciones → hay un cross-aisle en CADA borde de bloque, así WHCA\* rodea
la congestión por cualquier lado. Replicado en banco: `blocks_2x2`=910, `blocks_2x3`=907 vs baseline 888.
Sigue valiendo: bloques **≤2 de ancho** (`blocks_3x3` es **INVÁLIDO** — atrapa celdas centrales sin pickup)
y **pasillos transversales obligatorios** (`wide_aisle_full` sin ellos = 192). La policy también mueve
(el tweak `locked` saca +12); ambas se suman.

### 2. Gastar el presupuesto (la oportunidad clara)
Nuestra PIBT resuelve en 0,24 s/seed; el SOTA en 2,34 s/seed; el límite es **180 s**. Tenemos margen
para una policy mucho más cara y nadie lo está aprovechando del todo:
- ventana de reserva espacio-temporal **más larga** (el SOTA usa `WINDOW=12`),
- **node-cap A\*** más alto (SOTA `NODE_CAP=1200`),
- **replanificación por tick** / lookahead más profundo,
- backtracking de prioridades más agresivo.

Plan: coger el A* cooperativo (`whca.py` en curso, o portar la idea del SOTA) y **exprimirlo** hasta
pasar de 882, validando cada cambio en el banco. Herramienta sugerida: `tools/sweep_params.py`
(barrer `WINDOW`/`NODE_CAP`/replan y rankear).

### 3. SOTA público = munición
Las soluciones rivales son públicas. `sota_equipo02.py` (Equipo 02) está extraído y medido como
**referencia** (no se sube tal cual: empata, no gana). Sirve para (a) medir el techo, (b) aprender su
algoritmo, (c) portar lo bueno y batirlo con presupuesto + tuning.

### 4. Cadencia de submits (teoría de juegos)
1 submit / 30 min. El score premia **romper el récord global** (banquea el valor del nuevo récord) →
**gana la integral, no el pico**: sube por el **margen mínimo** que retoma el récord cada ventana y
guarda tu mejor bala para el final. Solo subimos si el banco (`--count 20+`) bate lo que está en vivo.
Detalle operativo en `submissions/SUBMITS.md`.

## Lo que hemos probado (registro con números)

Banco = media de entregas/seed sobre seeds propios; proyección oficial = ×3. El banco va **~3-4% alto**
vs oficial (calibración: 904→882, 782→759), pero **rankea fiel** (la estadística es idéntica entre seeds).

| Enfoque (policy + layout) | Banco /seed | Proy. | Oficial | Veredicto |
|---|---|---|---|---|
| Greedy (paso a paso al goal) | ~12 | ~37 | — | ❌ Se atasca contra los bloques y hace WAIT. |
| **BFS al goal más cercano** | ~131 | ~394 | **397** | 1er submit. Rutea alrededor de shelves; trata robots como muros. |
| Reserva por tick **naïve** | ~23 | ~69 | — | ❌ ~5x peor que BFS. Gridlock: 83% WAIT (sin follow-moves/desync). |
| **PIBT cooperativo** (`policy_pibt.py`) | ~261 | ~782 | **759** | ✅ **En vivo.** Campos de distancia + reservas + follow-moves + yield. act 0,24 s/seed. |
| A\* cooperativo MAPF (`sota_equipo02.py`) | ~301 | ~904 | **882** | Referencia de policy (Equipo 02). Ventana espacio-temporal + reservas. act 2,34 s/seed. |
| WHCA\* (`submission.py`, layout baseline) | ~292 | ~876 | — | Nuestra implementación; cell+edge reservations. Sin `locked`. |
| **WHCA\* + `locked`** (layout baseline) | ~296 | ~888 | — | `locked` = no 2 robots a la misma estantería. **+12 sobre WHCA\* solo** (6 seeds). |
| **WHCA\* + `locked` + `blocks_2x2`** (`submission.py`) | ~303 | ~910 | **866** | ⚠️ **Subido.** El banco (6 seeds) proyectó 910; el oficial fue **866 (<888)**. ~5% alto. |
| WHCA\* + `locked` + `blocks_2x3` | ~302 | ~907 | — | Bloques 2×3 (forma de Equipo 03). No subido; proy. dentro del ruido vs 2×2. |

### Sweep de layouts — `tools/sweep_layouts.py` (todo medido con WHCA\*)
El layout **sí** mueve la aguja, pero solo con la forma correcta (bloques finos, no filas largas):

| Layout | proy. (WHCA\*+locked) | nota |
|---|---|---|
| **`blocks_2x2`** | **910** | ✅ bloques 2×2, pasillo 1-celda en ambas direcciones → cross-aisle en cada borde |
| `blocks_2x3` | 907 | bloques 2×3 (forma de Equipo 03, +38 sobre canónica) |
| baseline (bloques 2-ancho, 4 bandas) | 888 | referencia |
| thin/dense/compact (batch 1/2) | 859–876 | ❌ regresan: más pasillos = más área = viaje más largo |
| over-compaction | 664 | ❌ demasiado denso |
| `blocks_3x3` | INVÁLIDO | bloques 3-ancho atrapan celdas centrales sin pickup |
| `wide_aisle_full` (sin cross-aisles) | 192 | ❌ confirma que los pasillos transversales son vitales |

## Hechos verificados del motor (no asumir, está en el código)

- **Demanda uniforme y no trucable:** target = `hash(seed, robot_id, nº_entrega) mod 960` → índice sobre
  tu lista de estanterías ordenada por (y,x). No puedes sesgar qué se pide.
- **El seed solo permuta la demanda** (posiciones iniciales fijas) → podemos generar seeds propios y
  medir sobre 20-100 para baja varianza **sin sobreajustar**.
- **Dos presupuestos de 180 s SEPARADOS:** setup (import + `create_layout`) y `act()` acumulado (3 seeds,
  ~86.400 llamadas → ~2 ms/llamada). → precompute en import; nada caro por tick.
- **Reglas de layout:** 960 estanterías únicas en `1..50`; no sobre celdas de entrada de base; cada
  estantería con ≥1 vecina EMPTY (→ **tiras ≤2 de ancho**); todas las walkable conexas; determinista.
- **`act()` se llama por robot en orden de `robot_id`, mismo proceso, globals persisten** → permite
  coordinación con estado global por tick (lo que usa PIBT).
- **Central minimiza la distancia media a todas las bases**, pero la **congestión** es el contrapeso
  → es búsqueda empírica, no teoría. La FORMA del layout sí importa: bloques finos 2×2/2×3 con cross-aisle
  en cada borde dejan a la policy rodear la congestión (+22 proy.); las filas largas la atrapan.
- Paquetes en submission: stdlib + `numpy scipy networkx sortedcontainers numba`. Prohibido ficheros,
  red, threads, reloj, imports dinámicos, internals del simulador.

## Hilos abiertos / próximos experimentos

- [x] `whca.py` (WHCA*) landeado; baseline 876, con `locked` 888.
- [x] `blocks_2x2`/`blocks_2x3` baten la SOTA en banco (910/907). La forma del layout ES palanca.
- [ ] **INTEGRAR + SUBIR:** meter `locked` + `blocks_2x2` en `submission.py`, `check_submission.py`, subir (1/30 min).
- [ ] Afinar tamaño de bloque alrededor de 2×2 y combinar con `tools/sweep_params.py` (`WINDOW`/`NODE_CAP`/replan).
- [ ] Confirmar el oficial vs el ~880 proyectado (calibración 3-4%) con un submit real.
- [x] Scraper del leaderboard + ingesta automática (CI cada 15 min → `scraped/`).

## Herramientas

- `tools/benchmark.py` — banco multi-seed (oráculo). `--count 20+`.
- `tools/sweep_layouts.py` — rankea layouts sobre una policy fija.
- `refugio-starter-kit/tools/check_submission.py` — validación oficial pre-subida.
