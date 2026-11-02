"""Context-free grammar parsing and FIRST/FOLLOW analysis for the teaching tool."""
from __future__ import annotations
from dataclasses import dataclass
import re

EPSILON = 'ε'
EOF = '$'


class GrammarError(ValueError):
    """Invalid grammar, start symbol, or grammar size."""


@dataclass(frozen=True)
class Production:
    lhs: str
    rhs: tuple[str, ...]

    def __str__(self) -> str:
        return f"{self.lhs} → {' '.join(self.rhs) if self.rhs else EPSILON}"


@dataclass(frozen=True)
class Grammar:
    productions: tuple[Production, ...]
    start: str
    nonterminals: frozenset[str]
    terminals: frozenset[str]

    def for_lhs(self, lhs: str) -> list[Production]:
        return [p for p in self.productions if p.lhs == lhs]


def _compact_symbols(rhs: str, nts: set[str]) -> tuple[str, ...]:
    """Split E+T and AB into symbols, recognizing declared nonterminals."""
    out: list[str] = []
    nonterminals = sorted(nts, key=lambda s: (-len(s), s))
    pos = 0
    while pos < len(rhs):
        n = next((nt for nt in nonterminals if rhs.startswith(nt, pos)), None)
        if n:
            out.append(n)
            pos += len(n)
            continue
        m = re.match(r'[a-z_][a-z_0-9]*|\d+(?:\.\d+)?|==|!=|<=|>=|\S', rhs[pos:])
        if not m:
            raise GrammarError(f"Cannot tokenize production: {rhs!r}")
        out.append(m.group(0))
        pos += len(m.group(0))
    return tuple(out)


def parse_grammar(text: str, start: str | None = None) -> Grammar:
    """Parse one production per line; `|` introduces alternatives.

    Whitespace separates symbols. Compact notation such as E->E+T is also
    supported for common single-letter nonterminals. Empty/ε is epsilon.
    """
    rows: list[tuple[str, str]] = []
    for line_number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if '->' in line:
            parts = line.split('->')
        elif '→' in line:
            parts = line.split('→')
        else:
            raise GrammarError(f"Line {line_number}: expected '->' (for example S -> A B).")
        if len(parts) != 2:
            raise GrammarError(f"Line {line_number}: exactly one arrow is required.")
        lhs, rhs = parts[0].strip(), parts[1].strip()
        if not re.fullmatch(r'[A-Z][A-Za-z_0-9]*', lhs):
            raise GrammarError(f"Line {line_number}: nonterminal must start with A–Z: {lhs!r}.")
        rows.append((lhs, rhs))
    if not rows:
        raise GrammarError('Enter at least one production.')
    if len(rows) > 80:
        raise GrammarError('Limit: 80 production lines.')
    nts = {lhs for lhs, _ in rows}
    start = start.strip() if start else rows[0][0]
    if start not in nts:
        raise GrammarError(f"Start symbol {start!r} has no production.")

    productions: list[Production] = []
    for lhs, alternatives in rows:
        for alt in alternatives.split('|'):
            alt = alt.strip()
            if not alt or alt.lower() in ('epsilon', 'eps') or alt in (EPSILON, 'ε'):
                rhs = ()
            elif any(c.isspace() for c in alt):
                rhs = tuple(alt.split())
            else:
                rhs = _compact_symbols(alt, nts)
            if EOF in rhs:
                raise GrammarError("'$' is reserved as the end-of-input marker.")
            if len(rhs) > 50:
                raise GrammarError('A production may contain at most 50 symbols.')
            if EPSILON in rhs:
                raise GrammarError('Use ε by itself for an empty production.')
            # In spaced grammars, unrecognized capitalized symbols are probably typos.
            undefined = [s for s in rhs if re.match(r'^[A-Z]', s) and s not in nts]
            if undefined:
                raise GrammarError(f"Undefined nonterminal(s) in {lhs}: {', '.join(undefined)}")
            p = Production(lhs, rhs)
            if p not in productions:
                productions.append(p)
    if len(productions) > 150:
        raise GrammarError('Limit: 150 production alternatives.')
    symbols = {symbol for p in productions for symbol in p.rhs}
    return Grammar(tuple(productions), start, frozenset(nts), frozenset(symbols - nts))


def first_sets(g: Grammar) -> dict[str, set[str]]:
    first: dict[str, set[str]] = {nt: set() for nt in g.nonterminals}
    changed = True
    while changed:
        changed = False
        for p in g.productions:
            symbols_first = first_of_sequence(p.rhs, first, g.terminals)
            new = symbols_first - first[p.lhs]
            if new:
                first[p.lhs].update(new)
                changed = True
    return first


def first_of_sequence(seq: tuple[str, ...], first: dict[str, set[str]],
                      terminals: frozenset[str]) -> set[str]:
    if not seq:
        return {EPSILON}
    out: set[str] = set()
    for symbol in seq:
        f = {symbol} if symbol in terminals else first[symbol]
        out |= f - {EPSILON}
        if EPSILON not in f:
            return out
    out.add(EPSILON)
    return out


def follow_sets(g: Grammar, first: dict[str, set[str]]) -> dict[str, set[str]]:
    follow = {nt: set() for nt in g.nonterminals}
    follow[g.start].add(EOF)
    changed = True
    while changed:
        changed = False
        for p in g.productions:
            for i, symbol in enumerate(p.rhs):
                if symbol not in g.nonterminals:
                    continue
                trailing = first_of_sequence(p.rhs[i + 1:], first, g.terminals)
                new = trailing - {EPSILON}
                if EPSILON in trailing:
                    new |= follow[p.lhs]
                addition = new - follow[symbol]
                if addition:
                    follow[symbol].update(addition)
                    changed = True
    return follow


def prefix_warnings(g: Grammar) -> list[str]:
    """Teaching-only heuristic; *not* a formal ambiguity/conflict test."""
    warnings = []
    for nt in sorted(g.nonterminals):
        rules = [p.rhs for p in g.for_lhs(nt)]
        for i, a in enumerate(rules):
            for b in rules[i + 1:]:
                if (len(a) <= len(b) and a == b[:len(a)]) or (len(b) < len(a) and b == a[:len(b)]):
                    sa = ' '.join(a) or EPSILON
                    sb = ' '.join(b) or EPSILON
                    warnings.append(f"Common-prefix hint: {nt} → {sa} / {sb} (not proof of ambiguity).")
    return warnings
