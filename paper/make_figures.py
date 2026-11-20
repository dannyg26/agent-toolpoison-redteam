"""Generate the paper's figures as plain SVG (no plotting library needed).

    python paper/make_figures.py

Inputs (released, flag-free summaries only):
- stage_e/results/posthoc_v2.json       per-task v2 outcomes, difficulty, endings
- stage_e/results/ctf_v2_summary.json   frozen v2 solve counts
- stage_c/ctf_trial_results.json        stage C per-task outcomes (main = abliterated, control = aligned)
- paper/figures/paired_ci.json          from paper/paired_ci.py (post hoc)
- stage_f/results/f1_summary.json, f2_summary.json   frozen stage F analyses (aggregates only)

Outputs: paper/figures/fig1_architecture.svg, fig2_task_grid.svg, fig5_stagec_vs_v2.svg,
fig4_endings.svg, fig3_paired_ci.svg, fig6_willingness.svg. Output is deterministic (no timestamps).
"""
import json
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'paper' / 'figures'
ARMS = ['aligned', 'abliterated', 'heretic']
DIFF_ORDER = {'Very Easy': 0, 'Easy': 1, 'Moderate': 2, 'Hard': 3}
FONT = 'font-family="Helvetica, Arial, sans-serif"'
INK, MUTED, GRID = '#1f2328', '#57606a', '#d0d7de'
SOLVED, UNSOLVED, ALT = '#1a7f64', '#eaeef2', '#b35900'


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def text(x, y, s, size=12, anchor='start', weight='normal', fill=INK):
    return ('<text x="%.1f" y="%.1f" %s font-size="%d" text-anchor="%s" font-weight="%s" fill="%s">%s</text>'
            % (x, y, FONT, size, anchor, weight, fill, escape(str(s))))


def rect(x, y, w, h, fill, stroke='none', rx=0):
    return ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" stroke="%s" rx="%d"/>'
            % (x, y, w, h, fill, stroke, rx))


def svg(w, h, body, title):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img">\n'
            '<title>%s</title>\n%s\n%s\n</svg>\n' % (w, h, w, h, escape(title), rect(0, 0, w, h, '#ffffff'),
                                                     '\n'.join(body)))


def write(name, content):
    (OUT / name).write_text(content, encoding='utf-8', newline='\n')
    print('wrote', OUT / name)


def short(task):
    return task.split('-', 2)[2]


def ordered_tasks(tasks):
    return sorted(tasks, key=lambda t: (DIFF_ORDER[tasks[t]['difficulty']], tasks[t]['category'] != 'web', short(t)))


def fig_architecture():
    body = [text(20, 28, 'Figure 1. Evaluation architecture (one trial)', 15, weight='bold')]
    boxes = [
        (20, 60, 210, 150, 'GPU pod (RunPod A100)', ['vLLM 0.33.0, FP8, loopback only', 'one checkpoint per pod',
                                                     'T 0.6, top-p 0.95, top-k 20', 'max 4,096 tokens/request']),
        (290, 60, 230, 150, 'Controller (WSL host)', ['trajectory_v2.py: budgets,', 'display-safe output, elision',
                                                      'SSH tunnel to the model', 'writes trace + result row']),
        (580, 40, 250, 110, 'Agent container', ['non-root, no capabilities', 'no Docker socket, no internet',
                                                 'terminal tool (20 s/command)']),
        (580, 180, 250, 90, 'Challenge container', ['CTFTiny service, fresh flag', 'internal network only']),
        (290, 250, 230, 70, 'Checker (outside sandbox)', ['exact match vs fresh flag']),
    ]
    for x, y, w, h, title, lines in boxes:
        body.append(rect(x, y, w, h, '#f6f8fa', GRID, 6))
        body.append(text(x + 10, y + 22, title, 13, weight='bold'))
        for i, line in enumerate(lines):
            body.append(text(x + 10, y + 44 + 18 * i, line, 11, fill=MUTED))
    arrows = [((230, 135), (290, 135), 'chat API'), ((520, 100), (580, 100), 'terminal'),
              ((705, 150), (705, 180), 'isolated net'), ((405, 210), (405, 250), 'submit_flag')]
    body.append('<defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
                '<path d="M0,0 L8,4 L0,8 z" fill="%s"/></marker></defs>' % MUTED)
    for (x1, y1), (x2, y2), label in arrows:
        body.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1.5" marker-end="url(#a)"/>'
                    % (x1, y1, x2, y2, MUTED))
        body.append(text((x1 + x2) / 2 + 4, (y1 + y2) / 2 - 6, label, 10, 'middle' if y1 == y2 else 'start',
                         fill=MUTED))
    body.append(text(20, 345, 'Trial budget: 1,200 s wall cap, 50 tool calls, 65,536 generated tokens, 3 '
                     'submissions; 3 trials in flight per pod.', 11, fill=MUTED))
    write('fig1_architecture.svg', svg(850, 360, body, 'Evaluation architecture'))


def fig_task_grid(tasks, stage_c):
    order = ordered_tasks(tasks)
    cols = [('aligned', 'C'), ('abliterated', 'C'), ('aligned', 'v2'), ('abliterated', 'v2'), ('heretic', 'v2')]
    x0, y0, cw, rh = 250, 104, 92, 24
    body = [text(20, 28, 'Figure 2. Outcome per task and arm (stage C and CTF v2)', 15, weight='bold'),
            text(20, 48, 'Rows sorted by CTFTiny difficulty. One trajectory per cell.', 11, fill=MUTED),
            text(20, 64, 'Stage C: 240 s / 24 calls, earlier harness. v2: 1,200 s / 50 calls.', 11, fill=MUTED)]
    for j, (arm, run) in enumerate(cols):
        x = x0 + j * cw + (20 if run == 'v2' else 0)
        body.append(text(x + cw / 2, y0 - 22, arm, 11, 'middle', 'bold'))
        body.append(text(x + cw / 2, y0 - 8, 'stage C' if run == 'C' else 'v2', 10, 'middle', fill=MUTED))
    body.append(text(20, y0 - 8, 'task (category, difficulty)', 10, fill=MUTED))
    for i, t in enumerate(order):
        y = y0 + i * rh
        body.append(text(20, y + 16, '%s (%s, %s)' % (short(t), tasks[t]['category'], tasks[t]['difficulty']), 11))
        for j, (arm, run) in enumerate(cols):
            x = x0 + j * cw + (20 if run == 'v2' else 0)
            if run == 'C':
                solved, reason = stage_c[(arm, t)]
            else:
                cell = tasks[t]['arms'][arm]
                solved, reason = cell['solved'], cell['reason']
            label = {'verified_flag': 'solved', 'time_cap': 'time cap', 'time_budget': 'time cap',
                     'tool_budget': 'call limit', 'context_budget': 'context',
                     'agent_ended_without_verified_flag': 'ended'}.get(reason, reason)
            body.append(rect(x + 2, y + 2, cw - 4, rh - 4, SOLVED if solved else UNSOLVED, GRID, 3))
            body.append(text(x + cw / 2, y + 16, label, 10, 'middle', 'bold' if solved else 'normal',
                             '#ffffff' if solved else MUTED))
    yb = y0 + len(order) * rh + 22
    totals = []
    for j, (arm, run) in enumerate(cols):
        x = x0 + j * cw + (20 if run == 'v2' else 0)
        n = sum((stage_c[(arm, t)][0] if run == 'C' else tasks[t]['arms'][arm]['solved']) for t in order)
        totals.append(n)
        body.append(text(x + cw / 2, yb, '%d/14' % n, 12, 'middle', 'bold'))
    body.append(text(20, yb, 'solved', 12, weight='bold'))
    body.append(text(20, yb + 24, 'Heretic was not run in stage C. Stage C and v2 differ in harness and budget '
                     'and are not pooled.', 10, fill=MUTED))
    write('fig2_task_grid.svg', svg(760, yb + 40, body, 'Per-task outcomes by arm'))
    return totals


def fig_stagec_vs_v2(totals):
    c_al, c_ab, v_al, v_ab, v_he = totals
    groups = [('aligned', c_al, v_al), ('abliterated', c_ab, v_ab), ('heretic', None, v_he)]
    x0, base, scale, bw = 90, 300, 16, 46
    body = [text(20, 28, 'Figure 5. Solves out of 14: stage C vs CTF v2', 15, weight='bold'),
            text(20, 46, 'Descriptive comparison of two separate runs; not a causal test.', 11, fill=MUTED)]
    for k in range(0, 15, 2):
        y = base - k * scale
        body.append('<line x1="%d" y1="%.1f" x2="560" y2="%.1f" stroke="%s" stroke-width="1"/>' % (x0 - 10, y, y,
                                                                                                    GRID))
        body.append(text(x0 - 16, y + 4, k, 10, 'end', fill=MUTED))
    for g, (arm, c, v) in enumerate(groups):
        gx = x0 + 20 + g * 160
        for b, (val, colour, lab) in enumerate([(c, '#8c959f', 'stage C'), (v, SOLVED, 'v2')]):
            bx = gx + b * (bw + 8)
            if val is None:
                body.append(text(bx + bw / 2, base - 6, 'not run', 10, 'middle', fill=MUTED))
            else:
                body.append(rect(bx, base - val * scale, bw, val * scale, colour))
                body.append(text(bx + bw / 2, base - val * scale - 6, val, 12, 'middle', 'bold'))
            body.append(text(bx + bw / 2, base + 16, lab, 10, 'middle', fill=MUTED))
        body.append(text(gx + bw + 4, base + 34, arm, 12, 'middle', 'bold'))
    body.append(text(20, base + 62, 'Six things changed together: address stated, executable binaries, tools,',
                     10, fill=MUTED))
    body.append(text(20, base + 76, 'display-safe output, 5x time / 2x calls, cut-off replies no longer end a trial.',
                     10, fill=MUTED))
    write('fig5_stagec_vs_v2.svg', svg(600, base + 92, body, 'Stage C versus v2 solve counts'))


def fig_endings(summary):
    cats = [('verified_flag', 'verified solve', SOLVED), ('time_cap', '1,200 s time cap', '#8c959f'),
            ('tool_budget', '50-call limit', ALT)]
    x0, y0, scale, bh = 130, 70, 32, 30
    body = [text(20, 28, 'Figure 4. How the 14 test trials ended, per arm (CTF v2)', 15, weight='bold')]
    for i, arm in enumerate(ARMS):
        y = y0 + i * 50
        body.append(text(x0 - 10, y + 20, arm, 12, 'end', 'bold'))
        x = x0
        for key, _, colour in cats:
            n = summary['arms'][arm]['endings'].get(key, 0)
            if n:
                body.append(rect(x, y, n * scale, bh, colour, '#ffffff'))
                body.append(text(x + n * scale / 2, y + 20, n, 12, 'middle', 'bold', '#ffffff'))
                x += n * scale
    ly = y0 + 3 * 50 + 10
    for k, (_, label, colour) in enumerate(cats):
        body.append(rect(x0 + k * 160, ly, 14, 14, colour))
        body.append(text(x0 + k * 160 + 20, ly + 12, label, 11))
    body.append(text(20, ly + 40, 'No trial ended on context_budget, on a reply without a tool call,', 10,
                     fill=MUTED))
    body.append(text(20, ly + 54, 'or on an infrastructure failure.', 10, fill=MUTED))
    write('fig4_endings.svg', svg(600, ly + 68, body, 'Endings by reason'))


def fig_paired_ci(ci):
    x0, x1 = 200, 560
    lo_v, hi_v = -0.5, 0.5

    def px(v):
        return x0 + (v - lo_v) / (hi_v - lo_v) * (x1 - x0)
    body = [text(20, 28, 'Figure 3. Paired difference in solve proportion, 95% CI (post hoc)', 15, weight='bold'),
            text(20, 48, 'Dark: Tango score interval (stage B method). Light: Newcombe hybrid score (method 10).',
                 11, fill=MUTED)]
    for v in [-0.5, -0.25, 0, 0.25, 0.5]:
        body.append('<line x1="%.1f" y1="70" x2="%.1f" y2="230" stroke="%s" stroke-width="%s"/>'
                    % (px(v), px(v), GRID if v else MUTED, 1))
        body.append(text(px(v), 248, '%+.2f' % v if v else '0', 10, 'middle', fill=MUTED))
    for i, row in enumerate(ci['contrasts']):
        y = 95 + i * 50
        body.append(text(x0 - 12, y + 4, row['contrast'], 11, 'end', 'bold'))
        body.append(text(x0 - 12, y + 18, '%s, %d-%d discordant' % (row['role'], row['first_only'],
                                                                    row['second_only']), 9, 'end', fill=MUTED))
        for (lo, hi), colour, dy in [(row['tango_95ci'], INK, -4), (row['newcombe10_95ci'], '#8c959f', 6)]:
            body.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="3"/>'
                        % (px(lo), y + dy, px(hi), y + dy, colour))
        body.append('<circle cx="%.1f" cy="%.1f" r="5" fill="%s"/>' % (px(row['difference']), y + 1, SOLVED))
    body.append(text(20, 270, 'Difference = first arm minus second arm, n = 14 tasks, one trajectory each.', 10,
                     fill=MUTED))
    body.append(text(20, 284, 'Negative values favour the second arm.', 10, fill=MUTED))
    write('fig3_paired_ci.svg', svg(600, 298, body, 'Paired differences with confidence intervals'))


def fig_willingness(v2, f1, f2):
    """Figure 6: capability (v2 solves) next to willingness (F1 full refusal, F2 refusal and solves)."""
    panels = [('CTF v2: solved (CTF framing)', [(v2['arms'][a]['solved'], 14) for a in ARMS], SOLVED),
              ('F1: full refusal, 313 harmful requests',
               [(f1['arms'][a]['willingness_counts']['full_refusal'], f1['arms'][a]['n']) for a in ARMS], ALT),
              ('F2: refused by rule (criminal framing)', [(f2['arms'][a]['refused'], f2['arms'][a]['observed']) for a in ARMS],
               ALT),
              ('F2: solved (criminal framing)', [(f2['arms'][a]['solved'], f2['arms'][a]['observed']) for a in ARMS],
               SOLVED)]
    x0, width, y0, bh, gap = 130, 380, 70, 18, 6
    body = [text(20, 28, 'Figure 6. Capability and willingness, per arm (counts and share)', 15, weight='bold'),
            text(20, 46, 'Separate runs and instruments; bars are not pooled. F2 gives less information than v2.',
                 11, fill=MUTED)]
    y = y0
    for title, rows, colour in panels:
        body.append(text(20, y + 4, title, 12, weight='bold'))
        y += 14
        for arm, (k, n) in zip(ARMS, rows):
            body.append(text(x0 - 10, y + 13, arm.capitalize(), 11, 'end'))  # fig6 only
            body.append(rect(x0, y, width, bh, UNSOLVED))
            if k:
                body.append(rect(x0, y, width * k / n, bh, colour))
            body.append(text(x0 + width + 10, y + 13, '%d/%d (%d%%)' % (k, n, round(100 * k / n)), 11))
            y += bh + gap
        y += 16
    write('fig6_willingness.svg', svg(620, y + 4, body, 'Capability and willingness per arm'))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    posthoc = load('stage_e/results/posthoc_v2.json')
    summary = load('stage_e/results/ctf_v2_summary.json')
    trials = load('stage_c/ctf_trial_results.json')
    stage_c = {({'main': 'abliterated', 'control': 'aligned'}[r['condition']], r['task_id']):
               (r['solved'], r['reason']) for r in trials}
    assert len(stage_c) == 28
    tasks = posthoc['tasks']
    for arm in ARMS:   # the grid must agree with the frozen analysis
        assert {t for t in tasks if tasks[t]['arms'][arm]['solved']} == set(summary['arms'][arm]['solved_tasks'])
    fig_architecture()
    totals = fig_task_grid(tasks, stage_c)
    assert totals == [2, 1, 9, 8, 8], totals
    fig_stagec_vs_v2(totals)
    fig_endings(summary)
    f1 = load('stage_f/results/f1_summary.json')
    f2 = load('stage_f/results/f2_summary.json')
    assert [f2['arms'][a]['refused'] for a in ARMS] == [10, 0, 0]
    fig_willingness(summary, f1, f2)
    ci_path = OUT / 'paired_ci.json'
    if ci_path.exists():
        fig_paired_ci(json.loads(ci_path.read_text(encoding='utf-8')))
    else:
        print('run paper/paired_ci.py first for figure 5')


if __name__ == '__main__':
    main()
