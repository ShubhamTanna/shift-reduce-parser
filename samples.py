"""Examples from the project report plus richer compiler-design test cases."""
EXAMPLES = {
    '01 · Two symbols (report example)': {
        'grammar': 'S -> A B\nA -> p\nB -> q',
        'source': 'pq',
        'start': 'S',
        'description': 'Bottom-up reductions: p→A; q→B; A B→S.',
    },
    '02 · One plus zero (report example)': {
        'grammar': 'S -> A + B\nA -> 1\nB -> 0',
        'source': '1+0',
        'start': 'S',
        'description': 'Shows shifts, reductions, a tree, a rightmost derivation, and TAC.',
    },
    '03 · Operator precedence': {
        'grammar': 'E -> E + T | T\nT -> T * F | F\nF -> ( E ) | id | num',
        'source': 'id+id*id',
        'start': 'E',
        'description': 'Demonstrates that multiplication binds tighter than addition.',
    },
    '04 · Nested parentheses': {
        'grammar': 'E -> E + T | T\nT -> T * F | F\nF -> ( E ) | id | num',
        'source': 'x*(y+3)',
        'start': 'E',
        'description': 'Generic id/num terminals also accept actual identifiers and numbers.',
    },
    '05 · Constant folding': {
        'grammar': 'E -> E + T | T\nT -> T * F | F\nF -> ( E ) | id | num',
        'source': '2+3*4',
        'start': 'E',
        'description': 'TAC followed by constant folding: final result is 14.',
    },
    '06 · Empty production (epsilon)': {
        'grammar': 'S -> A B\nA -> a | ε\nB -> b',
        'source': 'b',
        'start': 'S',
        'description': 'An SLR grammar with an epsilon reduction.',
    },
    '07 · Invalid expression': {
        'grammar': 'E -> E + T | T\nT -> T * F | F\nF -> ( E ) | id | num',
        'source': 'id+*id',
        'start': 'E',
        'description': 'Demonstrates a syntax error with the expected lookahead set.',
    },
    '08 · Shift/reduce conflict': {
        'grammar': 'E -> E + E | E * E | id',
        'source': 'id+id*id',
        'start': 'E',
        'description': 'Ambiguous expression grammar; see actual SLR conflicts.',
    },
    '09 · Reduce/reduce conflict': {
        'grammar': 'S -> A | B\nA -> id\nB -> id',
        'source': 'id',
        'start': 'S',
        'description': 'Two different productions reduce on the same lookahead.',
    },
}
