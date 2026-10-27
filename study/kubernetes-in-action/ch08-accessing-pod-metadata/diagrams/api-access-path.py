#!/usr/bin/env python3
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

FONT = 'AppleGothic'
plt.rcParams['font.family'] = FONT
plt.rcParams['axes.unicode_minus'] = False

BG, PANEL = '#1a1a2e', '#16213e'
CYAN, GOLD, LIGHT, TEXT, GREEN = '#00d4ff', '#ffd700', '#7fdbff', '#e6edf3', '#00ff88'

fig, ax = plt.subplots(figsize=(16, 4.6))
ax.set_xlim(0, 16)
ax.set_ylim(0, 4.6)
ax.axis('off')
fig.patch.set_facecolor(BG)

box_h = 2.4
gap = 2.0
y_box = 1.3
box_widths = [3.0, 4.4, 3.0]
total_w = sum(box_widths) + gap * (len(box_widths) - 1)
x0 = (16 - total_w) / 2

boxes = [
    {'title': 'Pod', 'subtitle': '앱 컨테이너', 'edge': CYAN, 'title_size': 24},
    {'title': 'kubernetes.default.svc', 'subtitle': '클러스터 항상 존재\n(고정 DNS)', 'edge': LIGHT, 'title_size': 22},
    {'title': 'apiserver', 'subtitle': 'Kubernetes\nControl Plane', 'edge': GOLD, 'title_size': 24},
]

box_xs = []
cursor = x0
for i, b in enumerate(boxes):
    bw = box_widths[i]
    box_xs.append(cursor)
    ax.add_patch(FancyBboxPatch(
        (cursor, y_box), bw, box_h,
        boxstyle="round,pad=0.05,rounding_size=0.18",
        facecolor=PANEL, edgecolor=b['edge'], linewidth=3.0))
    ax.text(cursor + bw / 2, y_box + box_h - 0.75, b['title'],
            fontsize=b['title_size'], color=b['edge'], fontweight='bold',
            fontfamily=FONT, ha='center', va='center')
    ax.text(cursor + bw / 2, y_box + box_h / 2 - 0.35, b['subtitle'],
            fontsize=17, color=TEXT, fontfamily=FONT,
            ha='center', va='center', linespacing=1.35)
    cursor += bw + gap

y_arrow = y_box + box_h / 2

arrows = [
    {'from_idx': 0, 'to_idx': 1, 'top': 'HTTPS', 'top_color': GOLD,
     'bottom': '+ Bearer token', 'bottom_color': GREEN, 'bottom_size': 16},
    {'from_idx': 1, 'to_idx': 2, 'top': 'route', 'top_color': GOLD,
     'bottom': '(ClusterIP)', 'bottom_color': TEXT, 'bottom_size': 15},
]

for a in arrows:
    x_s = box_xs[a['from_idx']] + box_widths[a['from_idx']] + 0.05
    x_e = box_xs[a['to_idx']] - 0.05
    ax.annotate('', xy=(x_e, y_arrow), xytext=(x_s, y_arrow),
                arrowprops=dict(
                    arrowstyle='-|>,head_length=0.7,head_width=0.45',
                    color=GOLD, lw=4.0, shrinkA=0, shrinkB=0))
    ax.text((x_s + x_e) / 2, y_arrow + 0.55, a['top'],
            fontsize=20, color=a['top_color'], fontweight='bold',
            fontfamily=FONT, ha='center', va='bottom')
    ax.text((x_s + x_e) / 2, y_arrow - 0.55, a['bottom'],
            fontsize=a['bottom_size'], color=a['bottom_color'], fontfamily=FONT,
            ha='center', va='top')

ax.text(8.0, 0.4,
        '모든 Pod에서 도달 가능 · DNS는 모든 클러스터에서 동일',
        fontsize=15, color=LIGHT, fontfamily=FONT,
        ha='center', va='center', style='italic')

plt.tight_layout(pad=0.3)
plt.savefig(
    '/Users/wonjunchoi/study/study/kubernetes-in-action/ch08-accessing-pod-metadata/diagrams/api-access-path.png',
    dpi=200, facecolor=BG, bbox_inches='tight', pad_inches=0.25)
plt.close()
print('saved api-access-path.png')
