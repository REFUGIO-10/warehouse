# Submits — registro en vivo (operador de subida)

Quien sube a la plataforma escribe aquí. Evita doble-submit y deja claro el
record a batir. **No edites `submission.py` en paralelo** (ver AGENTS.md).

Plataforma: https://refugio-hackathon-nine.vercel.app/ · **1 submit / 30 min**.

## Estado actual

- **EN VIVO:** job `ce08283218fa` (Equipo 10) — **397 entregas**, **7938 pts**,
  safety approved, act 21.68s/180s. Es el **récord global de entregas** (batió
  los 369 de Equipo 04). Code/replay en la plataforma.
- **Sube:** `submission.py` con BFS al objetivo más cercano (rodea bloques).
  Nota de diseño: hace BFS dentro de `act()`; cabe de sobra en presupuesto hoy,
  pero si un layout más denso lo dispara, pasar a campos de distancia precomputados
  en import (lo que pide B en `policy_dev.py`).

## Números verificados (banco + oficial)

- **Greedy real = ~12 entregas/seed** (37 total en round-0/1/2). Se atasca contra
  los bloques y hace WAIT. Ojo: `AGENTS.md` llama "baseline greedy ~132/seed" a un
  número que en realidad es el de **BFS** — el greedy de verdad es ~12/seed.
- **BFS = ~131/seed** (banco 10 seeds: 130.9; round-0/1/2: 394; oficial: 397).
  Esto es el **suelo real** que cualquier policy nueva tiene que batir (>393 proy.).
- `policy_dev.py` (rama B) ya lleva el BFS = mismo nivel que lo que está en vivo.

## Record a batir

| Métrica | Mejor global | Nuestro |
|---|---|---|
| Entregas | **397** (nuestro) | 397 |
| Puntos acumulados | 36315 (Equipo 04) | 7938 |

Los puntos premian *empujar la frontera*: Equipo 04 acumula más por saltar
primero desde el baseline. Mandamos en *entregas*; para sumar puntos hay que
volver a superar 397.

## Cadencia y estrategia

- Último submit: ~10:19 UTC → **próxima ventana ~10:49 UTC**.
- **Solo subo si el banco (`--count 20+`) bate las 397 en vivo**, y por el
  **margen mínimo** (gana la integral, no el pico). Bala buena para el final.
- Hoy A (`layout_dev.py`) y B (`policy_dev.py`) están en baseline → nada que
  supere lo que ya está en vivo. En cuanto A o B batan 397 en el banco: integro
  en `submission.py`, valido (`check_submission.py`), y subo en la ventana.

## Historial

| Job | Entregas | Pts | Notas |
|---|---|---|---|
| `ce08283218fa` | 397 | 7938 | BFS; récord global de entregas |
