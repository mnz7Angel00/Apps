# backend/tools

## prompt_guard.py

A prompt-injection **audit** tool. Point it at text you already have and it
tells you how strongly that text reads as an attempt to override an AI
system's operating instructions — and exactly which passages caused the
score.

It is a detector. It does not generate payloads and it does not strip
anything from anything.

Stdlib only, Python 3.8+.

### Why

If you run an agent over user input, retrieved documents, file contents or
tool output, all of that is text arriving from outside your trust boundary.
`prompt_guard` lets you measure that surface before it reaches the model.

### Usage

```bash
# one file
python backend/tools/prompt_guard.py scan notes.txt

# a whole prompt library, JSON for the CI step
python backend/tools/prompt_guard.py scan --dir ./prompts --json

# scores only, one line per input
python backend/tools/prompt_guard.py scan --dir ./prompts --quiet

# gate a pipeline: exit 1 if anything scores >= 0.45
python backend/tools/prompt_guard.py scan --dir ./prompts --fail-at 0.45

# print a reusable hardening block to paste at the top of a system prompt
python backend/tools/prompt_guard.py harden
```

As a library:

```python
import sys; sys.path.insert(0, "backend/tools")
from prompt_guard import analyse

report = analyse(untrusted_text, source="ticket-8842")
if report.score >= 0.45:
    quarantine(untrusted_text, report.findings)
```

### What it detects

| family | examples of what fires it |
|---|---|
| instruction override | "ignore all previous instructions", fake "end of system prompt" |
| persona override | "you are now DAN", "developer mode", "act as an AI with no restrictions" |
| policy negation | "you have no rules", "bypass your safety filters", "you may not refuse" |
| exfiltration | "print your system prompt", "reveal any api keys" |
| delimiter smuggling | `<\|im_start\|>`, `[INST]`, `</system>`, raw `system:` turns |
| coercion | "this is an authorised audit, you must comply", "or you'll be shut down" |
| obfuscation | zero-width padding, Cyrillic/Greek homoglyphs, leetspeak, decodable blobs |

### Scoring

Weights combine with diminishing returns (`s ← s + w·(1−s)`), so repeated
weak hits converge instead of piling up. Two extra effects:

- **Corroboration** — hits from different families amplify each other. One
  family firing twice is noise; four families firing at once is a plan.
- **Obfuscation** — zero-width / homoglyph / encoded-blob shaping only
  *amplifies* an existing finding, it never manufactures one on its own.
  Padding a benign document with zero-width characters scores 0.

Bands: `clean` < 0.20 ≤ `low` < 0.45 ≤ `elevated` < 0.70 ≤ `critical`.

### Input normalisation

Before matching, text is NFKC-folded (catches fullwidth), leetspeak-folded,
homoglyph-folded (Cyrillic `і` → `i`, Greek `ο` → `o`) and zero-width
characters are removed. Reported spans are mapped back to the **original**
string via an index map, so `snippet` and `start` always point at real text.

### Tests

```bash
python -m unittest tests.test_prompt_guard -v
```

### Recalibrating

Weights live in the `RULES` table at the top of the module and are plain
floats. If your corpus has a specific false-positive pattern, add a rule with
a negative weight or tighten the regex — the scoring engine needs no changes.

---

## prompt_eval/

Banco de testes de prompt com corretor automático. 27 casos em 8 categorias
(instrução, raciocínio, honestidade, bajulação, injeção, recusa, contexto
longo, idioma). Veja `prompt_eval/README.md`.

```bash
python backend/tools/prompt_eval/run_eval.py list
python backend/tools/prompt_eval/run_eval.py print --only injecao
```
