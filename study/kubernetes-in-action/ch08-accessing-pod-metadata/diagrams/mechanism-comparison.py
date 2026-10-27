#!/usr/bin/env python3
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

FONT = 'AppleGothic'
plt.rcParams['font.family'] = FONT
plt.rcParams['axes.unicode_minus'] = False

BG, PANEL = '#1a1a2e', '#16213e'
CYAN, GOLD, LIGHT, TEXT, GREEN, DIM, RED = '#00d4ff', '#ffd700', '#7fdbff', '#e6edf3', '#00ff88', '#5e7290', '#e63946'

fig, ax = plt.subplots(figsize=(16, 5.2))
ax.set_xlim(0, 16)
ax.set_ylim(0, 5.2)
ax.axis('off')
fig.patch.set_facecolor(BG)

ax.text(4.0, 4.75, 'Downward API',
        fontsize=24, color=CYAN, fontweight='bold',
        fontfamily=FONT, ha='center', va='center')
ax.text(12.0, 4.75, 'API Server 호출',
        fontsize=24, color=GOLD, fontweight='bold',
        fontfamily=FONT, ha='center', va='center')

ax.plot([8.0, 8.0], [0.3, 4.5], color=DIM, lw=1.5, linestyle=':')

left_x, left_y = 0.6, 0.5
left_w, left_h = 6.8, 3.9
ax.add_patch(FancyBboxPatch(
    (left_x, left_y), left_w, left_h,
    boxstyle="round,pad=0.05,rounding_size=0.18",
    facecolor=PANEL, edgecolor=CYAN, linewidth=2.5))

right_x, right_y = 8.6, 0.5
right_w, right_h = 6.8, 3.9
ax.add_patch(FancyBboxPatch(
    (right_x, right_y), right_w, right_h,
    boxstyle="round,pad=0.05,rounding_size=0.18",
    facecolor=PANEL, edgecolor=GOLD, linewidth=2.5))

left_lines = [
    ('읽기 1줄', GREEN, FONT, 17, 'bold'),
    ("os.Getenv(\"POD_NAME\")", LIGHT, 'Menlo', 15, 'normal'),
    ('', None, None, 0, None),
    ('통신 0회', GREEN, FONT, 17, 'bold'),
    ('kubelet이 이미 주입', TEXT, FONT, 15, 'normal'),
    ('', None, None, 0, None),
    ('인증 불필요', GREEN, FONT, 17, 'bold'),
    ('TLS · 토큰 · RBAC 없음', TEXT, FONT, 15, 'normal'),
    ('', None, None, 0, None),
    ('지연 ≈ 0', GREEN, FONT, 17, 'bold'),
]

y_cursor = left_y + left_h - 0.45
for txt, col, fam, sz, w in left_lines:
    if txt:
        ax.text(left_x + 0.4, y_cursor, txt,
                fontsize=sz, color=col, fontweight=w,
                fontfamily=fam, ha='left', va='top')
    y_cursor -= 0.32

right_lines = [
    ('읽기 5+줄', RED, FONT, 17, 'bold'),
    ('token = open(...).read()', LIGHT, 'Menlo', 13, 'normal'),
    ('ca = "/var/run/.../ca.crt"', LIGHT, 'Menlo', 13, 'normal'),
    ('headers = {Authorization: ...}', LIGHT, 'Menlo', 13, 'normal'),
    ('requests.get(url, verify=ca)', LIGHT, 'Menlo', 13, 'normal'),
    ('', None, None, 0, None),
    ('통신 1회', RED, FONT, 17, 'bold'),
    ('Pod → kube-proxy → apiserver', TEXT, FONT, 14, 'normal'),
    ('', None, None, 0, None),
    ('인증 필수', RED, FONT, 17, 'bold'),
    ('TLS · Bearer · RBAC', TEXT, FONT, 14, 'normal'),
    ('', None, None, 0, None),
    ('지연 ≈ 수십 ms (네트워크)', RED, FONT, 17, 'bold'),
]

y_cursor = right_y + right_h - 0.45
for txt, col, fam, sz, w in right_lines:
    if txt:
        ax.text(right_x + 0.4, y_cursor, txt,
                fontsize=sz, color=col, fontweight=w,
                fontfamily=fam, ha='left', va='top')
    y_cursor -= 0.27

ax.text(4.0, 0.18,
        '"내" 정보면 충분 → 이 길로',
        fontsize=15, color=GREEN, fontweight='bold',
        fontfamily=FONT, ha='center', va='center')
ax.text(12.0, 0.18,
        '"남"의 정보 필요할 때만',
        fontsize=15, color=GOLD, fontweight='bold',
        fontfamily=FONT, ha='center', va='center')

plt.tight_layout(pad=0.3)
plt.savefig(
    '/Users/wonjunchoi/study/study/kubernetes-in-action/ch08-accessing-pod-metadata/diagrams/mechanism-comparison.png',
    dpi=200, facecolor=BG, bbox_inches='tight', pad_inches=0.25)
plt.close()
print('saved mechanism-comparison.png')
