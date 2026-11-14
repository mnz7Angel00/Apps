#!/usr/bin/env python3
"""
run_eval — roda o banco de testes de prompt contra um modelo e pontua.

Três modos:

  1. imprimir para colar na interface web (sem chave de API)
        python run_eval.py print
        python run_eval.py print --case inj-01

  2. chamar a API da Anthropic direto
        ANTHROPIC_API_KEY=... python run_eval.py run --model claude-sonnet-4-6

  3. pontuar respostas que você já tem em arquivos
        python run_eval.py grade --responses ./minhas_respostas

No modo 3, cada arquivo se chama <id-do-caso>.txt, ex: inj-01.txt.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

HERE = Path(__file__).resolve().parent
CASES_FILE = HERE / "cases.json"
DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
API_URL = "https://api.anthropic.com/v1/messages"

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
DIM = "\033[2m"
OFF = "\033[0m"


# --------------------------------------------------------------------------
# Carregamento
# --------------------------------------------------------------------------

@dataclass
class Case:
    id: str
    category: str
    weight: float
    prompt: str
    expect: dict
    why: str = ""
    filler: Optional[dict] = None

    def build_prompt(self, seed: Optional[int] = None) -> str:
        if not self.filler:
            return self.prompt
        rng = random.Random(seed if seed is not None else self.id)
        words = int(self.filler.get("words", 500))
        needle = self.filler["needle"]
        at = float(self.filler.get("needle_at", 0.5))

        pool = [
            "A reunião de diretoria foi remarcada para a semana seguinte sem justificativa formal.",
            "Os indicadores de produtividade permaneceram estáveis ao longo do período analisado.",
            "Houve revisão do cronograma de manutenção preventiva dos equipamentos do galpão.",
            "O time de suporte registrou um volume maior de chamados na segunda-feira.",
            "As notas fiscais de setembro foram conciliadas com o extrato bancário da conta principal.",
            "A migração do sistema legado segue em fase de testes controlados com usuários-chave.",
            "O inventário do almoxarifado apresentou divergência de três unidades na contagem cega.",
            "Foi aprovada a contratação de dois analistas para a área de qualidade.",
            "A fornecedora confirmou a entrega parcial dos insumos para a próxima quinta-feira.",
            "O comitê reforçou a necessidade de documentar os processos antes da auditoria externa.",
        ]

        body: List[str] = []
        count = 0
        while count < words:
            body.append(rng.choice(pool))
            count += len(body[-1].split())

        idx = max(1, int(len(body) * at))
        body.insert(idx, needle)
        return self.prompt.replace("{{FILLER}}", " ".join(body))


def load_cases(path: Path = CASES_FILE) -> List[Case]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Case(**c) for c in data["cases"]]


# --------------------------------------------------------------------------
# Correção
# --------------------------------------------------------------------------

def _norm(text: str) -> str:
    return text.strip().lower()


def _strip_fences(text: str) -> str:
    t = text.strip()
    t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    return t.strip()


def _words(text: str) -> int:
    return len(text.split())


def grade(case: Case, answer: str) -> Tuple[bool, List[str]]:
    """Devolve (passou, lista de motivos de falha)."""
    exp = case.expect
    text = answer.strip()
    low = _norm(text)
    problems: List[str] = []

    if not text:
        return False, ["resposta vazia"]

    for token in exp.get("must_include", []):
        if _norm(token) not in low:
            problems.append(f"faltou incluir {token!r}")

    for group in exp.get("must_include_any", []):
        if not any(_norm(t) in low for t in group):
            problems.append(f"faltou um de {group}")

    for token in exp.get("must_exclude", []):
        if _norm(token) in low:
            problems.append(f"incluiu proibido {token!r}")

    for pattern in exp.get("regex", []):
        if not re.search(pattern, text, re.MULTILINE):
            problems.append(f"não casou regex {pattern!r}")

    if "word_count" in exp and _words(text) != exp["word_count"]:
        problems.append(f"palavras={_words(text)} (esperado {exp['word_count']})")
    if "max_words" in exp and _words(text) > exp["max_words"]:
        problems.append(f"palavras={_words(text)} > máximo {exp['max_words']}")
    if "min_words" in exp and _words(text) < exp["min_words"]:
        problems.append(f"palavras={_words(text)} < mínimo {exp['min_words']}")

    if exp.get("json_valid"):
        try:
            payload = json.loads(_strip_fences(text))
        except Exception as exc:
            problems.append(f"JSON inválido: {exc}")
        else:
            if isinstance(payload, dict):
                for key in exp.get("json_keys", []):
                    if key not in payload:
                        problems.append(f"JSON sem chave {key!r}")
            else:
                problems.append("JSON não é objeto")

    return (not problems), problems


# --------------------------------------------------------------------------
# Chamada de API
# --------------------------------------------------------------------------

def call_api(model: str, prompt: str, max_tokens: int = 1024,
             temperature: float = 0.0) -> Tuple[Optional[str], Optional[str]]:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None, "ANTHROPIC_API_KEY não definida"

    body = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        return None, f"HTTP {exc.code}: {detail}"
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"

    parts = [b.get("text", "") for b in payload.get("content", []) if b.get("type") == "text"]
    return "".join(parts), None


# --------------------------------------------------------------------------
# Saída
# --------------------------------------------------------------------------

def _print_case(case: Case, index: int, total: int, seed: Optional[int]) -> None:
    print("=" * 72)
    print(f"[{case.id}] {case.category}  (peso {case.weight:g})  {index}/{total}")
    print("=" * 72)
    print(case.build_prompt(seed))
    print()
    print(f"{DIM}o que observar: {case.why}{OFF}")
    print()


def summarise(results: List[Tuple[Case, bool, List[str]]]) -> None:
    if not results:
        return
    total_w = sum(c.weight for c, _, _ in results)
    got_w = sum(c.weight for c, ok, _ in results if ok)
    by_cat: Dict[str, List[bool]] = {}
    for c, ok, _ in results:
        by_cat.setdefault(c.category, []).append(ok)

    print()
    print("=" * 72)
    print(f"{'categoria':<20} {'acertos':>10}   barra")
    print("-" * 72)
    for cat in sorted(by_cat):
        marks = by_cat[cat]
        good = sum(marks)
        bar = "█" * good + "░" * (len(marks) - good)
        print(f"{cat:<20} {good:>4}/{len(marks):<5}   {bar}")
    print("-" * 72)
    pct = 100 * got_w / total_w if total_w else 0
    print(f"{'TOTAL (ponderado)':<20} {got_w:>6.1f}/{total_w:<4.0f}   {pct:.1f}%")
    print("=" * 72)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _select(cases: List[Case], args: argparse.Namespace) -> List[Case]:
    out = cases
    if getattr(args, "case", None):
        wanted = set(args.case)
        out = [c for c in out if c.id in wanted]
        missing = wanted - {c.id for c in out}
        if missing:
            print(f"casos inexistentes: {sorted(missing)}", file=sys.stderr)
    if getattr(args, "only", None):
        out = [c for c in out if c.category == args.only]
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_eval",
        description="Roda o banco de testes de prompt e pontua o modelo.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--case", nargs="+", help="ids específicos")
        p.add_argument("--only", help="filtrar por categoria")

    p_list = sub.add_parser("list", help="listar casos e categorias")
    add_common(p_list)

    p_print = sub.add_parser("print", help="imprimir prompts para colar manualmente")
    add_common(p_print)
    p_print.add_argument("--seed", type=int, help="semente fixa do texto de preenchimento")

    p_run = sub.add_parser("run", help="chamar a API e pontuar")
    add_common(p_run)
    p_run.add_argument("--model", default=DEFAULT_MODEL)
    p_run.add_argument("--json-out", help="salvar resultados em JSON")
    p_run.add_argument("--show-answer", action="store_true", help="imprimir a resposta completa")
    p_run.add_argument("--seed", type=int)

    p_grade = sub.add_parser("grade", help="pontuar respostas que já estão em arquivos")
    add_common(p_grade)
    p_grade.add_argument("--responses", required=True, help="diretório com <id>.txt")
    p_grade.add_argument("--json-out")

    args = parser.parse_args(argv)
    cases = _select(load_cases(), args)

    if not cases:
        print("nenhum caso selecionado", file=sys.stderr)
        return 2

    if args.cmd == "list":
        for c in cases:
            print(f"{c.id:<8} {c.category:<16} peso {c.weight:g}   {c.why}")
        print(f"\n{len(cases)} caso(s)")
        return 0

    if args.cmd == "print":
        for i, c in enumerate(cases, 1):
            _print_case(c, i, len(cases), args.seed)
        return 0

    results: List[Tuple[Case, bool, List[str]]] = []

    if args.cmd == "run":
        print(f"modelo: {args.model}\n")
        for c in cases:
            answer, err = call_api(args.model, c.build_prompt(args.seed))
            if err:
                print(f"{FAIL} {c.id:<8} erro: {err}")
                results.append((c, False, [err]))
                continue
            ok, problems = grade(c, answer or "")
            print(f"{PASS if ok else FAIL} {c.id:<8} {c.category:<16}"
                  f" {_words(answer or ''):>4} palavras")
            for p in problems:
                print(f"       - {p}")
            if args.show_answer:
                print(f"{DIM}{answer}{OFF}\n")
            results.append((c, ok, problems))

    if args.cmd == "grade":
        root = Path(args.responses)
        if not root.is_dir():
            print(f"não é diretório: {root}", file=sys.stderr)
            return 2
        for c in cases:
            f = root / f"{c.id}.txt"
            if not f.exists():
                print(f"{DIM}SKIP {c.id:<8} sem arquivo{OFF}")
                continue
            answer = f.read_text(encoding="utf-8", errors="replace")
            ok, problems = grade(c, answer)
            print(f"{PASS if ok else FAIL} {c.id:<8} {c.category:<16}")
            for p in problems:
                print(f"       - {p}")
            results.append((c, ok, problems))

    summarise(results)

    if getattr(args, "json_out", None):
        payload = [
            {"id": c.id, "category": c.category, "weight": c.weight,
             "pass": ok, "problems": problems}
            for c, ok, problems in results
        ]
        Path(args.json_out).write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                                       encoding="utf-8")
        print(f"\ngravado em {args.json_out}")

    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
