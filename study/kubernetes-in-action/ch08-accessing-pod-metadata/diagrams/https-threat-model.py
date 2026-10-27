#!/usr/bin/env python3
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

FONT = 'AppleGothic'
plt.rcParams['font.family'] = FONT
plt.rcParams['axes.unicode_minus'] = False

BG, PANEL, DEEP = '#1a1a2e', '#16213e', '#0d1f3c'
CYAN, GOLD, LIGHT, TEXT, GREEN, DIM, RED = '#00d4ff', '#ffd700', '#7fdbff', '#e6edf3', '#00ff88', '#5e7290', '#e63946'

fig, ax = plt.subplots(figsize=(16, 5.4))
ax.set_xlim(0, 16)
ax.set_ylim(0, 5.4)
ax.axis('off')
fig.patch.set_facecolor(BG)

ax.text(4.0, 5.05, 'HTTP라면 (가상)',
        fontsize=22, color=RED, fontweight='bold',
        fontfamily=FONT, ha='center', va='center')
ax.text(12.0, 5.05, 'HTTPS (현재)',
        fontsize=22, color=GREEN, fontweight='bold',
        fontfamily=FONT, ha='center', va='center')

ax.plot([8.0, 8.0], [0.3, 4.7], color=DIM, lw=1.5, linestyle=':')

def draw_node(cx, cy, w, h, label, edge):
    ax.add_patch(FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0.04,rounding_size=0.12",
        facecolor=PANEL, edgecolor=edge, linewidth=2.5))
    ax.text(cx, cy, label,
            fontsize=16, color=edge, fontweight='bold',
            fontfamily=FONT, ha='center', va='center')

draw_node(1.6, 3.5, 1.6, 1.0, 'Pod', LIGHT)
draw_node(6.4, 3.5, 1.6, 1.0, 'apiserver', GOLD)

ax.annotate('', xy=(5.6, 3.5), xytext=(2.4, 3.5),
            arrowprops=dict(
                arrowstyle='-|>,head_length=0.55,head_width=0.35',
                color=RED, lw=3.5, shrinkA=0, shrinkB=0))
ax.text(4.0, 3.85, 'Authorization: Bearer eyJ...',
        fontsize=12, color=RED, fontfamily='Menlo',
        ha='center', va='bottom')
ax.text(4.0, 3.18, '평문 — 네트워크 어디서든 보임',
        fontsize=12, color=RED, fontfamily=FONT,
        ha='center', va='top', style='italic')

attacker_x, attacker_y = 4.0, 1.7
ax.add_patch(FancyBboxPatch(
    (attacker_x - 1.5, attacker_y - 0.5), 3.0, 1.0,
    boxstyle="round,pad=0.04,rounding_size=0.12",
    facecolor=DEEP, edgecolor=RED, linewidth=2.5, linestyle='--'))
ax.text(attacker_x, attacker_y + 0.18, '도청자',
        fontsize=15, color=RED, fontweight='bold',
        fontfamily=FONT, ha='center', va='center')
ax.text(attacker_x, attacker_y - 0.22, '(노드 간 네트워크)',
        fontsize=11, color=RED, fontfamily=FONT,
        ha='center', va='center')

ax.annotate('', xy=(attacker_x, attacker_y + 0.55), xytext=(4.0, 3.15),
            arrowprops=dict(
                arrowstyle='-|>,head_length=0.45,head_width=0.3',
                color=RED, lw=2.5, linestyle='--', shrinkA=0, shrinkB=0))
ax.text(5.05, 2.45, '토큰 탈취',
        fontsize=12, color=RED, fontweight='bold',
        fontfamily=FONT, ha='left', va='center')

ax.text(4.0, 0.65, '→ SA 권한 전체 탈취\n→ 만료까지 자유롭게 재사용',
        fontsize=12, color=RED, fontfamily=FONT,
        ha='center', va='center', linespacing=1.5)

draw_node(9.6, 3.5, 1.6, 1.0, 'Pod', LIGHT)
draw_node(14.4, 3.5, 1.6, 1.0, 'apiserver', GOLD)

ax.annotate('', xy=(13.6, 3.5), xytext=(10.4, 3.5),
            arrowprops=dict(
                arrowstyle='-|>,head_length=0.55,head_width=0.35',
                color=GREEN, lw=3.5, shrinkA=0, shrinkB=0))
ax.text(12.0, 3.85, '암호화된 TLS',
        fontsize=14, color=GREEN, fontweight='bold',
        fontfamily=FONT, ha='center', va='bottom')
ax.text(12.0, 3.18, 'ca.crt로 서버 인증서 검증',
        fontsize=12, color=TEXT, fontfamily=FONT,
        ha='center', va='top', style='italic')

ax.text(12.0, 2.4, '✓ 토큰 헤더 암호화\n✓ MITM 방지 (SAN 검증)\n✓ kubernetes.default.svc → 10.96.0.1',
        fontsize=12, color=GREEN, fontfamily=FONT,
        ha='center', va='center', linespacing=1.7)

ax.text(12.0, 0.85, 'v1.20+: insecure port (8080) 코드 제거 · v1.24+: 플래그 제거',
        fontsize=12, color=LIGHT, fontfamily=FONT,
        ha='center', va='center', style='italic')

plt.tight_layout(pad=0.3)
plt.savefig(
    '/Users/wonjunchoi/study/study/kubernetes-in-action/ch08-accessing-pod-metadata/diagrams/https-threat-model.png',
    dpi=200, facecolor=BG, bbox_inches='tight', pad_inches=0.25)
plt.close()
print('saved https-threat-model.png')
