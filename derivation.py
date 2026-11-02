"""Correct parse-tree-based rightmost derivations and Graphviz DOT output."""
from dataclasses import dataclass
from parser import ParseNode


@dataclass(frozen=True)
class DerivationStep:
    sentential_form: str
    rule_applied: str


def _format_symbols(symbols: list[str], compact: bool) -> str:
    if not symbols:
        return 'ε'
    return ''.join(symbols) if compact else ' '.join(symbols)


def rightmost_derivation(root: ParseNode) -> list[DerivationStep]:
    """Expand the rightmost pending nonterminal in the *actual* parse tree.

    This prevents the original project's rule-first loop from choosing
    productions that do not derive the accepted input (or never terminating).
    """
    frontier = [root]
    raw: list[tuple[list[str], str]] = [([root.symbol], 'Start')]
    for _ in range(10000):
        idx = next((i for i in range(len(frontier) - 1, -1, -1)
                    if frontier[i].production is not None), None)
        if idx is None:
            # One spacing style for the whole derivation: compact only when every
            # symbol in every step is a single character (e.g. S => AB => pq).
            compact = all(len(sym) == 1 for form, _ in raw for sym in form)
            return [DerivationStep(_format_symbols(form, compact), rule) for form, rule in raw]
        node = frontier[idx]
        frontier[idx:idx + 1] = list(node.children)
        raw.append(([n.symbol for n in frontier], str(node.production)))
    raise RuntimeError('Derivation exceeded safety limit.')


def to_dot(root: ParseNode) -> str:
    """Create self-contained DOT (Graphviz) markup; no graphviz Python dependency."""
    lines = [
        'digraph ParseTree {',
        'rankdir=TB; bgcolor="transparent";',
        'node [fontname="Helvetica", fontsize=12, style="filled", color="#7090aa"];',
        'edge [color="#7b8fa3"];',
    ]
    serial = [0]

    def escape(value: str) -> str:
        return value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')

    def walk(node: ParseNode) -> int:
        nid = serial[0]
        serial[0] += 1
        label = node.symbol
        if node.lexeme is not None and node.lexeme != node.symbol:
            label += f'\\n{node.lexeme}'
        shape = 'box' if node.production else 'ellipse'
        fill = '#dbeafe' if node.production else '#dcfce7'
        lines.append(f'n{nid} [label="{escape(label)}", shape={shape}, fillcolor="{fill}"];')
        if node.production is not None and not node.children:
            eid = serial[0]
            serial[0] += 1
            lines.append(f'n{eid} [label="ε", shape=plaintext];')
            lines.append(f'n{nid} -> n{eid};')
        for child in node.children:
            cid = walk(child)
            lines.append(f'n{nid} -> n{cid};')
        return nid

    walk(root)
    lines.append('}')
    return '\n'.join(lines)
