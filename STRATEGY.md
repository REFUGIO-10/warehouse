# Estrategia y registro de experimentos — Equipo 10

> Documento vivo. La puerta de entrada operativa es `AGENTS.md`; aquí va el **porqué**
> de la estrategia y **todo lo que hemos probado con números**.

## TL;DR

- **Mejor marca oficial nuestra: 888** (job `d0f2389ad450` = WHCA\* + `locked` + **`_coordinated_step`** +
  `blocks_2x3`, subido 27-jun 11:53). Sube desde 866: **`_coordinated_step` capturó la congestión tal como
  predijo la tesis** — blocked_moves oficiales **26/33/25 → 3/8/5**, **+22 entregas**. Pero 888 = pelotón
  (6 equipos clavados ahí, copiando el público de Equipo 03) y **<895 (frontera Equipo 16) → 0 pts. Estancados.**
  **Frontera pública viva: 895** (Equipo 16). Para romperla → la bala `whca_2x2flow.py` (banco 914) de abajo.
- 🆕 **MEJOR BALA MEDIDA (27-jun): `submissions/whca_2x2flow.py`** = `blocks_2x2` + el flow-penalty/detour/
  center-tiebreak/coordinated-step del 895, pero con los **carriles flow CASADOS al período 2×2** (el 895 los
  tiene casados a su 2×3, `y%4==2`). Banco **914 (50 seeds, sd 9)** vs Equipo 16 (895) **903** y nuestro
  `submission.py` **900** → **+11 / +14**. Mejora **real, no copia** (entrega lo que §2 predijo: "casar el
  flow del 895 y exprimirlo"). Caveat: en los 3 seeds oficiales exactos el 895 empata-gana (914 vs 911, ruido
  sd 17) y el banco va ~5 % alto → 914 ≈ **~870-895 oficial** → roza la frontera; **solo un submit confirma**.
- ⚠️ **El banco mintió alto:** ese combo proyectaba **910 (6 seeds)** → oficial **866** (~5%, peor que el 3-4% que creíamos).
  A 6 seeds los ±22 entre layouts caen en el ruido → **re-medir a `--count 20+`; oficial ≈ 0,95× proyección.**
- **TECHO MEDIDO (27-jun, `tools/freeflow.py`): el problema ya está resuelto al ~93 %.** El máximo
  físico (flujo libre, cero congestión) es **~320/seed ≈ 960 total** para CUALQUIER layout. La frontera 895
  está al **93,3 %** de ese techo. **No existe ningún salto grande**: el margen total es ~65 entregas y la
  última franja es inalcanzable (colisiones simultáneas inevitables). Realista: **895 → ~905-920.**
- **El LAYOUT NO es palanca de distancia.** Medida la distancia media ida-vuelta para todas las formas:
  **39,3–39,9 celdas, ventana del 1,4 %.** Las 96 bases rodean la caja → cualquier celda está a ~40 de una
  base aleatoria, central o no. **CORRECCIÓN de la tesis "la forma del layout es lo que importa": falsa para
  distancia.** La forma solo mueve por **anti-congestión** (cross-aisles → menos blocked_moves), y eso cae en
  el ruido (nuestro "+22" de bloques NO se confirmó en oficial: 866<895). El "+38" de Equipo 03 sobre la
  canónica también es anti-congestión, no distancia. **Congelar el layout.**
- **La congestión es el ÚNICO lever vivo, y la evidencia fresca lo confirma:** el delta 866→895 es
  **blocked_moves** (nuestro 866 = 26/33/25 bloqueos por run; el 895 = **2/3/1**), no distancia ni planner
  nuevo. Es congestión **local** (4 bases-esquina + embudos de entrada); densidad global = **6,2 %**.
- **Tenemos 14× de cómputo sin usar:** WHCA\* gasta **12,3 s de 180 s** (medido). Pero ojo: con el 895 ya en
  2/3/1 bloqueos, lo barato (eliminar bloqueos) está casi capturado → un rewrite MAPF completo (LNS2) es
  **alto esfuerzo y retorno incierto**. El ROI está en **igualar el flow-penalty+detour del 895 y exprimirlo**.

## El techo real (27-jun, MEDIDO con `tools/freeflow.py`, calibrado vs motor)

Flujo libre = cada robot hace sus viajes ida-vuelta óptimos (BFS sobre el grid real) contra el stream de
targets sha256 real, **sin congestión**. Es el máximo físico que un layout puede dar.

| Layout | dist. media ida | flujo-libre/seed | ×3 | válido |
|---|---|---|---|---|
| diamante (min Σ dist-a-bases, óptimo teórico) | 39,30 | 321 | 963 | ✅ |
| 2×3 blocks (nuestra `submission.py` / forma SOTA) | 39,86 | 319 | 958 | ✅ |
| central cluster (ring road) | 39,60 | 305 | 914 | ❌ rompe conexión |

**Lectura:** distancia ≈ 40 ida para todo (ventana 1,4 %) → **techo ≈ 960 igual para cualquiera. Layout =
palanca muerta.** El óptimo teórico de distancia (diamante) solo da +2/seed = +6 oficial = ruido.

### Calibración flujo-libre → banco → oficial (nuestra `submission.py`, 2×3)

| Capa | /seed | % del flujo-libre |
|---|---|---|
| Flujo libre (techo físico) | 319 | 100 % |
| Banco round-0/1/2 | 303 (298, 323, 288) | 95 % |
| Oficial | 289 (=866) | 90,6 % |
| Frontera viva (Equipo 16) | 298 (=895) | 93,3 % |

El banco va ~5 % alto y es ruidoso (sd 14,7). La pérdida real de congestión es ~10 % (319→289 nuestro,
319→298 el SOTA). **Ese ~7-10 % es TODO el terreno que queda, y el SOTA ya capturó la mayoría.**

### Dónde está el cuello (distribución por base)

- ida media por base: **min 35,5 (centro-borde) · max 47,9 (esquinas) · media 39,9 · std 3,7**.
- 4 bases más lentas = las 4 **esquinas** (`rid 23, 24, 48, 95`): ~3 viajes/robot vs ~4,1 las de centro.
- Densidad global **6,2 %** (96/1540) → congestión NO global, es de **embudo** (entrada de base + aisles
  cerca del perímetro). El 895 ya la lleva a 2/3/1 blocked_moves → el embudo está casi resuelto arriba.

### Confirmación independiente del techo + la mejora real (28-jun, `tools/instrument.py`)

Segundo método, coincide con `freeflow.py`: contabilizando los **28.800 robot-ticks** del 895 sobre un seed,
**96,0 % son MOVE productivos · 1,8 % WAIT · ~0 % colisiones (2 reverts de 28.800)**. La congestión global
ya está liquidada → el throughput es **distancia pura** (~92 move-ticks/entrega, ida ~46). El planner del 895
no tiene grasa que quitar; confirma "el 895 capturó casi todo".

**PERO sí queda un +11 real, y es de anti-congestión casada a la geometría — exactamente el ROI de §2.**
Medido a **50 seeds** (no 6 → fuera del ruido que nos quemó antes):
- `blocks_2x2` (rejilla fina, pasillo cada 3 en AMBOS ejes) bate a `blocks_2x3` con flow=0: **902 vs 898**.
- Los flow-penalty del 895 están casados a su período 2×3 (`y%4==2`, `y//4`). En 2×2 hay que **recasarlos**
  (`y%3==2`, `y//3`). Hecho → el flow aporta **+12 en 2×2** (902→914) vs +8 en 2×3. La anti-congestión
  responde a la **finura** de la rejilla: más estructura de carril que explotar.
- Resultado: `whca_2x2flow.py` = **914 (50 seeds, sd 9)** vs 895-Equipo16 **903** (50 seeds). +11 ≈ **10 SE**.
- `FLOW_PENALTY` óptimo en 2×2 = **0,1** (monótono 0,1>0,2>0,3 en n24 y n50), no 0,2 como en 2×3.
- **No contradice "layout = palanca muerta para distancia":** esto NO es distancia (la ida sigue ~40), es el
  **lever de congestión** que §2 marcó como único vivo, exprimido vía rejilla más fina + carriles alineados.
- Disciplina: en round-0/1/2 exactos el 895 saca 914 vs 911 (ruido); banco ~5 % alto. Mejor bala, no
  frontier-break garantizado. Subir para confirmar oficial.

## La estrategia ahora mismo

### 1. Congelar el layout — solo importa que tenga cross-aisles, no su forma fina
**Corrección (27-jun, medida).** Tesis previa ("la forma del layout es lo que importa"): **falsa para
distancia.** El flujo-libre (`tools/freeflow.py`) da 39,3–39,9 de ida para TODAS las formas válidas
(diamante = óptimo teórico = solo +2/seed sobre 2×3 = ruido). La distancia es geometría pura: las 96 bases
rodean la caja. Lo ÚNICO que la forma cambia es la **congestión**: un layout con cross-aisle en cada borde
de bloque deja al planner rodear embudos → menos blocked_moves. Por eso `blocks_3x3` es **INVÁLIDO**
(atrapa celdas sin pickup) y `wide_aisle_full` sin cross-aisles se hunde (192). Pero entre layouts BUENOS
(2×2/2×3 con cross-aisles), el delta cae en el ruido (866<895). **Conclusión: la forma 2×3 actual ya es
suficiente; tocar `create_layout()` es rascar o regresar.** Única excepción acotada: micro-relieve SOLO en
los embudos de entrada de base, medido a 20+ seeds.

### 2. La congestión es 100 % policy — pero el cheap-win ya está casi capturado
Tenemos 14× de cómputo libre (12,3 s / 180 s), pero el 895 ya está en 2/3/1 blocked_moves: lo que queda
NO es eliminar bloqueos (hecho) sino el **overhead de detour/espera** del MAPF, que es el tail duro e
inalcanzable. Por eso:
- **Default (alto ROI):** igualar el **flow-penalty + detour simple** del 895 y exprimirlo (sweep de
  `FLOW_PENALTY`, detour field-aware, reservas de stayer más cortas). Ver "Ideas accionables" abajo.
- **Opción cara (ROI incierto):** rewrite a **LNS2 / PIBT-con-rollback**. Solo si los micro-tweaks topan
  y el banco a 20+ seeds demuestra que recupera detour-overhead real. No empezar por aquí.
- Subir `WINDOW`/`NODE_CAP` del WHCA\* = mismo algoritmo más caro: rasca 2-3, no es la palanca.

> **Recordatorio de marco:** "+15 entregas" suena a rascar, pero cerca de la frontera cada entrega vale
> ~790 pts (bounty triangular). 895→910 ≈ **11.500 pts + liderato**. Es el mayor botín disponible.

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

Banco = media de entregas/seed sobre seeds propios; proyección oficial = ×3. El banco va **~3-5% alto**
vs oficial (calibración: 904→882, 782→759, **909/910→866**), pero **rankea fiel**. Usa ×0,95 conservador.

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
| **Equipo 16 público** (`ba833bb4d9ea`) | ~302 / 301 (50s) | ~905 / 903 | **895** | SOTA público: layout 2×3 + flow penalty (casado a 2×3) + detour + center-tiebreak + coordinated-step. |
| 🆕 **`whca_2x2flow.py`** (2×2 + flow casado a 2×2, f=0,1) | **~305 (50s)** | **914** | — | **Mejor bala.** +11 vs Equipo16 (903, 50s) ≈ 10 SE; +14 vs `submission.py`. Sólido en skill medio; falta submit p/ oficial. |

### Sweep de layouts — `tools/sweep_layouts.py` (medido con WHCA\*, 6 seeds)
⚠️ **6 seeds = ruidoso.** `blocks_2x2` lideró aquí con 910 pero el submit dio **866 oficial (<888)**; los ±22
entre las mejores layouts caen dentro del ruido. Esta tabla sirve para descartar lo MALO (filas largas,
sin cross-aisles), **no** para rankear lo bueno. Re-mide candidatas a 20+ seeds:

| Layout | proy. (WHCA\*+locked, 6 seeds) | nota |
|---|---|---|
| **`blocks_2x2`** | 910 banco → **866 oficial** | bloques 2×2, pasillo 1-celda en ambas direcciones → cross-aisle en cada borde |
| `blocks_2x3` | 907 | bloques 2×3 (forma de Equipo 03, +38 oficial sobre canónica) |
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
- **Dos presupuestos de 180 s SEPARADOS:** setup (usamos 0,01 s) y `act()` acumulado sobre 3 seeds
  (~86.400 llamadas). **Medido: 12,3 s de 180 → 6,8 %, sobra 14×.** Cabe una policy mucho más cara, pero
  ver §2: el cuello ya no es CPU. **Colisión simultánea** (edge-swaps + vértices) hace el techo 960
  inalcanzable: siempre quedan choques residuales aunque el planner sea perfecto.
- **Reglas de layout:** 960 estanterías únicas en `1..50`; no sobre celdas de entrada de base; cada
  estantería con ≥1 vecina EMPTY (→ **tiras ≤2 de ancho**); todas las walkable conexas; determinista.
- **`act()` se llama por robot en orden de `robot_id`, mismo proceso, globals persisten** → permite
  coordinación con estado global por tick (lo que usa PIBT).
- **La distancia es geometría, no optimizable:** con 96 bases rodeando la caja, la distancia media a una
  estantería aleatoria es ~40 ida para CUALQUIER layout (medido: ventana 39,3–39,9, 1,4 %). "Central" NO
  baja distancia (las bases están por los 4 lados). La forma solo cambia la **congestión** (cross-aisles →
  menos blocked_moves); entre layouts con cross-aisles ese efecto está en el ruido. → **layout = palanca
  muerta para entregas; el techo (~960) es el mismo para todos.**
- Paquetes en submission: stdlib + `numpy scipy networkx sortedcontainers numba`. Prohibido ficheros,
  red, threads, reloj, imports dinámicos, internals del simulador.

## Ideas accionables tras el scrape fresco

La frontera ya no es 888 sino **895**. El benchmark local a 20 seeds separa al nuevo SOTA: nuestro `submission.py`
y Equipo 03 dan ~897 proy.; Equipo 16 da ~905 proy. La mejora parece venir de bajar `blocked_moves`, no de
reescribir el planner: nuestro 866 oficial tuvo 26/33/25 bloqueos por run; el 895 tuvo 2/3/1.

Próximos experimentos con mejor ROI:

1. **Base de trabajo:** partir del 895 público como referencia, no de nuestro 866. No subirlo tal cual: empata la frontera.
2. **Pickup base-facing:** combinar el 895 con `shelf_field_to_base_side` de Equipo 14 para elegir el lado de pickup que minimiza la vuelta cargado.
3. **Detour field-aware:** el 895 desvía al primer vecino libre; probar elegir vecino por menor `goal_field` y sin swap.
4. **Reservas de stayers más cortas:** hoy bloquean su celda todo el `WINDOW`; probar reservar 1-2 ticks para pickup/drop.
5. **Sweep de `FLOW_PENALTY`:** ✅ HECHO. En 2×2 el óptimo es **0,1** (0,1>0,2>0,3, n50). Falta probar
   variantes solo-internos vs perímetro y recasar para otros períodos si se cambia el layout.
6. **Fallback `_field_step`:** portar el fallback plan-aware de Equipo 15 cuando A\* agota `NODE_CAP`.
7. **Endgame priority:** probar prioridad de Equipo 02 para robots que todavía pueden entregar antes del tick 300.
8. **Layout:** ✅ CORREGIDO. Entre layouts buenos, **2×2 con flow recasado bate a 2×3** (+11, n50) — pero
   el lever es anti-congestión, no distancia, y exige recasar los carriles al período (`y%3==2`). Evitar
   filas largas / sin cross-aisles (se hunden). `whca_2x2flow.py` es la integración actual de esto.

## Hilos abiertos / próximos experimentos

- [x] `whca.py` (WHCA*) landeado; baseline 876, con `locked` 888 (banco, 6 seeds).
- [x] Integrado + subido: WHCA\* + `locked` + `blocks_2x2` (`submission.py`). **Oficial 866** (sube desde 759, <888 frontera).
- [x] Aprendido: el banco 6-seed va ~5% alto y es ruidoso; el "+22 del layout" NO se confirmó en oficial.
- [x] Scrape fresco: frontera pública 895; nuevo benchmark local: `submission.py`/Equipo 03 ~897 proy., Equipo 16 ~905 proy.
- [ ] Para batir 895: recombinar micro-mejoras sobre el 895 público; no perseguir otro rewrite MAPF completo.
- [ ] Re-medir cada híbrido a `--count 20+` y estimar oficial con margen conservador antes de subir.
- [x] Scraper del leaderboard + ingesta automática (CI cada 15 min → `scraped/`).

## Herramientas

- `tools/benchmark.py` — banco multi-seed (oráculo). `--count 20+`.
- `tools/sweep_layouts.py` — rankea layouts sobre una policy fija (ya poco útil: layout muerto).
- `tools/freeflow.py` — **techo de flujo-libre por layout** (análisis del máximo físico, no banco).
- `tools/exp.py` — driver de experimentos: parchea constantes (`WINDOW`/`NODE_CAP`/`FLOW_PENALTY`/stayer) y/o
  override de layout sobre un base, y banquea N seeds. Workhorse del sweep de policy+flow.
- `tools/instrument.py` — contabiliza a dónde van los 28.800 robot-ticks (MOVE/WAIT/PICKUP/DROP/reverts).
  Demostró que el 895 es 96 % MOVE productivo, ~0 colisiones → throughput = distancia.
- `tools/metric.py` — **distancia media de acceso estática** (BFS desde 96 bases) → predice el ranking de
  layouts SIN simular. Confirma 2×2 = menor meanD (39,78) y que el ideal central (38,1) es inalcanzable.
- `tools/gen_layouts.py` — genera+valida JSONs de layout candidatos (block geometries, highways, central).
- `refugio-starter-kit/tools/check_submission.py` — validación oficial pre-subida.
