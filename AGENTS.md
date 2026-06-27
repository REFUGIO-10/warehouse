# REFUGIO Warehouse Challenge — Equipo 10

Guía para humanos y agentes. Todo el trabajo vive en `refugio-starter-kit/`.
Corre los comandos **desde `refugio-starter-kit/`**.

## El problema en 30 segundos

Colocas **960 estanterías** en una rejilla 50×50 (interior `1..50`, bordes = bases).
**96 robots** (uno por base en el borde) hacen viajes recoger→entregar durante
**300 ticks**. Cada robot: ve su target (una estantería), va a una celda contigua
libre, `PICKUP`; lleva a la celda de drop de su base, `DROP` → +1 entrega y recibe
nuevo target.

**Score = total de entregas, sumado sobre 3 seeds.** `blocked_moves` y
`remaining_distance` solo son desempates.

Submission = **un único `.py`** con `create_layout()` y `act(observation)`.
Plataforma: https://refugio-hackathon-nine.vercel.app/ · 1 submit / 30 min.

## Hechos clave (verificados en el código, no en el README)

- **Demanda uniforme y no trucable.** El target es `hash(seed, robot_id, nº_entrega) mod 960`
  → índice sobre tu lista de estanterías *ya ordenada por (y,x)*. Toda estantería se
  pide por igual; el orden no te da ventaja. → Optimiza la **accesibilidad media**.
- **El seed solo permuta la demanda.** Las posiciones iniciales de los robots son
  fijas. Por eso **el seed es solo un string**: podemos evaluar sobre 20-100 seeds
  propios para una estimación de baja varianza del score oficial **sin sobreajustar**.
- **Dos presupuestos de 180s SEPARADOS:** setup (import + `create_layout`) y `act()`
  acumulado sobre los 3 seeds. Son ~86.400 llamadas a `act()` → **~2 ms/llamada**.
  → Precomputa en el import (sabemos nuestra layout); **nunca BFS dentro de `act()`**.
- **Layout = la mayor palanca de score** (puede casi duplicar entregas). Policy/
  coordinación es la segunda.
- Paquetes permitidos en submission: stdlib + `numpy scipy networkx sortedcontainers numba`.
  Prohibido: ficheros, red, threads/procesos, `time.time`/reloj, imports dinámicos,
  e internals del simulador (`warehouse.simulation`, `warehouse.state`).

## Ramas de trabajo (1 fichero por persona, todos válidos por separado)

| Rama | Fichero | Edita | No tocar |
|------|---------|-------|----------|
| **A · Layout** | `submissions/layout_dev.py` | `create_layout()` | el `act()` greedy |
| **B · Policy** | `submissions/policy_dev.py` | `act()` + helpers | el `create_layout()` baseline |
| **C · Infra**  | `tools/benchmark.py` | banco / scraper / scheduler | — |

`submissions/submission.py` = **la integración** (lo que se sube): layout de A +
act de B, pegados ahí cuando ambos baten al baseline. **Nadie edita `submission.py`
en paralelo.**

## Comandos

```bash
python tools/check_submission.py submissions/<fichero>.py        # valida forma + reglas de layout
python tools/benchmark.py submissions/<fichero>.py --count 20    # media de entregas sobre 20 seeds propios
python tools/benchmark.py submissions/<fichero>.py --seeds round-0,round-1,round-2
```

El banco imprime **mean/seed** y **PROJECTED OFFICIAL (mean × 3)** — ese es el
número que importa. Mide siempre con `--count 20+`, no con 3 seeds.

## Baseline medido (greedy + layout baseline)

~**132 entregas/seed** → proyección oficial ~**397**. setup ~0 s, act ~3 s/seed
(holgura enorme sobre 180 s). Cualquier cambio se juzga contra esto en el banco.

## Reglas de layout (el validador rechaza si no se cumplen)

960 estanterías únicas en `1..50`; no sobre una celda de entrada de base; cada
estantería con ≥1 vecina EMPTY para pickup; todas las celdas walkable conexas;
`create_layout()` determinista (se llama dos veces y se compara).

## Direcciones de mejora

- **A (layout):** denso cerca de las bases + avenidas anchas; minimiza viaje medio
  sin crear atascos. Búsqueda local moviendo estanterías. Mide en el banco.
- **B (policy):** BFS de campos de distancia precomputados en import → paso al
  vecino con menor distancia (rodea bloques en vez de WAIT). La coordinación
  (reservas) hay que hacerla bien: **una reserva naïve nos regresó ~5x** (gridlock,
  83% WAIT). Valida cualquier coordinación en el banco antes de fiarte.
- **C (infra):** scraper del leaderboard + ingesta de layouts públicos rivales
  (re-puntúalos en el banco y alimenta a A) + scheduler de submits (1/30 min).

## Estrategia de submits (leaderboard público, records que se banquean)

Las soluciones rivales son públicas → cópialas, re-puntúalas, mejóralas. El score
banquea el valor del nuevo récord cada vez que superas el mejor global: **gana la
integral, no el pico** → rompe el récord en cada ventana por el margen mínimo,
guarda tu mejor bala para el final. Confirmar regla exacta en la plataforma.
