"""Optional arithmetic three-address-code generation and safe optimization.

Works only for accepted trees whose shapes represent standard expressions:
  ( expression ), expression + expression, etc., plus atomic literals/ids.
Arbitrary CFGs intentionally have no executable semantics in this demo.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, DivisionByZero
from parser import ParseNode

BINARY = frozenset({'+', '-', '*', '/'})


@dataclass(frozen=True)
class Instruction:
    target: str
    lhs: str
    op: str = 'copy'
    rhs: str = ''

    def __str__(self) -> str:
        if self.op == 'copy':
            return f'{self.target} = {self.lhs}'
        if self.op == 'neg':
            return f'{self.target} = -{self.lhs}'
        return f'{self.target} = {self.lhs} {self.op} {self.rhs}'


@dataclass(frozen=True)
class IRResult:
    instructions: tuple[Instruction, ...]
    result: str


class UnsupportedExpression(ValueError):
    pass


def generate_tac(root: ParseNode) -> IRResult:
    instructions: list[Instruction] = []

    def emit(node: ParseNode) -> str:
        if node.production is None:
            if node.symbol in {'(', ')', '+', '-', '*', '/'}:
                raise UnsupportedExpression('Operators/parentheses are not standalone expressions.')
            return node.lexeme or node.symbol
        children = node.children
        if len(children) == 1:
            return emit(children[0])
        if len(children) == 3 and children[0].symbol == '(' and children[2].symbol == ')':
            return emit(children[1])
        if len(children) == 3 and children[1].symbol in BINARY:
            left = emit(children[0])
            right = emit(children[2])
            target = f't{len(instructions) + 1}'
            instructions.append(Instruction(target, left, children[1].symbol, right))
            return target
        if len(children) == 2 and children[0].symbol == '-':
            arg = emit(children[1])
            target = f't{len(instructions) + 1}'
            instructions.append(Instruction(target, arg, 'neg'))
            return target
        raise UnsupportedExpression(f'Rule {node.production} does not describe a supported arithmetic expression.')

    result = emit(root)
    if not instructions:
        raise UnsupportedExpression('The accepted input contains no arithmetic operation.')
    return IRResult(tuple(instructions), result)


def _number(text: str) -> Decimal | None:
    try:
        value = Decimal(text)
        return value if value.is_finite() else None
    except (InvalidOperation, TypeError):
        return None


def _format_decimal(number: Decimal) -> str:
    if number == number.to_integral_value():
        return str(number.quantize(Decimal('1')))
    return format(number.normalize(), 'f')


def optimize_tac(ir: IRResult) -> IRResult:
    """Constant propagation/folding, simple identities, and dead temp removal.

    This assumes a pure arithmetic grammar, without assignments or side effects.
    Division by zero is left untouched. A Decimal context is used rather than eval.
    """
    substitution: dict[str, str] = {}
    cleaned: list[Instruction] = []

    def resolve(value: str) -> str:
        seen = set()
        while value in substitution and value not in seen:
            seen.add(value)
            value = substitution[value]
        return value

    for ins in ir.instructions:
        lhs = resolve(ins.lhs)
        rhs = resolve(ins.rhs) if ins.rhs else ''
        a, b = _number(lhs), _number(rhs) if rhs else None
        replacement: str | None = None
        if ins.op == 'copy':
            replacement = lhs
        elif ins.op == 'neg' and a is not None:
            replacement = _format_decimal(-a)
        elif ins.op in BINARY:
            if a is not None and b is not None:
                try:
                    calculated = {'+': lambda: a + b, '-': lambda: a - b,
                                  '*': lambda: a * b, '/': lambda: a / b}[ins.op]()
                    if calculated.is_finite():
                        replacement = _format_decimal(calculated)
                except (DivisionByZero, ZeroDivisionError, InvalidOperation):
                    pass
            elif ins.op == '+' and b == 0:
                replacement = lhs
            elif ins.op == '+' and a == 0:
                replacement = rhs
            elif ins.op == '-' and b == 0:
                replacement = lhs
            elif ins.op == '*' and b == 1:
                replacement = lhs
            elif ins.op == '*' and a == 1:
                replacement = rhs
            elif ins.op == '/' and b == 1:
                replacement = lhs
        if replacement is not None:
            substitution[ins.target] = replacement
        else:
            cleaned.append(Instruction(ins.target, lhs, ins.op, rhs))

    output = resolve(ir.result)
    # Retain only computations contributing to the final result.
    live = {output}
    result: list[Instruction] = []
    for ins in reversed(cleaned):
        if ins.target not in live:
            continue
        result.append(ins)
        live.discard(ins.target)
        live.add(ins.lhs)
        if ins.rhs:
            live.add(ins.rhs)
    result.reverse()
    return IRResult(tuple(result), output)
