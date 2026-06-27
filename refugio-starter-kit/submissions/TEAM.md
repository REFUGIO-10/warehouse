# Equipo 10 — ramas de trabajo

Cada rama es un fichero válido e independiente: podéis correr y medir sin esperar a nadie.

| Rama | Fichero | Dueño edita | No tocar |
|------|---------|-------------|----------|
| A · Layout | `submissions/layout_dev.py` | `create_layout()` | el `act()` greedy de abajo |
| B · Policy | `submissions/policy_dev.py` | `act()` + helpers | el `create_layout()` baseline |
| C · Infra  | `tools/benchmark.py` | el banco / scraper / scheduler | — |

`submissions/submission.py` = **la integración** (lo que se sube). Al final:
layout de A + act de B pegados ahí. Nadie edita `submission.py` en paralelo —
se mergea cuando A y B tienen algo mejor que el baseline.

## Comandos (desde `refugio-starter-kit/`)

```bash
python tools/check_submission.py submissions/<fichero>.py   # valida forma + layout
python tools/benchmark.py submissions/<fichero>.py --count 20   # media de entregas sobre 20 seeds
```

## Reglas que decidimos

- **El banco manda.** Medid sobre muchos seeds (`--count 20+`), no sobre round-0/1/2.
  Los 3 seeds oficiales son ruido; la estadística es idéntica entre seeds.
- **Layout = mayor palanca de score.** `act()` ~2 ms/llamada (precompute en import, no BFS por tick).
- **Coordinación = mayor palanca de policy.** Reservas por tick ya van en `policy_dev.py`.
- No sobreajustar a 3 seeds. Proyección oficial = (media por seed) × 3.
