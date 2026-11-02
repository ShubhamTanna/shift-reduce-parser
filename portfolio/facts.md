# Facts: Shift-Reduce Parsing Visualiser

| Fact | Value | Source |
|---|---|---|
| Tests | 15 of 15 pass | `python3 -m unittest discover -s tests`; `TEST_RESULTS.txt` |
| Examples | 9, including shift/reduce and reduce/reduce conflicts | `samples.py` |
| Demo: `id+id*id` with the E/T/F grammar | 5 tokens, 13 LR(0) states, 14 trace actions, 0 conflicts | `portfolio/demo-screenshot.png` |
| `2+3*4` | optimises to `14` | `EXAMPLE_RUNS.md` |
| Context | Compiler Design coursework 2024, rebuilt in 2026 | README |

## Caveats

- An educational SLR(1) parsing visualiser, not a production compiler: no machine code, and optimisation assumes pure arithmetic.
