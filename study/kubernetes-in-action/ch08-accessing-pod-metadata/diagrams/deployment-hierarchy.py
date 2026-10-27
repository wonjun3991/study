#!/usr/bin/env python3
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

FONT = 'AppleGothic'
plt.rcParams['font.family'] = FONT
plt.rcParams['axes.unicode_minus'] = False

BG, PANEL = '#1a1a2e', '#16213e'
CYAN, GOLD, LIGHT, TEXT, GREEN, DIM = '#00d4ff', '#ffd700', '#7fdbff', '#e6edf3', '#00ff88', '#5e7290'

fig, ax = plt.subplots(figsize=(16, 5.2))
ax.set_xlim(0, 16)
ax.set_ylim(0, 5.2)
ax.axis('off')
fig.patch.set_facecolor(BG)

layers = [
    {'title': 'Deployment',  'role': '원하는 상태 선언\n(replicas: 3, image: ...)',                 'edge': GOLD,  'manages': '관리'},
    {'title': 'ReplicaSet',  'role': '실제 개수 유지\n(살아있는 Pod 수 == replicas)',                'edge': CYAN,  'manages': '생성'},
    {'title': 'Pod',         'role': '스케줄링 단위\n(metadata.name, IP, labels)',                  'edge': LIGHT, 'manages': '실행'},
    {'title': 'Container',   'role': '실제 프로세스\n(image, env, volumeMounts)',                   'edge': GREEN, 'manages': None},
]

box_w = 3.2
box_h = 3.4
gap = 0.7
y_box = 1.1
total_w = box_w * len(layers) + gap * (len(layers) - 1)
x0 = (16 - total_w) / 2

box_xs = []
for i, L in enumerate(layers):
    x = x0 + i * (box_w + gap)
    box_xs.append(x)
    ax.add_patch(FancyBboxPatch(
        (x, y_box), box_w, box_h,
        boxstyle="round,pad=0.05,rounding_size=0.18",
        facecolor=PANEL, edgecolor=L['edge'], linewidth=3.0))
    ax.text(x + box_w / 2, y_box + box_h - 0.55, L['title'],
            fontsize=24, color=L['edge'], fontweight='bold',
            fontfamily=FONT, ha='center', va='center')
    ax.text(x + box_w / 2, y_box + box_h / 2 - 0.15, L['role'],
            fontsize=15, color=TEXT, fontfamily=FONT,
            ha='center', va='center', linespacing=1.45)

y_arrow = y_box + box_h / 2
for i in range(len(layers) - 1):
    x_s = box_xs[i] + box_w + 0.04
    x_e = box_xs[i + 1] - 0.04
    ax.annotate('', xy=(x_e, y_arrow), xytext=(x_s, y_arrow),
                arrowprops=dict(
                    arrowstyle='-|>,head_length=0.6,head_width=0.4',
                    color=GOLD, lw=4.0, shrinkA=0, shrinkB=0))
    if layers[i]['manages']:
        ax.text((x_s + x_e) / 2, y_arrow + 0.40, layers[i]['manages'],
                fontsize=15, color=GOLD, fontweight='bold',
                fontfamily=FONT, ha='center', va='bottom')

ax.text(8.0, 0.55,
        '우리가 만드는 건 보통 Deployment · Pod은 자동 생성됨 → metadata.name도 매번 다름',
        fontsize=15, color=LIGHT, fontfamily=FONT,
        ha='center', va='center', style='italic')

ax.text(8.0, 4.85,
        'kubectl apply -f deployment.yaml',
        fontsize=15, color=GREEN, fontfamily='Menlo',
        ha='center', va='center')

plt.tight_layout(pad=0.3)
plt.savefig(
    '/Users/wonjunchoi/study/study/kubernetes-in-action/ch08-accessing-pod-metadata/diagrams/deployment-hierarchy.png',
    dpi=200, facecolor=BG, bbox_inches='tight', pad_inches=0.25)
plt.close()
print('saved deployment-hierarchy.png')
