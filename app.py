"""Interactive SLR(1) shift-reduce compiler design laboratory.

Run: streamlit run app.py
"""
from __future__ import annotations
import csv
from io import StringIO
import streamlit as st
from grammar import GrammarError, parse_grammar, prefix_warnings, EOF
from lexer import LexError, lex
from parser import SLRParser, ParserError
from derivation import rightmost_derivation, to_dot
from ir import generate_tac, optimize_tac, UnsupportedExpression
from samples import EXAMPLES

st.set_page_config(page_title='Shift–Reduce Compiler Lab', page_icon='🧩',
                   layout='wide', initial_sidebar_state='expanded')
st.markdown('''
<style>
.block-container {padding-top: 1.6rem; padding-bottom: 4rem;}
.stApp h1 {letter-spacing: -0.04em;}
.status {border-radius: .5rem; padding: .7rem 1rem; margin: .6rem 0 1.2rem;}
.small-note {opacity: .77; font-size: .9rem;}
</style>
''', unsafe_allow_html=True)

example_name = list(EXAMPLES)[2]
default = EXAMPLES[example_name]
for key, value in {'selected_example': example_name, 'grammar_text': default['grammar'],
                   'source_text': default['source'], 'start_symbol': default['start'],
                   'bundle': None}.items():
    if key not in st.session_state:
        st.session_state[key] = value

with st.sidebar:
    st.header('Example library')
    selected = st.selectbox('Load a prepared case', list(EXAMPLES), key='selected_example')
    st.caption(EXAMPLES[selected]['description'])
    if st.button('Load selected example', use_container_width=True):
        example = EXAMPLES[selected]
        st.session_state.grammar_text = example['grammar']
        st.session_state.source_text = example['source']
        st.session_state.start_symbol = example['start']
        st.session_state.bundle = None
        st.rerun()
    st.divider()
    st.markdown('**Notation**')
    st.code('E -> E + T | T\nT -> T * F | F\nF -> ( E ) | id | num', language='text')
    st.caption('Separate symbols with spaces. Compact rules such as S -> AB and E -> E+T also work. Use ε for an empty RHS.')
    st.caption('`id` matches identifier names; `num` matches numeric literals. The end marker `$` is automatic.')
    st.divider()
    st.caption('Based on the supplied Compiler Design mini-project, rebuilt with an SLR(1) engine.')

st.title('Shift–Reduce Compiler Lab')
st.markdown('Explore **lexical analysis → SLR(1) syntax analysis → parse tree / rightmost derivation → three-address code → optimization**.')
st.caption('An educational compiler pipeline for custom context-free grammars. TAC/optimization apply only to supported arithmetic expressions.')

with st.form('parse_form'):
    left, right = st.columns([1.55, 1], gap='large')
    with left:
        st.text_area('Grammar productions', key='grammar_text', height=182,
                     help='Use one LHS -> RHS production per line; alternatives with |')
    with right:
        st.text_input('Input string', key='source_text', help='Examples: id+id*id or x*(y+3)')
        st.text_input('Start symbol', key='start_symbol', help='Must match a production LHS')
        st.markdown('<p class="small-note">The app builds an SLR(1) parse table from your grammar, not hard-coded reductions.</p>', unsafe_allow_html=True)
    submitted = st.form_submit_button('Build parse table & run', type='primary', use_container_width=True)

if submitted:
    try:
        g = parse_grammar(st.session_state.grammar_text, st.session_state.start_symbol)
        analyzer = SLRParser(g)
        tokens = lex(st.session_state.source_text, g)
        result = analyzer.parse(tokens)
        st.session_state.bundle = {'grammar': g, 'parser': analyzer, 'tokens': tokens,
                                   'result': result, 'error': None}
    except (GrammarError, ParserError, LexError) as exc:
        st.session_state.bundle = {'error': str(exc)}

bundle = st.session_state.bundle
if not bundle:
    st.info('Choose or edit an example, then click **Build parse table & run**.')
    st.stop()
if bundle.get('error'):
    st.error(bundle['error'])
    st.stop()

g = bundle['grammar']
analyzer = bundle['parser']
tokens = bundle['tokens']
result = bundle['result']

m1, m2, m3, m4 = st.columns(4)
m1.metric('Lexical tokens', len(tokens))
m2.metric('LR(0) states', len(analyzer.states))
m3.metric('Trace actions', len(result.trace) - 1)
m4.metric('SLR conflicts', len(analyzer.conflicts))
if result.status == 'accepted':
    st.success('ACCEPTED — ' + result.message)
elif result.status == 'rejected':
    st.error('REJECTED — ' + result.message)
else:
    st.warning('CONFLICT — ' + result.message)

warnings = prefix_warnings(g)
if warnings:
    with st.expander(f'{len(warnings)} grammar prefix hint(s) (not proof of ambiguity)'):
        for warning in warnings:
            st.write('•', warning)

lex_tab, trace_tab, tree_tab, grammar_tab, ir_tab = st.tabs([
    '1 · Lexer', '2 · Shift / reduce', '3 · Tree & derivation',
    '4 · Grammar & SLR tables', '5 · Intermediate code',
])

with lex_tab:
    st.subheader('Lexical analysis')
    st.write('The input is split into terminal symbols and original lexemes. The parser consumes the **symbols**; TAC uses the **lexemes**.')
    st.dataframe([{'#': i + 1, 'Type / symbol': t.symbol, 'Lexeme': t.lexeme,
                   'Position (0-based)': t.position} for i, t in enumerate(tokens)]
                 or [{'#': '—', 'Type / symbol': '(empty)', 'Lexeme': '', 'Position (0-based)': ''}],
                 use_container_width=True, hide_index=True)
    st.code('  '.join(f'{t.symbol}<{t.lexeme}>' for t in tokens) + f'  {EOF}', language='text')

with trace_tab:
    st.subheader('SLR(1) parsing trace')
    st.write('A state-and-symbol stack evolves via the generated **ACTION** and **GOTO** tables. The `$` marker is never shifted.')
    rows = [{'Step': t.step, 'State stack': ' '.join(map(str, t.states)),
             'Symbol stack': ' '.join(t.symbols), 'Remaining input': ' '.join(t.remaining),
             'Action': t.action} for t in result.trace]
    st.dataframe(rows, use_container_width=True, hide_index=True, height=370)
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    st.download_button('Download parsing trace (CSV)', data=output.getvalue(),
                       file_name='parsing_trace.csv', mime='text/csv')
    st.divider()
    st.markdown('**Inspect an individual transition**')
    step_id = st.slider('Trace step', 0, len(result.trace) - 1, 0, key='step_id')
    step = result.trace[step_id]
    c1, c2 = st.columns(2)
    with c1:
        st.caption('Symbol stack')
        st.code(' '.join(step.symbols), language='text')
        st.caption('State stack')
        st.code(' '.join(map(str, step.states)), language='text')
    with c2:
        st.caption('Remaining lookahead')
        st.code(' '.join(step.remaining), language='text')
        st.caption('Action executed')
        st.info(step.action)

with tree_tab:
    if not result.root:
        st.info('A parse tree and rightmost derivation require a successfully accepted input.')
    else:
        st.subheader('Concrete parse tree')
        dot = to_dot(result.root)
        st.graphviz_chart(dot, use_container_width=True)
        st.download_button('Download tree (.dot)', data=dot,
                           file_name='parse_tree.dot', mime='text/vnd.graphviz')
        st.subheader('Rightmost derivation')
        st.caption('Each step expands the rightmost unresolved nonterminal in the accepted parse tree. Unlike a first-rule heuristic, this exactly derives the accepted token sequence.')
        deriv = rightmost_derivation(result.root)
        st.dataframe([{'#': i, 'Sentential form': d.sentential_form,
                       'Production used': d.rule_applied} for i, d in enumerate(deriv)],
                     hide_index=True, use_container_width=True)
        st.caption('This is a token-level derivation: a lexeme such as `x` appears as the grammar terminal `id`.')

with grammar_tab:
    st.subheader('Grammar analysis')
    pleft, pright = st.columns(2)
    with pleft:
        st.markdown('**Productions**')
        st.code('\n'.join(f'{i}. {p}' for i, p in enumerate(g.productions, 1)), language='text')
        st.markdown('**FIRST sets**')
        st.dataframe([{'Nonterminal': x, 'FIRST': '{ ' + ', '.join(sorted(analyzer.first[x])) + ' }'}
                      for x in sorted(g.nonterminals)], use_container_width=True, hide_index=True)
    with pright:
        st.markdown('**FOLLOW sets**')
        st.dataframe([{'Nonterminal': x, 'FOLLOW': '{ ' + ', '.join(sorted(analyzer.follow[x])) + ' }'}
                      for x in sorted(g.nonterminals)], use_container_width=True, hide_index=True)
        st.markdown('**Symbols**')
        st.write('Terminals:', ', '.join(sorted(g.terminals)) or '(none)')
        st.write('Nonterminals:', ', '.join(sorted(g.nonterminals)))

    st.divider()
    st.subheader('Actual SLR parsing-table conflicts')
    if analyzer.conflicts:
        st.warning('This grammar is not SLR(1). Conflicting ACTION entries are preserved and reported; the parser stops if one is reached.')
        st.dataframe([{'State': state, 'Lookahead': symbol,
                       'Competing actions': '  |  '.join(sorted(analyzer.action_description(a) for a in acts))}
                      for (state, symbol), acts in sorted(analyzer.conflicts.items())],
                     hide_index=True, use_container_width=True)
    else:
        st.success('No SLR(1) table conflicts detected.')

    st.subheader('ACTION / GOTO parse tables')
    terminal_cols = sorted(g.terminals | {EOF})
    nt_cols = sorted(g.nonterminals)
    table_rows = []
    for s in range(len(analyzer.states)):
        row = {'State': s}
        for t in terminal_cols:
            actions = analyzer.actions.get((s, t), set())
            row[f'ACTION[{t}]'] = ' | '.join(sorted(analyzer.action_description(a) for a in actions))
        for nt in nt_cols:
            target = analyzer.gotos.get((s, nt))
            row[f'GOTO[{nt}]'] = str(target) if target is not None else ''
        table_rows.append(row)
    st.dataframe(table_rows, use_container_width=True, hide_index=True, height=360)

    st.subheader('LR(0) item-set explorer')
    state_index = st.selectbox('Inspect automaton state', list(range(len(analyzer.states))),
                               format_func=lambda s: f'I{s}')
    st.code('\n'.join(analyzer.state_items(state_index)), language='text')
    outgoing = sorted((symbol, destination) for (origin, symbol), destination
                      in analyzer.transitions.items() if origin == state_index)
    st.write('Transitions:', ', '.join(f'{symbol} → I{dest}' for symbol, dest in outgoing) or '(none)')

with ir_tab:
    st.subheader('Intermediate code generation & optimization')
    st.caption('A third/fourth compiler phase added beyond the original parser-centric report. Only simple arithmetic grammar shapes are supported.')
    if not result.root:
        st.info('A successfully parsed arithmetic expression is required for TAC generation.')
    else:
        try:
            tac = generate_tac(result.root)
            optimized = optimize_tac(tac)
            a, b = st.columns(2, gap='large')
            with a:
                st.markdown('**Three-address code (TAC)**')
                st.code('\n'.join(map(str, tac.instructions)) + f'\nresult = {tac.result}', language='text')
            with b:
                st.markdown('**Optimized TAC**')
                snippet = '\n'.join(map(str, optimized.instructions))
                st.code((snippet + '\n' if snippet else '') + f'result = {optimized.result}', language='text')
                st.caption('Passes: constant folding, constant propagation, algebraic identities, and dead-temporary elimination. No user code is evaluated.')
        except UnsupportedExpression as exc:
            st.info(f'No TAC for this grammar: {exc}')

st.divider()
st.caption('Educational scope: SLR(1) grammars, not every context-free grammar. A prefix hint does not establish ambiguity; conflicts in this app are computed from the SLR ACTION table.')
