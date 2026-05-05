#!/usr/bin/env python3
"""AI slop vicious cycle — 2x2 grid with clear directional arrows forming a loop."""
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

FONT = 'AppleGothic'
plt.rcParams['font.family'] = FONT
plt.rcParams['axes.unicode_minus'] = False

fig, ax = plt.subplots(figsize=(9, 8))
ax.set_xlim(0, 9)
ax.set_ylim(0, 8)
ax.axis('off')
fig.patch.set_facecolor('#1a1a2e')

ACCENT = '#fca311'
BOX_BG = '#2d1f10'
SUB_COLOR = '#ffd9a0'

box_w = 3.6
box_h = 1.7
gap_x = 0.6
gap_y = 1.4

y_center = 4.0
x_center = 4.5
x_left = x_center - gap_x / 2 - box_w
x_right = x_center + gap_x / 2
y_top = y_center + gap_y / 2
y_bottom = y_center - gap_y / 2 - box_h

stages = [
    (x_left,  y_top,    '① 반복 개선',     '기능 추가 · 문서 보강'),
    (x_right, y_top,    '② 문서 비대',     '중복 · 미사용 누적'),
    (x_right, y_bottom, '③ 토큰 과소비',   '작업 속도 저하'),
    (x_left,  y_bottom, '④ 정리는 뒷전',   '또 쌓기만 반복'),
]

for (x, y, title, sub) in stages:
    ax.add_patch(Rectangle(
        (x, y), box_w, box_h,
        facecolor=BOX_BG, edgecolor=ACCENT, linewidth=3.0
    ))
    ax.text(x + box_w / 2, y + box_h - 0.55, title,
            fontsize=22, color='#ffffff', fontweight='bold',
            fontfamily=FONT, ha='center', va='center')
    ax.text(x + box_w / 2, y + 0.5, sub,
            fontsize=15, color=SUB_COLOR,
            fontfamily=FONT, ha='center', va='center', fontstyle='italic')

arrow_style = dict(
    arrowstyle='-|>,head_length=0.55,head_width=0.38',
    color=ACCENT, lw=4.2,
    shrinkA=0, shrinkB=0,
)

ax.annotate('',
    xy=(x_right - 0.05, y_top + box_h / 2),
    xytext=(x_left + box_w + 0.05, y_top + box_h / 2),
    arrowprops=arrow_style)

ax.annotate('',
    xy=(x_right + box_w / 2, y_bottom + box_h + 0.05),
    xytext=(x_right + box_w / 2, y_top - 0.05),
    arrowprops=arrow_style)

ax.annotate('',
    xy=(x_left + box_w + 0.05, y_bottom + box_h / 2),
    xytext=(x_right - 0.05, y_bottom + box_h / 2),
    arrowprops=arrow_style)

ax.annotate('',
    xy=(x_left + box_w / 2, y_top - 0.05),
    xytext=(x_left + box_w / 2, y_bottom + box_h + 0.05),
    arrowprops=arrow_style)

ax.text(x_center, y_center, 'LOOP', fontsize=42, color=ACCENT,
        ha='center', va='center',
        fontweight='bold', alpha=0.3,
        family='sans-serif')

plt.tight_layout(pad=0.2)
plt.savefig('ai-slop-cycle.png', dpi=200, facecolor='#1a1a2e',
            bbox_inches='tight', pad_inches=0.2)
plt.close()
print("✅ ai-slop-cycle.png 생성 완료")
