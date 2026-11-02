"""Run the educational parser without Streamlit. Zero external dependencies."""
from __future__ import annotations
import argparse
from grammar import parse_grammar, prefix_warnings
from lexer import lex
from parser import SLRParser
from derivation import rightmost_derivation
from ir import generate_tac, optimize_tac, UnsupportedExpression
from samples import EXAMPLES


def run(grammar_text: str, source: str, start: str | None = None):
    grammar = parse_grammar(grammar_text, start)
    parser = SLRParser(grammar)
    tokens = lex(source, grammar)
    print('TOKENS:', ' '.join(f'{t.symbol}[{t.lexeme}]' for t in tokens) or '(empty)')
    print(f'SLR STATES: {len(parser.states)}')
    for hint in prefix_warnings(grammar):
        print('HINT:', hint)
    for (state, terminal), actions in sorted(parser.conflicts.items()):
        print('CONFLICT:', f'state {state} / {terminal}:',
              ' vs '.join(sorted(parser.action_description(a) for a in actions)))
    result = parser.parse(tokens)
    print(f"\n{'#':<4} {'STATE STACK':<22} {'SYMBOLS':<22} {'INPUT':<22} ACTION")
    for step in result.trace:
        print(f'{step.step:<4} {" ".join(map(str, step.states)):<22} '
              f'{" ".join(step.symbols):<22} {" ".join(step.remaining):<22} {step.action}')
    print('\nSTATUS:', result.status.upper(), '-', result.message)
    if result.root:
        print('RIGHTMOST DERIVATION:')
        for step in rightmost_derivation(result.root):
            print('  ', step.sentential_form, '  ', step.rule_applied)
        try:
            tac = generate_tac(result.root)
            print('THREE-ADDRESS CODE:')
            for line in tac.instructions:
                print('  ', line)
            print('  result =', tac.result)
            optimized = optimize_tac(tac)
            print('OPTIMIZED:')
            for line in optimized.instructions:
                print('  ', line)
            print('  result =', optimized.result)
        except UnsupportedExpression:
            pass
    return result.status


if __name__ == '__main__':
    arg = argparse.ArgumentParser(description='Shift-reduce compiler design laboratory')
    arg.add_argument('--example', type=int, default=3, help='Example number 1–9')
    arg.add_argument('--source', help='Override the example source')
    arg.add_argument('--grammar-file', help='Path to a UTF-8 grammar file')
    arg.add_argument('--start', help='Start nonterminal (default: first production)')
    args = arg.parse_args()
    exs = list(EXAMPLES.values())
    if not 1 <= args.example <= len(exs):
        arg.error(f'--example must be between 1 and {len(exs)}')
    ex = exs[args.example - 1]
    grammar = open(args.grammar_file, encoding='utf-8').read() if args.grammar_file else ex['grammar']
    run(grammar, args.source if args.source is not None else ex['source'],
        args.start or (None if args.grammar_file else ex['start']))
