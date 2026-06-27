# Submits — registro en vivo (operador de subida)

Quien sube a la plataforma escribe aquí. Evita doble-submit y deja claro el
record a batir. **No edites `submission.py` en paralelo** (ver AGENTS.md).

Plataforma: https://refugio-hackathon-nine.vercel.app/ · **1 submit / 30 min**.

## Estado actual

- **EN VIVO (nuestro récord): 759 entregas** — job `8960d3b7806b` (PIBT, `policy_pibt.py`).
  Confirmado por el scraper (`scraped/INDEX.md`, 10:52 UTC). Superó nuestro 397 (BFS) anterior.
  La frontera global sigue en 882 (Equipo 01/02), así que ese submit ganó 0 pts de récord.
- ⚠️ **`submission.py` AHORA contiene WHCA\*** (copia de `whca.py`, último commit), **NO** el PIBT
  que está en vivo ni el BFS antiguo. **WHCA\* no está banqueado** (`STRATEGY.md` lo lista como hilo
  abierto; el "proj 903" del commit no está verificado). **Antes de subir:**
  `python tools/benchmark.py submissions/submission.py --count 20` y confirma que bate 759 proy.
  Si no bate, restaura el PIBT vivo: `cp submissions/policy_pibt.py submissions/submission.py`.

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
| Entregas | **882** (Equipo 01/02) | 759 |
| Puntos acumulados | 88683 (Equipo 02) | 7938 |

Los puntos premian *empujar la frontera global*. Nuestro 759 quedó por debajo de
los 882 que ya tenían varios equipos → 0 pts por ese submit. Para volver a sumar
puntos hay que **superar 882**, no solo nuestro propio récord.

## Cadencia y estrategia

- Último submit: ~10:19 UTC → **próxima ventana ~10:49 UTC**.
- **Solo subo si el banco (`--count 20+`) bate los 759 en vivo**, y por el
  **margen mínimo** (gana la integral, no el pico). Bala buena para el final.
- Candidato pendiente: WHCA\* (ya en `submission.py`) — banquéalo vs 759 ANTES de subir.
  En cuanto algo bata 759 en el banco: valido (`check_submission.py`) y subo en la ventana.

## Historial

| Job | Entregas | Pts | Notas |
|---|---|---|---|
| `ce08283218fa` | 397 | 7938 | BFS al goal más cercano; primer submit, récord global en su momento |
| `8960d3b7806b` | 759 | 0 | PIBT cooperativo; superó nuestro 397. 0 pts (no batió la frontera global 882) |
