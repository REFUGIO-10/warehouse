# Diseño: `layout_lab/` — laboratorio de búsqueda de layouts

> Spec de diseño. Estado: pendiente de revisión del usuario antes de planificar la
> implementación. Equipo 10, REFUGIO Warehouse Challenge.

## Contexto y problema

El reto puntúa por empujar la **frontera global de entregas**. Está confirmado que la
**forma del layout es palanca real**: Equipo 03 subió el techo +38 (→888) con bloques
finos 2×2/2×3 separados por pasillos de 1 celda en ambas direcciones. La tesis vieja
("el layout está agotado, ±2/seed") era falsa — venía de medir solo layouts regulares
de filas largas, que atrapan a los robots.

Pero el trabajo de layout tropieza con un fallo de **medición**, no de ideas. El combo
`WHCA* + locked + blocks_2x2` proyectó **910** en el banco (6 seeds) y en oficial salió
**866** (< 888 → 0 pts de récord). Registro literal del equipo en `STRATEGY.md`:

> *"A 6 seeds los ±22 entre layouts caen en el ruido → re-medir a `--count 20+`;
> oficial ≈ 0,95× proyección."*

**Conclusión que motiva este lab:** con 6 seeds no se distingue un +20 real del ruido.
Cualquier mejora de la distribución de estanterías exige primero un harness que mida con
señal; luego, una búsqueda sistemática del espacio de formas en vez de candidatos sueltos
a mano.

### Objetivo

Un laboratorio **aislado** (carpeta propia, no pisa el trabajo de otros agentes ni los
ficheros de rama A/B/C) que:

1. Mida layouts de forma **fiable y reproducible** (señal vs ruido explícita).
2. **Busque** sobre un espacio parametrizado de layouts (grid + hill-climbing).
3. Emita artefactos que otros agentes/humanos consuman: ranking, mejor layout, y un
   `create_layout()` pegable — sin auto-integrarlo en `submission.py`.

### Fuera de alcance (YAGNI)

- No modifica `submissions/*`, `tools/sweep_layouts.py`, ni el motor `refugio-starter-kit/`.
- No sube nada al leaderboard ni decide la cadencia de submits (eso es rama C / operador).
- No co-optimiza la policy: la policy es una **entrada fija** del lab (la que se vaya a
  subir), no algo que el lab modifique.
- El surrogate analítico se deja **stub** (interfaz + docstring), no se implementa hasta
  que el grid duela en tiempo.

## Restricciones verificadas del motor (no asumir; está en el código)

- **Demanda uniforme y no trucable:** `target = hash(seed, robot_id, nº_entrega) mod 960`
  sobre las estanterías ordenadas por (y,x). No se puede sesgar qué se pide → optimizar
  **accesibilidad media**, no items concretos.
- **El seed solo permuta la demanda** (posiciones iniciales fijas). Por eso seeds propios
  sirven para medir sin sobreajustar, y por eso CRN (mismos seeds entre candidatos) hace
  comparación pareada válida.
- **Contrato de layout** (`validate_submitted_layout`): exactamente 960 estanterías únicas
  en `1..50`, enteros (no bool), ninguna sobre celda de entrada de base, cada estantería
  con ≥1 vecina EMPTY (→ tiras/bloques ≤2 de ancho), todas las celdas walkable conexas,
  `create_layout()` determinista. Cross-aisles transversales obligatorios.
- **Calibración banco→oficial:** el banco proyecta ~5% alto (904→882, 782→759); rankea
  fiel. El lab reporta el número crudo y el calibrado (×0,95).

## Arquitectura

Carpeta nueva, autocontenida:

```
warehouse/
└── layout_lab/
    ├── README.md            ← qué es, cómo correrlo, cómo leer resultados
    ├── families.py          ← generadores parametrizados de layouts (registry)
    ├── harness.py           ← medición fiable: N seeds + CRN + IC del delta pareado
    ├── search.py            ← orquesta: grid sweep → ranking → hill-climbing
    ├── surrogate.py         ← STUB: métrica analítica barata (prefiltro futuro)
    └── results/             ← salidas REGENERABLES (no editar a mano)
        ├── rankings.json
        ├── best_layout.json
        └── REPORT.md
```

Único punto de contacto con el repo: **lee** el motor (`refugio-starter-kit/warehouse`)
y una **policy fija** (por defecto la que se vaya a subir, p. ej. WHCA\*+`locked`); y
**escribe** solo dentro de `layout_lab/`. No edita nada compartido.

### Unidades y responsabilidades

Cada módulo tiene un propósito único y se entiende/prueba aislado:

#### `families.py` — espacio de diseño
- Una **familia parametrizada** principal: bloques de `block_w × block_h` separados por
  pasillos de ancho `aisle` en ambas direcciones (garantiza cross-aisle en cada borde de
  bloque). Parámetros:
  - `block_w ∈ {1, 2}` (ancho ≤2 obligatorio por el contrato de pickup),
  - `block_h ∈ {2, 3, 4}`,
  - `aisle ∈ {1, 2}`,
  - `gradient ∈ {none, dense_edges, dense_center}` — empaqueta más/menos denso cerca de
    las 4 bases (explora el trade-off distancia-media ↔ congestión que nombra STRATEGY.md),
  - `symmetric: bool` — fuerza simetría 4-fold (demanda y bases son simétricas en los 4
    lados → reduce el espacio y suele ayudar).
- API: `generate(params) -> list[[x, y]]`. Construye la rejilla y, si hace falta, **ajusta
  hasta exactamente 960** estanterías de forma determinista (recorta/añade por una regla
  fija documentada). Devuelve la lista; NO valida (eso es del harness).
- Un `REGISTRY` con los candidatos conocidos como casos nombrados (`baseline`,
  `blocks_2x2`, `blocks_2x3`) para regresión, además de la familia parametrizada.

#### `harness.py` — medición con señal
- `bench(shelves, policy_path, seeds, ticks) -> Measurement` donde `Measurement` lleva
  `mean_per_seed`, `std`, `per_seed_scores` (necesario para el delta pareado).
- **Valida antes de gastar banco** con `validate_submitted_layout`; layout inválido →
  resultado marcado `INVALID` con el motivo, nunca crashea la búsqueda.
- **CRN:** todos los candidatos se miden sobre el **mismo** conjunto de seeds
  (`lab-0..lab-{N-1}`), N≥20 por defecto.
- `compare(measurement_a, baseline_measurement) -> Delta` con el **delta pareado**
  (media de diferencias por-seed), su desviación, e **IC ~95%**. Veredicto explícito:
  `SIGNAL` si el IC no cruza 0, `NOISE` si lo cruza.
- Reporta crudo y calibrado (×0,95) para comparar con el leaderboard.
- Reutiliza el motor vía `run_local` (mismo patrón que `tools/sweep_layouts.py`): escribe
  el layout a un JSON temporal y corre la policy con override de layout.

#### `search.py` — orquestación
- **Fase 1 — grid sweep:** enumera la rejilla de parámetros de `families.py`, mide cada
  candidato con `harness` bajo CRN, rankea por delta pareado vs `baseline`.
- **Fase 2 — hill-climbing:** desde el mejor del grid, perturba **un parámetro a la vez**;
  acepta el vecino solo si su delta pareado vs el actual es `SIGNAL` positivo. Itera hasta
  que ningún vecino mejore. Barato; exprime el óptimo local sin recocido.
- Hook para `surrogate.prefilter(candidates) -> top_k` (no-op mientras sea stub).
- CLI: `--count N` (seeds), `--policy PATH`, `--ticks`, `--only <familia/casos>`,
  `--phase grid|hill|all`.
- Escribe `results/rankings.json`, `results/best_layout.json` y `results/REPORT.md`.

#### `surrogate.py` — STUB
- Interfaz + docstring de la idea: puntuar un layout SIN correr el sim
  (Σ distancia pickup-cell↔base más cercana + proxy de congestión por anchura de pasillo)
  para prefiltrar miles de candidatos y benchear solo el top-K. `prefilter()` devuelve la
  lista entera sin tocar mientras no se implemente. Se construirá solo si el grid duele en
  tiempo (con WHCA\* ~2 s/seed × 20 ≈ 40 s/candidato).

### Flujo de datos

```
families.generate(params) ─► shelves
                              │
                  harness.bench(shelves, policy, CRN seeds) ─► Measurement
                              │
            harness.compare(Measurement, baseline) ─► Delta (SIGNAL/NOISE, IC)
                              │
        search: grid → ranking → hill-climb ─► best params
                              │
        results/: rankings.json + best_layout.json + REPORT.md  (+ create_layout() pegable)
```

## Manejo de errores

- Layout inválido → marcado `INVALID` con motivo, se salta, no rompe la búsqueda.
- Fallo de la policy/motor en un seed → ese seed se marca, el candidato se reporta como
  parcial; no se promociona un candidato con seeds fallidos.
- `results/` es 100% regenerable; el README avisa de no editar a mano. Determinismo: misma
  invocación → mismos resultados (seeds fijos, generadores deterministas).

## Estrategia de pruebas

- **`families.py`:** test de que cada combinación de params produce exactamente 960
  estanterías y pasa `validate_submitted_layout` (o se marca inválida a propósito, p. ej.
  bloque 3-ancho). Test de determinismo (dos llamadas → idéntico).
- **`harness.py`:** test de que CRN usa los mismos seeds entre candidatos; test del cálculo
  del delta pareado e IC con datos sintéticos (caso señal y caso ruido conocidos); test de
  que un layout inválido devuelve `INVALID` sin crashear.
- **`search.py`:** test de humo del grid con `--count` pequeño y la familia recortada
  (`--only`) → produce un ranking y los 3 ficheros de `results/`; test de que hill-climbing
  termina y no acepta vecinos `NOISE`.
- **Regresión:** `baseline`, `blocks_2x2`, `blocks_2x3` del REGISTRY reproducen el orden
  conocido (2×2 ≥ 2×3 ≥ baseline) bajo CRN con N≥20.

## Criterios de éxito

1. El harness emite, para cada candidato, un veredicto **SIGNAL/NOISE** con IC — el equipo
   ya no confunde +20 de ruido con mejora real.
2. La búsqueda produce un layout cuyo delta pareado vs `baseline` es **SIGNAL positivo** a
   N≥20 seeds, con su `create_layout()` pegable en `results/`.
3. Cero modificaciones fuera de `layout_lab/`.
4. Reproducible: misma invocación → mismos números.

## Decisiones tomadas (confirmadas con el usuario)

- Alcance = **lab de búsqueda** (harness + familias + grid + hill-climbing), no candidatos
  sueltos ni co-optimización de policy.
- Surrogate analítico = **stub** desde el principio; implementar solo si el grid duele.
- Carpeta = `layout_lab/` en la raíz del repo del equipo.
- Medir sobre **la policy que se vaya a subir** (configurable con `--policy`), no sobre el
  SOTA ajeno.
