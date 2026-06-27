# REFUGIO Warehouse Challenge — Equipo 10

> **Puerta de entrada.** Si acabas de llegar: lee "El problema" (30s), busca **tu rama**
> abajo, ve a tu fichero. Todo el trabajo nuestro está en la raíz; el motor oficial
> queda intacto en `refugio-starter-kit/`.
>
> **Estrategia + todo lo que hemos probado con números → [`STRATEGY.md`](STRATEGY.md).**

## Estado

- **Mejor marca oficial: 866** (`submission.py` = WHCA\* + `locked` + layout `blocks_2x2`, ya subido).
  Sube desde 759, pero **sigue por DEBAJO de la frontera 888** → 0 pts de récord. (El scraper puede
  mostrar 759 hasta el próximo refresco.)
- ⚠️ **El banco MINTIÓ alto:** ese mismo combo proyectaba **910 en banco (6 seeds)** → oficial **866** (~5% menos).
  La calibración real es peor que el 3-4% que creíamos, y con 6 seeds los ±22 entre layouts caen DENTRO del
  ruido. **Re-mide cualquier layout a `--count 20+` y trata el oficial como ≈ 0,95× la proyección.**
- `submission.py` está integrado y commiteado (= `whca.py`): WHCA\* + `locked` + bloques 2×2. NO el WHCA\* viejo.
- **SOTA pública: 888 (Equipo 03), lograda por LAYOUT** (bloques 2×3, +38 oficial sobre la canónica). Equipo 02 = 884.
- **¿El layout es palanca?** Para Equipo 03 sí (888 oficial). Para nosotros, el +22 de `blocks_2x2` vs baseline
  era 6-seed (ruido) y el submit dio 866<888 → **no demostrado en oficial por nuestra parte**. Re-medir a 20+
  seeds antes de fiarse. El tweak `locked` (policy) sí parece real (+12 banco). Detalle en `STRATEGY.md`.
- Operación de subida (1 submit / 30 min): ver **`submissions/SUBMITS.md`**.

## Estructura del repo

```
warehouse/
├── AGENTS.md              ← estás aquí (gateway)
├── refugio-starter-kit/   ← motor oficial. NO meter cosas nuestras aquí.
├── submissions/           ← nuestro trabajo
│   ├── submission.py      ← INTEGRACIÓN: lo subido. = WHCA* + locked + blocks_2x2. OFICIAL 866 (bench proy era 910).
│   ├── whca.py            ← = submission.py (WHCA* + locked + bloques 2×2). locked = anti-contención (+12 banco).
│   ├── policy_pibt.py     ← PIBT cooperativo (759). Fallback de policy.
│   ├── sota_equipo02.py   ← REFERENCIA (Equipo 02, 882). No subir tal cual.
│   ├── pibt_v2.py         ← experimento de layout sobre PIBT (5 bandas, más pasillos transversales)
│   ├── layout_dev.py      ← RAMA A (edita solo create_layout)
│   ├── policy_dev.py      ← RAMA B (edita solo act)
│   └── SUBMITS.md         ← log del operador de subida
├── tools/
│   ├── benchmark.py       ← RAMA C (oráculo multi-seed)
│   ├── sweep_layouts.py   ← RAMA C (rankea layouts sobre una policy fija)
│   ├── sweep_params.py    ← RAMA C (barre WINDOW/NODE_CAP — aún sin commitear)
│   └── scrape.py          ← RAMA C (scraper del leaderboard → scraped/)
└── scraped/               ← inteligencia rival (código público de todos los equipos)
```

## Elige tu rama

### Rama A · Layout → `submissions/layout_dev.py`
Editas **solo `create_layout()`**. El `act()` es el BFS probado, para que tus layouts den entregas reales.
- **Pista actual (27-jun):** bloques finos **2×2 / 2×3 separados por pasillos de 1 celda en AMBAS direcciones**
  → cross-aisle en cada borde de bloque, WHCA\* rodea la congestión por cualquier lado. **`blocks_3x3` INVÁLIDO**
  (3-ancho atrapa celdas centrales sin pickup); las filas largas (cross-aisle cada 5-10 filas) **regresan**.
- ⚠️ **Realidad del submit:** `blocks_2x2` proyectaba 910 en banco (6 seeds) pero dio **866 oficial (<888)**.
  El +22 vs baseline está DENTRO del ruido a 6 seeds. **Mide a `--count 20+`**, no a 6, antes de declarar ganador.
- **Objetivo:** demanda uniforme sobre tus 960 estanterías; robots desde los 4 bordes.
  Minimiza el viaje medio base↔estantería **sin estrechar pasillos** (atascos). Búsqueda local moviendo estanterías.
- **Reglas (el validador rechaza si no):** 960 estanterías únicas en `1..50`; ninguna sobre
  una celda de entrada de base; cada estantería con ≥1 vecina EMPTY (pickup) → **tiras ≤2 de ancho**
  (un bloque más ancho deja celdas internas sin pickup = inválido); todas las celdas walkable
  conexas; `create_layout()` determinista. Los **pasillos transversales son críticos** (sin ellos se hunde).
- **Mide sobre la MEJOR policy** (no sobre el BFS débil): `python tools/sweep_layouts.py --count 5`
  prueba tus layouts encima del act del SOTA. Añade candidatas en `CANDIDATES`; las inválidas se
  reportan y se saltan. Para iterar la layout aislada: `python tools/benchmark.py submissions/layout_dev.py --count 20`

### Rama B · Policy → `submissions/policy_dev.py`
Editas **solo `act()`** y sus helpers. El `create_layout()` es el baseline, para medir la policy aislada.
- **Punto de partida = BFS al objetivo más cercano** (rodea bloques). Es el suelo (~131/seed).
- **Palanca 1:** precomputa **campos de distancia en el import** (setup tiene sus propios ~180 s;
  `act()` debe quedar ~2 ms/llamada → nada de BFS por tick si un layout denso lo dispara).
- **Palanca 2 (con cuidado):** coordinación/reservas. Una reserva naïve **nos regresó ~5x**
  (gridlock). Solo añádela si el banco confirma que bate el suelo.

### Rama C · Infra → `tools/benchmark.py`, `tools/scrape.py`
El oráculo. Imprime **mean/seed** y **PROJECTED OFFICIAL (mean × 3)** — ese es el número.
- **`tools/scrape.py` (hecho):** baja el código público de TODOS los equipos a `scraped/`
  (solo stdlib, sin auth). Empieza por `scraped/INDEX.md`; cómo usarlo en `scraped/README.md`.
  Bucle: `scrape → benchmark scraped/solutions/<file> → copiar layout a A / policy a B → batir`.
- Siguientes: scheduler de submits (1/30 min, sube solo si el banco bate la frontera viva).

## Comandos (desde la raíz `warehouse/`)

```bash
python tools/benchmark.py submissions/<fichero>.py --count 20          # media de entregas sobre 20 seeds propios
python tools/benchmark.py submissions/<fichero>.py --seeds round-0,round-1,round-2
python refugio-starter-kit/tools/check_submission.py submissions/submission.py   # validación oficial pre-subida
```
El banco ya valida el layout al cargarlo (mismo loader oficial), así que para iterar basta el banco.

## El problema (30s)

Colocas **960 estanterías** en una rejilla 50×50 (interior `1..50`, bordes = bases). **96 robots**
(uno por base) hacen viajes recoger→entregar durante **300 ticks**. Cada robot ve su target (una
estantería), va a una celda contigua libre → `PICKUP`, lleva al drop de su base → `DROP` (+1 entrega,
nuevo target). **Score = total de entregas sobre 3 seeds.** `blocked_moves`/`remaining_distance` solo desempatan.
Submission = **un único `.py`** con `create_layout()` y `act(observation)`.

## Hechos clave (verificados en el código)

- **Demanda uniforme y no trucable:** target = `hash(seed, robot_id, nº_entrega) mod 960` → índice
  sobre tu lista de estanterías ya ordenada por (y,x). Optimiza la **accesibilidad media**.
- **El seed solo permuta la demanda** (posiciones iniciales fijas) → es solo un string. Por eso el
  banco evalúa sobre 20-100 seeds propios: baja varianza, **sin sobreajustar** a round-0/1/2.
- **Dos presupuestos de 180 s SEPARADOS:** setup (import + `create_layout`) y `act()` acumulado sobre
  los 3 seeds (~86.400 llamadas → **~2 ms/llamada**). → precompute en import; nada caro por tick.
- **Palancas:** policy (tweak `locked`, +12 banco) parece real. Layout en bloques 2×2/2×3: Equipo 03 lo confirmó
  en oficial (888), pero nuestro +22 en banco era 6-seed y el submit dio 866<888 → re-medir a 20+ (datos en `STRATEGY.md`).
- Paquetes en submission: stdlib + `numpy scipy networkx sortedcontainers numba`. Prohibido: ficheros,
  red, threads/procesos, reloj, imports dinámicos, internals del simulador.

## Números verificados (corrige creencias viejas)

| Solución (policy + layout) | proy. (×3) | nota |
|---|---|---|
| Greedy (paso a paso hacia el goal) | ~37 | se atasca contra los bloques y hace WAIT |
| BFS al goal más cercano | ~394 (oficial 397) | submission inicial |
| PIBT cooperativo (`policy_pibt.py`) | ~782 (oficial 759) | en vivo, act 0,24 s/seed |
| A* cooperativo MAPF (Equipo 02) | ~904 (oficial 882) | referencia de policy |
| WHCA* (`submission.py`, layout baseline) | ~876 | nuestra base actual; sin `locked` |
| WHCA* + `locked` (layout baseline) | ~888 banco | `locked` solo: +12 en banco |
| **WHCA* + `locked` + `blocks_2x2`** (`submission.py`) | 910 banco / **866 OFICIAL** | subido. <888 frontera; banco ~5% alto |
| WHCA* + `locked` + `blocks_2x3` | ~907 banco | bloques 2×3 (no subido) |

(`locked` (policy) saca +12 en banco. El +22 de los bloques 2×2 era 6-seed y **NO se confirmó**: el submit dio
**866 oficial < 888** (banco ~5% alto; ±22 entre layouts cae en el ruido a 6 seeds). La SOTA 888 (Equipo 03)
sí es por layout pero medida en oficial. **Re-mide layouts a 20+ seeds.** Detalle y log en `STRATEGY.md`.)

## Estrategia de submits (resumen)

Soluciones rivales públicas → cópialas, re-puntúalas en el banco, mejóralas. El score banquea el valor
del nuevo récord al superar el mejor global: **gana la integral, no el pico** → rompe el récord por el
**margen mínimo** cada ventana y guarda tu mejor bala para el final. Detalle y estado vivo en `submissions/SUBMITS.md`.
```
