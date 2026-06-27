# Submits — registro en vivo (operador de subida)

Quien sube a la plataforma escribe aquí. Evita doble-submit y deja claro el
record a batir. **No edites `submission.py` en paralelo** (ver AGENTS.md).

Plataforma: https://refugio-hackathon-nine.vercel.app/ · **1 submit / 30 min**.

## Estado actual

- **EN VIVO (nuestro récord): 866 entregas** — WHCA\* + `locked` + layout `blocks_2x2` (`submission.py`, ya subido).
  Sube desde el 759 (PIBT) anterior. La frontera global está en **888** (Equipo 03) → seguimos por debajo → 0 pts de récord.
  (El scraper puede tardar un refresco en mostrar el 866 y su job id.)
- ⚠️ **Lección del submit:** el banco proyectó **910 (6 seeds)**; el oficial fue **866** (~5% menos, peor que el
  3-4% que asumíamos). **Mide a `--count 20+` y descuenta ~5%** para estimar el oficial — no subas fiándote de 6 seeds.
- `submission.py` ya está integrado y commiteado (= `whca.py`). Fallback para revertir: `cp submissions/policy_pibt.py submissions/submission.py` (PIBT 759).
- **CANDIDATO LISTO (sin subir, commit `b61fc3b`):** WHCA\* + `locked` + **`_coordinated_step`** + layout **2×3**. Banco 6-seed ~905 proy; estimado oficial **~870-880** (descontando ~5%). Apunta a batir 888 pero probablemente se queda corto — subir en la próxima ventana salvo mejor idea.

## Hallazgos clave — analizadas las 5 top (888/883/882/879…)

Todas son **el MISMO algoritmo que el nuestro**: WHCA\* centralizado (1 planner/tick en el robot 0), reservas espacio-tiempo de celda+arista, prioridad (cargando→inanición→distancia), resolución de conflictos sesgada por prioridad. Lo que nos faltaba:

1. **`_coordinated_step` (LA diferencia).** Los robots recién-entregados (sin target aún) NO deben dar un paso greedy suelto: deben dar un paso **plan-aware** que respete las celdas que los movers ya reservan ese tick (`next_claimed`) y evite edge-swaps. Si no, cancelan movimientos coordinados → cientos de movimientos desperdiciados. **Era nuestro gap principal** (nuestro 866 usaba greedy suelto). Ya implementado en `whca.py`.
2. **Cuello de botella diagnosticado:** con WHCA\* `blocked_moves` ≈ 30 (congestión RESUELTA). El cuello ahora es `remaining_distance` ≈ 2000 = **distancia de viaje** → favorece layout **DENSA** (2×3 > 2×2: 50% vs 44% de densidad → viajes más cortos).
3. **Layout (confirmado en 11 variantes):** bloques finos (2×2/2×3 con pasillos de 1 celda en **AMBAS** direcciones) baten el baseline; rack-rows largos, spreading y compactación extrema **regresan**. 2×3 = sweet spot (denso + cross-aisle en cada borde de bloque). El "+38" de Equipo 03 es real.
4. **Gap restante a 888 = policy fina.** `coordinated_step` dio solo +3 en banco (su valor real en hidden es incógnita). Otras palancas de los líderes aún sin copiar: prioridad **`can_deliver` primero**, y **endgame right-of-way** (`HORIZON=300`, visto en `f692704ea634`).

## Números verificados (banco + oficial)

- **Greedy real = ~12 entregas/seed** (37 total en round-0/1/2). Se atasca contra
  los bloques y hace WAIT. Ojo: `AGENTS.md` llama "baseline greedy ~132/seed" a un
  número que en realidad es el de **BFS** — el greedy de verdad es ~12/seed.
- **BFS = ~131/seed** (banco 10 seeds: 130.9; round-0/1/2: 394; oficial: 397).
  Esto es el **suelo real** que cualquier policy nueva tiene que batir (>393 proy.).
- `policy_dev.py` (rama B) arranca en el BFS (~131/seed). El suelo a batir hoy es el PIBT
  en vivo (~261/seed = 759 proy.), no el BFS — usa el banco para compararte contra eso.

## Record a batir

| Métrica | Mejor global | Nuestro |
|---|---|---|
| Entregas | ver `scraped/INDEX.md` (frontera 888; se refresca cada 15 min por CI) | 866 |
| Puntos acumulados | ver `scraped/INDEX.md` | 7938 |

> La frontera se mueve (was 882, ya 888…). **No la hardcodees aquí**: lee el número
> vivo de `scraped/INDEX.md` antes de decidir.

Los puntos premian *empujar la frontera global*. Nuestro 759 quedó por debajo de
la frontera → 0 pts por ese submit. Para volver a sumar puntos hay que **superar
la frontera viva** (no solo nuestro propio récord).

## Cadencia y estrategia

- Último submit: ~10:19 UTC → **próxima ventana ~10:49 UTC**.
- **Solo subo si el banco (`--count 20+`, no 6) bate los 866 en vivo** descontando ~5%, y por el
  **margen mínimo** (gana la integral, no el pico). Bala buena para el final.
- Para sumar puntos hay que pasar de **888** (frontera). 866 ya está subido; lo siguiente tiene que apuntar a >888 oficial.

## Historial

| Job | Entregas | Pts | Notas |
|---|---|---|---|
| `ce08283218fa` | 397 | 7938 | BFS al goal más cercano; primer submit, récord global en su momento |
| `8960d3b7806b` | 759 | 0 | PIBT cooperativo; superó nuestro 397. 0 pts (no batió la frontera) |
| _(pend. scraper)_ | 866 | 0 | WHCA* + `locked` + `blocks_2x2`. Banco 6-seed proyectó 910 → oficial 866 (<888) |
