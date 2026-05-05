#!/usr/bin/env python3
"""Standard workflow diagram — 6-step process with harness-handled tooling per step."""
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

FONT = 'AppleGothic'
plt.rcParams['font.family'] = FONT
plt.rcParams['axes.unicode_minus'] = False

fig, ax = plt.subplots(figsize=(16, 4.8))
ax.set_xlim(0, 16)
ax.set_ylim(0, 4.8)
ax.axis('off')
fig.patch.set_facecolor('#1a1a2e')

steps = [
    ('1',  'Jira 티켓',        'skill:jira'),
    ('2',  '브랜치\n+ worktree', 'skill:git-worktree'),
    ('3',  '코드 작업',         'agent:executor'),
    ('4',  '내부 리뷰',         'skill:ci-review'),
    ('5',  'PR 생성',           'gh cli + 다이어그램'),
    ('6',  'Jira 갱신',         'skill:jira'),
]

box_w = 2.35
box_h = 3.2
gap = 0.3
n = len(steps)
total_w = box_w * n + gap * (n - 1)
x_start = (16 - total_w) / 2
y_base = 0.9

positions = [(x_start + i * (box_w + gap), *s) for i, s in enumerate(steps)]

for (x, num, name, tool) in positions:
    ax.add_patch(Rectangle(
        (x, y_base), box_w, box_h,
        facecolor='none', edgecolor='#ffffff', linewidth=3.0
    ))

    ax.text(x + 0.4, y_base + box_h - 0.45, num,
            fontsize=22, color='#ffd700', fontweight='bold',
            fontfamily=FONT, ha='left', va='center')

    ax.text(x + box_w / 2, y_base + box_h - 1.4, name,
            fontsize=28, color='#ffffff', fontweight='bold',
            fontfamily=FONT, ha='center', va='center', linespacing=1.2)

    ax.text(x + box_w / 2, y_base + 0.6, tool,
            fontsize=19, color='#7fdbff', fontweight='bold',
            fontfamily=FONT, ha='center', va='center',
            linespacing=1.3, fontstyle='italic')

for i in range(n - 1):
    x_s = positions[i][0] + box_w + 0.02
    x_e = positions[i + 1][0] - 0.02
    y_m = y_base + box_h / 2
    ax.annotate('',
        xy=(x_e, y_m), xytext=(x_s, y_m),
        arrowprops=dict(
            arrowstyle='-|>,head_length=0.5,head_width=0.35',
            color='#ffd700', lw=4.0,
            shrinkA=0, shrinkB=0))

ax.text(8, 4.5, '사용자는 "플랜 주기" 한 번  →  나머지는 하네스가 자동 수행',
        fontsize=22, color='#ffd700', fontweight='bold',
        fontfamily=FONT, ha='center', va='center')

ax.text(8, 0.45, '각 단계에서  explore · LSP · oracle · hook  이 병렬 호출',
        fontsize=17, color='#52b788', fontweight='bold',
        fontfamily=FONT, ha='center', va='center', fontstyle='italic')

plt.tight_layout(pad=0.2)
plt.savefig('standard-workflow.png', dpi=200, facecolor='#1a1a2e',
            bbox_inches='tight', pad_inches=0.15)
plt.close()
print("✅ standard-workflow.png 생성 완료")
