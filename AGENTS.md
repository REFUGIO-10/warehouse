# REFUGIO Warehouse Challenge — Equipo 10

> **Puerta de entrada.** Si acabas de llegar: lee "El problema" (30s), busca **tu rama**
> abajo, ve a tu fichero. Todo el trabajo nuestro está en la raíz; el motor oficial
> queda intacto en `refugio-starter-kit/`.
>
> **Estrategia + todo lo que hemos probado con números → [`STRATEGY.md`](STRATEGY.md).**

## Estado

- **Nosotros EN VIVO: 759** (`submissions/policy_pibt.py`, PIBT — bench ~261/seed, 782 proy).
- **SOTA = Equipo 02: 882** (`submissions/sota_equipo02.py`, referencia — bench ~301/seed, A* cooperativo).
  Gap ~16%, **y es de POLICY** (mismo layout baseline; su A* rutea mejor que nuestra PIBT).
- **Tenemos 10x de presupuesto sin usar:** PIBT gasta ~0,24 s/seed de los 180 s. Hay margen para
  una policy mucho más pesada (A* con ventana más larga, replanificación).
- **La layout ya casi no es palanca:** sweep sobre PIBT → `horizontal_bands` +2/seed (ruido),
  `wide_avenues` se hunde. Con tiras ≤2 + pasillos transversales, la baseline ya es casi óptima.
  El 16% que falta está en la **policy**, no en el layout.
- Operación de subida (1 submit / 30 min): ver **`submissions/SUBMITS.md`**.

## Estructura del repo

```
warehouse/
├── AGENTS.md              ← estás aquí (gateway)
├── refugio-starter-kit/   ← motor oficial. NO meter cosas nuestras aquí.
├── submissions/           ← nuestro trabajo
│   ├── submission.py      ← INTEGRACIÓN: lo que se sube (BFS, = lo que está en vivo)
│   ├── layout_dev.py      ← RAMA A
│   ├── policy_dev.py      ← RAMA B
│   └── SUBMITS.md         ← log del operador de subida
└── tools/
    ├── benchmark.py       ← RAMA C (oráculo multi-seed)
    └── scrape.py          ← RAMA C (scraper del leaderboard → scraped/)
scraped/                   ← inteligencia rival (código público de todos los equipos)
```

## Elige tu rama

### Rama A · Layout → `submissions/layout_dev.py`
Editas **solo `create_layout()`**. El `act()` es el BFS probado, para que tus layouts den entregas reales.
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
- **Layout es la mayor palanca de score; la policy es la segunda.**
- Paquetes en submission: stdlib + `numpy scipy networkx sortedcontainers numba`. Prohibido: ficheros,
  red, threads/procesos, reloj, imports dinámicos, internals del simulador.

## Números verificados (corrige creencias viejas)

| Policy | entregas/seed | proy. oficial | nota |
|---|---|---|---|
| Greedy (paso a paso hacia el goal) | ~12 | ~37 | se atasca contra los bloques y hace WAIT |
| BFS al goal más cercano | ~131 | ~394 (oficial 397) | submission inicial |
| **PIBT cooperativo (`policy_pibt.py`)** | **~261** | **~782 (oficial 759)** | **lo nuestro en vivo**, act 0,24 s/seed |
| A* cooperativo MAPF (Equipo 02) | ~301 | ~904 (oficial 882) | SOTA público. El gap a nosotros es la policy. |

(En la layout baseline, BFS ≈ no se atasca; la ganancia ahora está en **mejorar la layout (A)**,
porque con pasillos donde el greedy moriría es donde una buena policy/layout despega.)

## Estrategia de submits (resumen)

Soluciones rivales públicas → cópialas, re-puntúalas en el banco, mejóralas. El score banquea el valor
del nuevo récord al superar el mejor global: **gana la integral, no el pico** → rompe el récord por el
**margen mínimo** cada ventana y guarda tu mejor bala para el final. Detalle y estado vivo en `submissions/SUBMITS.md`.
```
