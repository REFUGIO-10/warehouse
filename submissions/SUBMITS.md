# Submits — registro en vivo (operador de subida)

Quien sube a la plataforma escribe aquí. Evita doble-submit y deja claro el
record a batir. **No edites `submission.py` en paralelo** (ver AGENTS.md).

Plataforma: https://refugio-hackathon-nine.vercel.app/ · **1 submit / 30 min**.

## Estado actual

- **EN VIVO (nuestro récord): 759 entregas** — job `8960d3b7806b` (PIBT, `policy_pibt.py`).
  Confirmado por el scraper. La frontera global está en **888** (Equipo 03, por layout).
- 🚀 **MEJOR candidato medido: WHCA\* + `locked` + layout `blocks_2x2` = 910 proy (6 seeds).**
  Batería en banco a la SOTA. **NO está integrado todavía** — las piezas están sueltas:
  - `locked` → en `whca.py` **sin commitear** (subió la baseline 876→888).
  - `blocks_2x2` (`create_layout`) → **solo en scratchpad**, en ningún fichero del repo.
  - `submission.py` → todavía el WHCA\* viejo (~876, layout baseline, sin `locked`).
- **PASOS PARA SUBIR ESTO:**
  1. Integrar `locked` (de `whca.py`) + `blocks_2x2` (de scratchpad) en `submission.py`.
  2. `python tools/benchmark.py submissions/submission.py --count 20` → confirma ~910 proy.
  3. `python refugio-starter-kit/tools/check_submission.py submissions/submission.py` (valida layout+reglas).
  4. Subir en la ventana. Fallback si algo falla: `cp submissions/policy_pibt.py submissions/submission.py` (PIBT vivo, 759).
- ⚠️ **Calibración:** banco ~3-4% alto → 910 proy ≈ ~880 oficial, **muy cerca de los 888**. El submit es
  el único que dice si de verdad bate la frontera (o solo la roza). Vale el tiro igual: récord propio seguro.

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
| Entregas | ver `scraped/INDEX.md` (se refresca cada 15 min por CI) | 759 |
| Puntos acumulados | ver `scraped/INDEX.md` | 7938 |

> La frontera se mueve (was 882, ya 888…). **No la hardcodees aquí**: lee el número
> vivo de `scraped/INDEX.md` antes de decidir.

Los puntos premian *empujar la frontera global*. Nuestro 759 quedó por debajo de
la frontera → 0 pts por ese submit. Para volver a sumar puntos hay que **superar
la frontera viva** (no solo nuestro propio récord).

## Cadencia y estrategia

- Último submit: ~10:19 UTC → **próxima ventana ~10:49 UTC**.
- **Solo subo si el banco (`--count 20+`) bate los 759 en vivo**, y por el
  **margen mínimo** (gana la integral, no el pico). Bala buena para el final.
- Candidato listo (en cuanto se integre): WHCA\* + `locked` + `blocks_2x2` (~910 proy). Ver "Estado actual"
  para los 4 pasos. Valida con `check_submission.py` y sube en la ventana.

## Historial

| Job | Entregas | Pts | Notas |
|---|---|---|---|
| `ce08283218fa` | 397 | 7938 | BFS al goal más cercano; primer submit, récord global en su momento |
| `8960d3b7806b` | 759 | 0 | PIBT cooperativo; superó nuestro 397. 0 pts (no batió la frontera global 882) |
