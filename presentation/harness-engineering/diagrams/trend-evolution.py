#!/usr/bin/env python3
"""트렌드 변화 다이어그램 — 미니멀: 흰 테두리 직사각형 + 화살표"""
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

FONT = 'AppleGothic'
plt.rcParams['font.family'] = FONT
plt.rcParams['axes.unicode_minus'] = False

fig, ax = plt.subplots(1, 1, figsize=(16, 6.5))
ax.set_xlim(0, 16)
ax.set_ylim(0, 6.5)
ax.axis('off')
fig.patch.set_facecolor('#1a1a2e')

box_w = 2.8
box_h = 4.8
gap = 1.0
total_w = box_w * 4 + gap * 3
x_start_offset = (16 - total_w) / 2

# (title, subtitle, highlight)
contents = [
    ('Prompt\nEngineering',     '프롬프트를 잘 쓰자',    False),
    ('Context\nEngineering',    '맥락을 잘 주자',        False),
    ('Spec-Driven\nDevelopment', '명세를 잘 정의하자',    False),
    ('Harness\nEngineering',    '환경을 설계하자',       True),
]

boxes = []
for i, (title, subtitle, highlight) in enumerate(contents):
    x = x_start_offset + i * (box_w + gap)
    boxes.append((x, title, subtitle, highlight))

y_base = 0.8

for (x, title, subtitle, highlight) in boxes:
    edge_color = '#ffd700' if highlight else '#ffffff'
    title_color = '#ffd700' if highlight else '#ffffff'
    lw = 3.5 if highlight else 2.2

    rect = Rectangle(
        (x, y_base), box_w, box_h,
        facecolor='none', edgecolor=edge_color, linewidth=lw
    )
    ax.add_patch(rect)

    ax.text(x + box_w / 2, y_base + box_h / 2 + 0.7, title,
            fontsize=28, color=title_color, fontweight='bold',
            fontfamily=FONT, ha='center', va='center', linespacing=1.3)

    ax.text(x + box_w / 2, y_base + 0.75, subtitle,
            fontsize=18, color='#e0e0e0',
            fontfamily=FONT, ha='center', va='center')

for i in range(3):
    x_start = boxes[i][0] + box_w + 0.12
    x_end = boxes[i + 1][0] - 0.12
    y_mid = y_base + box_h / 2
    ax.annotate('',
                xy=(x_end, y_mid),
                xytext=(x_start, y_mid),
                arrowprops=dict(
                    arrowstyle='-|>,head_length=0.7,head_width=0.45',
                    color='#ffd700',
                    lw=4.0,
                    shrinkA=0, shrinkB=0,
                ))

plt.tight_layout(pad=0.3)
plt.savefig('trend-evolution.png', dpi=200, facecolor='#1a1a2e',
            bbox_inches='tight', pad_inches=0.25)
plt.close()
print("✅ trend-evolution.png 생성 완료")
