# Estrategia y registro de experimentos — Equipo 10

> Documento vivo. La puerta de entrada operativa es `AGENTS.md`; aquí va el **porqué**
> de la estrategia y **todo lo que hemos probado con números**.

## TL;DR

- **En vivo: 759** (`policy_pibt.py`). **SOTA: 882** (Equipo 02). Gap ~16%.
- **El gap es de POLICY, no de layout.** Misma layout baseline en ambos; su A* cooperativo
  rutea mejor que nuestra PIBT.
- **Usamos 0,24 s de los 180 s de presupuesto** → 10x de cómputo sin tocar.
- **Conclusión:** el siguiente salto sale de **una policy más fuerte que gaste el presupuesto**
  (A* con ventana larga + replanificación), no de tocar el layout.

## La estrategia ahora mismo

### 1. La policy es la palanca; el layout está agotado
Medido en banco (ver tabla abajo): cambiar el layout sobre una policy buena mueve **±2/seed (ruido)**.
La restricción del problema (tiras de estanterías ≤2 de ancho por la regla de pickup + pasillos
transversales obligatorios + demanda uniforme) hace que la **baseline ya sea casi óptima**. No merece
la pena grinding de layouts a mano. El 16% que falta está en cómo se mueven los 96 robots.

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

| Enfoque | Banco /seed | Proy. | Oficial | Veredicto |
|---|---|---|---|---|
| Greedy (paso a paso al goal) | ~12 | ~37 | — | ❌ Se atasca contra los bloques y hace WAIT. |
| **BFS al goal más cercano** | ~131 | ~394 | **397** | 1er submit. Rutea alrededor de shelves; trata robots como muros. |
| Reserva por tick **naïve** | ~23 | ~69 | — | ❌ ~5x peor que BFS. Gridlock: 83% WAIT (sin follow-moves/desync). |
| **PIBT cooperativo** (`policy_pibt.py`) | ~261 | ~782 | **759** | ✅ **En vivo.** Campos de distancia + reservas + follow-moves + yield. act 0,24 s/seed. |
| A\* cooperativo MAPF (`sota_equipo02.py`) | ~301 | ~904 | **882** | SOTA público (Equipo 02). Ventana espacio-temporal + reservas. act 2,34 s/seed. |

### Sweep de layouts (sobre policy fija) — `tools/sweep_layouts.py`
El layout casi no mueve la aguja sobre una policy buena:

| Layout | sobre SOTA /seed | sobre PIBT /seed | nota |
|---|---|---|---|
| baseline (bloques 2-ancho, 4 bandas) | 301 | 261 | referencia |
| horizontal_bands (transpuesta) | 300 | 263 | empata (simétrico) |
| wide_avenues (tiras altas, sin bandas) | 59 | 67 | ❌ sin pasillos transversales → colapsa |

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
  → es búsqueda empírica, no teoría. (En la práctica el layout apenas importa con buena policy.)
- Paquetes en submission: stdlib + `numpy scipy networkx sortedcontainers numba`. Prohibido ficheros,
  red, threads, reloj, imports dinámicos, internals del simulador.

## Hilos abiertos / próximos experimentos

- [ ] `whca.py` (WHCA*) — landearlo y compararlo vs PIBT en banco.
- [ ] **`tools/sweep_params.py`**: barrer `WINDOW`, `NODE_CAP`, profundidad de replan → exprimir los 180 s.
- [ ] Portar/mejorar el A* del SOTA y batir 882.
- [ ] Búsqueda automática de layout (annealing) — upside probablemente <10%, baja prioridad.
- [ ] Scraper del leaderboard + ingesta automática de soluciones públicas rivales.

## Herramientas

- `tools/benchmark.py` — banco multi-seed (oráculo). `--count 20+`.
- `tools/sweep_layouts.py` — rankea layouts sobre una policy fija.
- `refugio-starter-kit/tools/check_submission.py` — validación oficial pre-subida.
