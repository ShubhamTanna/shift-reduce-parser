"""Grammar-aware lexical analysis for tokens and arithmetic source examples."""
from __future__ import annotations
from dataclasses import dataclass
import re
from grammar import Grammar, EOF


class LexError(ValueError):
    pass


@dataclass(frozen=True)
class Token:
    symbol: str
    lexeme: str
    position: int


def lex(source: str, grammar: Grammar) -> list[Token]:
    if EOF in source:
        raise LexError("'$' is added automatically; remove it from the source input.")
    terminals = grammar.terminals
    literal_terms = sorted(terminals - {'id', 'num'}, key=lambda s: (-len(s), s))
    tokens = []
    i = 0
    while i < len(source):
        if source[i].isspace():
            i += 1
            continue
        tail = source[i:]
        match_word = re.match(r'[A-Za-z_][A-Za-z_0-9]*', tail)
        match_number = re.match(r'(?:\d+(?:\.\d+)?|\.\d+)', tail)

        if match_word:
            word = match_word.group(0)
            if word in terminals:
                tokens.append(Token(word, word, i))
                i += len(word)
                continue
            if 'id' in terminals:
                tokens.append(Token('id', word, i))
                i += len(word)
                continue
        if match_number:
            num = match_number.group(0)
            if num in terminals:
                tokens.append(Token(num, num, i))
                i += len(num)
                continue
            if 'num' in terminals:
                tokens.append(Token('num', num, i))
                i += len(num)
                continue

        terminal = next((t for t in literal_terms if tail.startswith(t)), None)
        if terminal:
            tokens.append(Token(terminal, terminal, i))
            i += len(terminal)
            continue
        context = source[max(0, i - 6):min(len(source), i + 12)]
        raise LexError(f"Cannot tokenize input at index {i} (near {context!r}). "
                       f"Expected terminals: {', '.join(sorted(terminals)) or '(none)'}.")
    if len(tokens) > 300:
        raise LexError('Limit: 300 input tokens.')
    return tokens
