# Compiler Design Project — Implementation Walkthrough

## 1. From the report to an executable project

My original 2024 report describes a **shift–reduce parser** that reads user-provided production rules, prints stack/input/actions, detects apparent grammar conflicts, and produces rightmost derivations. It also includes a Streamlit proof of concept. This implementation keeps the teaching objective and replaces the fragile greedy reductions with an **SLR(1) table-driven engine**. It additionally demonstrates **four** compiler phases to exceed the assignment's requirement of integrating at least three.

### Phase 1 — Lexical analysis

**Question:** What are the smallest meaningful terminal units in the source?

The lexer scans source characters and returns `Token(symbol, lexeme, position)` objects. In the grammar `F -> id | num`, the input `x+42` becomes:

```text
id[x]    +[+]    num[42]
```

A **lexeme** is the actual text (such as `x`); the **token type** or terminal symbol is `id`. The parser uses token *types*. Three-address-code generation uses lexemes.

### Phase 2 — Syntax analysis (SLR shift/reduce)

1. Parse the CFG: read `LHS -> RHS1 | RHS2` alternatives.
2. Compute the `FIRST` sets (tokens that can start a derivation).
3. Compute the `FOLLOW` sets (lookaheads that can follow nonterminals).
4. Add a new initial rule `S' -> S`.
5. Build the canonical LR(0) automaton using **closure** and **goto**.
6. Build the SLR(1) ACTION/GOTO tables:
   - LR(0) transitions on terminals produce **shift** entries.
   - Completed items `A -> α •` produce **reduce** entries on all terminals in `FOLLOW(A)`.
   - Completed augmented start item produces **accept** on `$`.
7. Parse with a **stack of symbols** and a **stack of states**. Preserve every stack snapshot for visualization.
8. If the applicable ACTION cell contains multiple actions, report a **conflict**; never arbitrarily pick a path.

For the report's grammar:

```text
S -> A B
A -> p
B -> q
```

Input: `pq`.

Expected conceptual trace (numeric state IDs may vary with construction order):

```text
$         pq$   Initialize
$p        q$    Shift p
$A        q$    Reduce A -> p
$Aq       $     Shift q
$AB       $     Reduce B -> q
$S        $     Reduce S -> A B
$S        $     Accept
```

### Phase 3 — Intermediate code generation

For this grammar:

```text
E -> E + T | T
T -> T * F | F
F -> ( E ) | id | num
```

The input `id+id*id` is parsed according to precedence: `(id)+(id*id)`. The TAC is:

```text
t1 = id * id
t2 = id + t1
result = t2
```

This step is intentionally defined only for arithmetic grammar shapes. There is no meaningful executable code to generate for an arbitrary language like `S -> A B` without adding semantics.

### Phase 4 — Code optimization

Input `2+3*4` yields:

```text
t1 = 3 * 4
t2 = 2 + t1
result = t2
```

Constant folding and propagation reduce it to:

```text
result = 14
```

Unused intermediate variables are removed after propagation.

## 2. Parse tree and rightmost derivation

The report notes that a parse-tree feature was attempted but dropped because some outputs were incorrect. Here, every parser reduction constructs a **tree node with the actual children popped from the stack**.

For `S -> A B`, `A -> p`, `B -> q`, the resulting tree is:

```text
       S
      / \
     A   B
     |   |
     p   q
```

Expanding the **rightmost unexpanded nonterminal** in that tree gives:

```text
S ⇒ AB ⇒ Aq ⇒ pq
```

This avoids the original rightmost-derivation loop's weakness: always choosing the first available production can derive the wrong string or loop indefinitely.

## 3. Grammar conflicts: important terminology

**The original prefix check is a heuristic, not a grammar-ambiguity detector.** Example:

```text
S -> A a | A
A -> b
```

The two `S` alternatives share a prefix `A`, but this grammar has no conflict in its SLR(1) ACTION table. Conversely, the grammar below has real **shift/reduce** conflicts:

```text
E -> E + E | E * E | id
```

And this grammar has a real **reduce/reduce** conflict:

```text
S -> A | B
A -> id
B -> id
```

In the Streamlit app, open **Grammar & SLR tables** to inspect exact conflicting state/lookahead cells.

An SLR conflict does **not** by itself prove a grammar is ambiguous; some unambiguous grammars require more powerful parsing methods, such as canonical LR(1).

## 4. How to demo this in 4 minutes

1. **Example 01:** Show input `pq` being accepted, each stack movement, and `S ⇒ AB ⇒ Aq ⇒ pq`.
2. **Example 03:** Show FIRST/FOLLOW and ACTION/GOTO; demonstrate that `*` is reduced before the outer `+`.
3. **Example 05:** Show `2+3*4` converted into TAC, then optimized to `14`.
4. **Example 07:** Show a syntax error for `id+*id` and the parser's expected symbols.
5. **Example 08:** Show conflicting SLR ACTION cells for an ambiguous arithmetic grammar.

## 5. Questions to expect in a viva

**Why is SLR safer than the original greedy algorithm?** A generated ACTION table incorporates LR(0) parser states and FOLLOW-based lookahead; it does not reduce every matching suffix immediately.

**Why are there two stacks?** The symbol stack visualizes grammar recognition; the state stack determines which ACTION/GOTO transition is valid.

**Why is `$` in the input?** `$` indicates end of input. The augmented start rule must finish with `$` as lookahead to accept. It is not a normal input token to be shifted.

**What's the difference between shift/reduce and reduce/reduce conflicts?** Shift/reduce means both shifting a lookahead and reducing a rule are permitted in one ACTION cell. Reduce/reduce means two different rules both request reductions in the same cell.

**Why not generate TAC from every grammar?** A CFG specifies syntax, not semantics. TAC generation requires known arithmetic operators and operand meaning.

**Where are the parser's limits?** SLR(1) grammars; compact terminals and generic `id`/`num` only; arithmetic-only TAC; no machine-code backend.
