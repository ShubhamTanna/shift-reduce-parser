"""Canonical LR(0) automaton, SLR(1) parse table and shift-reduce trace."""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from typing import Literal
from grammar import Grammar, Production, EOF, first_sets, follow_sets
from lexer import Token

Action = tuple[str, int | None]
Item = tuple[int, int]  # (production index, position of dot)


class ParserError(ValueError):
    pass


@dataclass(frozen=True)
class ParseNode:
    symbol: str
    children: tuple['ParseNode', ...] = ()
    lexeme: str | None = None
    production: Production | None = None


@dataclass(frozen=True)
class TraceStep:
    step: int
    states: tuple[int, ...]
    symbols: tuple[str, ...]
    remaining: tuple[str, ...]
    action: str
    category: str


@dataclass
class ParseResult:
    status: Literal['accepted', 'rejected', 'conflict']
    message: str
    trace: list[TraceStep]
    root: ParseNode | None


class SLRParser:
    def __init__(self, grammar: Grammar):
        self.grammar = grammar
        self.first = first_sets(grammar)
        self.follow = follow_sets(grammar, self.first)
        augmented_lhs = "__START__"
        while augmented_lhs in grammar.nonterminals or augmented_lhs in grammar.terminals:
            augmented_lhs += '_'
        self.rules = [Production(augmented_lhs, (grammar.start,))] + list(grammar.productions)
        self.rules_by_lhs: dict[str, list[int]] = {}
        for i, p in enumerate(self.rules):
            self.rules_by_lhs.setdefault(p.lhs, []).append(i)
        self.states: list[frozenset[Item]] = []
        self.transitions: dict[tuple[int, str], int] = {}
        self.actions: dict[tuple[int, str], set[Action]] = {}
        self.gotos: dict[tuple[int, str], int] = {}
        self._construct()
        self.conflicts = {key: acts for key, acts in self.actions.items() if len(acts) > 1}

    def _closure(self, items: set[Item]) -> frozenset[Item]:
        closure = set(items)
        queue = deque(items)
        while queue:
            rule_id, dot = queue.popleft()
            rhs = self.rules[rule_id].rhs
            if dot == len(rhs):
                continue
            symbol = rhs[dot]
            for new_id in self.rules_by_lhs.get(symbol, []):
                item = (new_id, 0)
                if item not in closure:
                    closure.add(item)
                    queue.append(item)
        return frozenset(closure)

    def _goto(self, items: frozenset[Item], symbol: str) -> frozenset[Item]:
        moved = {(rid, dot + 1) for rid, dot in items
                 if dot < len(self.rules[rid].rhs) and self.rules[rid].rhs[dot] == symbol}
        return self._closure(moved) if moved else frozenset()

    def _add_action(self, state: int, terminal: str, action: Action):
        self.actions.setdefault((state, terminal), set()).add(action)

    def _construct(self):
        initial = self._closure({(0, 0)})
        self.states = [initial]
        indices = {initial: 0}
        queue = deque([0])
        while queue:
            state = queue.popleft()
            items = self.states[state]
            next_symbols = sorted({self.rules[rid].rhs[dot] for rid, dot in items
                                   if dot < len(self.rules[rid].rhs)})
            for symbol in next_symbols:
                destination = self._goto(items, symbol)
                if destination not in indices:
                    if len(self.states) >= 400:
                        raise ParserError('Grammar too complex (more than 400 LR(0) states).')
                    indices[destination] = len(self.states)
                    self.states.append(destination)
                    queue.append(indices[destination])
                self.transitions[(state, symbol)] = indices[destination]

        for state, items in enumerate(self.states):
            for rid, dot in items:
                prod = self.rules[rid]
                if dot < len(prod.rhs):
                    symbol = prod.rhs[dot]
                    target = self.transitions[(state, symbol)]
                    if symbol in self.grammar.terminals:
                        self._add_action(state, symbol, ('shift', target))
                    else:
                        self.gotos[(state, symbol)] = target
                elif rid == 0:
                    self._add_action(state, EOF, ('accept', None))
                else:
                    for terminal in self.follow[prod.lhs]:
                        self._add_action(state, terminal, ('reduce', rid))

    def action_description(self, act: Action) -> str:
        operation, val = act
        if operation == 'shift':
            return f'shift → state {val}'
        if operation == 'reduce':
            return f'reduce {self.rules[val]}'
        return 'accept'

    def state_items(self, state: int) -> list[str]:
        result = []
        for rid, dot in sorted(self.states[state]):
            production = self.rules[rid]
            rhs = list(production.rhs)
            rhs.insert(dot, '•')
            result.append(f"{production.lhs} → {' '.join(rhs)}")
        return result

    def parse(self, tokens: list[Token], max_steps: int = 10000) -> ParseResult:
        state_stack = [0]
        symbol_stack = [EOF]
        node_stack: list[ParseNode] = []
        stream = tokens + [Token(EOF, EOF, -1)]
        cursor = 0
        trace: list[TraceStep] = []

        def record(action: str, category: str):
            trace.append(TraceStep(len(trace), tuple(state_stack), tuple(symbol_stack),
                                   tuple(t.symbol for t in stream[cursor:]), action, category))

        record('Initialize stack with $ and state 0', 'start')
        for _ in range(max_steps):
            state = state_stack[-1]
            lookahead = stream[cursor]
            actions = self.actions.get((state, lookahead.symbol), set())
            if not actions:
                expected = sorted(t for (s, t) in self.actions if s == state and t != EOF)
                if (state, EOF) in self.actions:
                    expected += [EOF]
                where = f"index {lookahead.position}" if lookahead.position >= 0 else 'end of input'
                message = (f"Syntax error near {lookahead.lexeme!r} at {where}. "
                           f"Expected one of: {', '.join(expected) or '(none)'}. ")
                record(message, 'error')
                return ParseResult('rejected', message, trace, None)
            if len(actions) > 1:
                descriptions = ' OR '.join(sorted(self.action_description(a) for a in actions))
                message = f"SLR conflict in state {state} on lookahead {lookahead.symbol!r}: {descriptions}."
                record(message, 'conflict')
                return ParseResult('conflict', message, trace, None)
            operation, value = next(iter(actions))
            if operation == 'shift':
                symbol_stack.append(lookahead.symbol)
                node_stack.append(ParseNode(lookahead.symbol, lexeme=lookahead.lexeme))
                state_stack.append(value)
                cursor += 1
                record(f"Shift {lookahead.symbol} ({lookahead.lexeme!r}) → state {value}", 'shift')
            elif operation == 'reduce':
                p = self.rules[value]
                count = len(p.rhs)
                children = tuple(node_stack[-count:]) if count else ()
                if count:
                    del node_stack[-count:]
                    del symbol_stack[-count:]
                    del state_stack[-count:]
                parent = ParseNode(p.lhs, children, production=p)
                target = self.gotos.get((state_stack[-1], p.lhs))
                if target is None:
                    raise ParserError(f'Missing GOTO after {p}; internal table error.')
                node_stack.append(parent)
                symbol_stack.append(p.lhs)
                state_stack.append(target)
                record(f'Reduce by {p} → GOTO state {target}', 'reduce')
            else:
                record('ACCEPT: start symbol recognized; input fully consumed', 'accept')
                if len(node_stack) != 1 or node_stack[0].symbol != self.grammar.start:
                    raise ParserError('Parser accepted without a valid root node.')
                return ParseResult('accepted', 'Input accepted by the SLR(1) parser.', trace, node_stack[0])
        raise ParserError(f'Parsing stopped after {max_steps} actions (safety limit).')
