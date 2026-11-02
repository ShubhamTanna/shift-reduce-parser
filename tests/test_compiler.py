"""Run with: python -m unittest discover -s tests -v"""
import unittest
from grammar import GrammarError, parse_grammar, prefix_warnings
from lexer import lex, LexError
from parser import SLRParser
from derivation import rightmost_derivation, to_dot
from ir import generate_tac, optimize_tac, UnsupportedExpression
from samples import EXAMPLES


class CompilerLabTests(unittest.TestCase):
    def do_example(self, number):
        ex = list(EXAMPLES.values())[number - 1]
        grammar = parse_grammar(ex['grammar'], ex['start'])
        parser = SLRParser(grammar)
        result = parser.parse(lex(ex['source'], grammar))
        return grammar, parser, result

    def test_report_pq(self):
        _, parser, result = self.do_example(1)
        self.assertFalse(parser.conflicts)
        self.assertEqual(result.status, 'accepted')
        self.assertEqual(result.trace[-1].category, 'accept')
        forms = [s.sentential_form for s in rightmost_derivation(result.root)]
        self.assertEqual(forms[0], 'S')
        self.assertEqual(forms[-1], 'pq')

    def test_report_one_plus_zero(self):
        _, parser, result = self.do_example(2)
        self.assertFalse(parser.conflicts)
        self.assertEqual(result.status, 'accepted')
        ir = generate_tac(result.root)
        self.assertEqual(optimize_tac(ir).result, '1')

    def test_arithmetic_precedence(self):
        _, parser, result = self.do_example(3)
        self.assertFalse(parser.conflicts)
        self.assertEqual(result.status, 'accepted')
        tac = generate_tac(result.root)
        self.assertEqual(len(tac.instructions), 2)
        self.assertEqual(tac.instructions[0].op, '*')
        self.assertEqual(tac.instructions[1].op, '+')
        self.assertEqual(rightmost_derivation(result.root)[-1].sentential_form, 'id + id * id')
        self.assertIn('digraph ParseTree', to_dot(result.root))

    def test_parentheses_lexemes(self):
        g, parser, r = self.do_example(4)
        self.assertEqual(r.status, 'accepted')
        self.assertEqual([t.lexeme for t in lex('x*(y+3)', g)], ['x', '*', '(', 'y', '+', '3', ')'])
        tac = generate_tac(r.root)
        self.assertEqual(tac.instructions[0].op, '+')
        self.assertEqual(tac.instructions[1].op, '*')

    def test_constant_folding(self):
        _, _, r = self.do_example(5)
        tac = generate_tac(r.root)
        optimized = optimize_tac(tac)
        self.assertEqual(optimized.result, '14')
        self.assertEqual(len(optimized.instructions), 0)

    def test_epsilon(self):
        _, _, r = self.do_example(6)
        self.assertEqual(r.status, 'accepted')
        self.assertTrue(any('ε' in t.action for t in r.trace))
        self.assertEqual(rightmost_derivation(r.root)[-1].sentential_form, 'b')
        with self.assertRaises(UnsupportedExpression):
            generate_tac(r.root)

    def test_syntax_rejection(self):
        _, _, r = self.do_example(7)
        self.assertEqual(r.status, 'rejected')
        self.assertIsNone(r.root)
        self.assertIn('Expected', r.message)

    def test_shift_reduce_conflicts(self):
        _, parser, r = self.do_example(8)
        self.assertTrue(parser.conflicts)
        self.assertEqual(r.status, 'conflict')
        self.assertTrue(any({a[0] for a in actions} == {'reduce', 'shift'}
                            for actions in parser.conflicts.values()))

    def test_reduce_reduce_conflicts(self):
        _, parser, r = self.do_example(9)
        self.assertTrue(parser.conflicts)
        self.assertEqual(r.status, 'conflict')
        self.assertTrue(any(sum(a[0] == 'reduce' for a in acts) > 1
                            for acts in parser.conflicts.values()))

    def test_common_prefix_not_necessarily_slr_conflict(self):
        g = parse_grammar('S -> A a | A\nA -> b')
        self.assertTrue(prefix_warnings(g))
        parser = SLRParser(g)
        self.assertFalse(parser.conflicts)
        self.assertEqual(parser.parse(lex('ba', g)).status, 'accepted')
        self.assertEqual(parser.parse(lex('b', g)).status, 'accepted')

    def test_compact_notation(self):
        g = parse_grammar('S->AB\nA->p\nB->q')
        self.assertEqual(g.productions[0].rhs, ('A', 'B'))
        self.assertEqual(SLRParser(g).parse(lex('pq', g)).status, 'accepted')

    def test_start_symbol_not_hardcoded(self):
        g = parse_grammar('E -> id')
        self.assertEqual(SLRParser(g).parse(lex('name', g)).status, 'accepted')

    def test_input_validation(self):
        for code in ['S A', 'S -> X', 'S -> id ε', 'S -> id $', '']:
            with self.subTest(code=code), self.assertRaises(GrammarError):
                parse_grammar(code)
        g = parse_grammar('S -> a')
        with self.assertRaises(LexError):
            lex('a$', g)
        with self.assertRaises(LexError):
            lex('?', g)

    def test_empty_input_with_epsilon(self):
        g = parse_grammar('S -> ε')
        r = SLRParser(g).parse(lex('', g))
        self.assertEqual(r.status, 'accepted')
        self.assertEqual(rightmost_derivation(r.root)[-1].sentential_form, 'ε')

    def test_no_code_execution(self):
        g = parse_grammar('S -> id')
        with self.assertRaises(LexError):
            lex('__import__("os")', g)


if __name__ == '__main__':
    unittest.main()
