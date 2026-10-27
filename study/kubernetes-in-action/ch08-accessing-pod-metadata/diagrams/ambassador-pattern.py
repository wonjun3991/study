#!/usr/bin/env python3
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

FONT = 'AppleGothic'
plt.rcParams['font.family'] = FONT
plt.rcParams['axes.unicode_minus'] = False

BG, PANEL, DEEP = '#1a1a2e', '#16213e', '#0d1f3c'
CYAN, GOLD, LIGHT, TEXT, GREEN, DIM = '#00d4ff', '#ffd700', '#7fdbff', '#e6edf3', '#00ff88', '#5e7290'

fig, ax = plt.subplots(figsize=(16, 5.2))
ax.set_xlim(0, 16)
ax.set_ylim(0, 5.2)
ax.axis('off')
fig.patch.set_facecolor(BG)

pod_x, pod_y, pod_w, pod_h = 0.6, 0.7, 9.4, 4.0
ax.add_patch(FancyBboxPatch(
    (pod_x, pod_y), pod_w, pod_h,
    boxstyle="round,pad=0.05,rounding_size=0.25",
    facecolor=DEEP, edgecolor=CYAN, linewidth=2.5, linestyle='--'))
ax.text(pod_x + 0.25, pod_y + pod_h - 0.35, 'Pod',
        fontsize=22, color=CYAN, fontweight='bold',
        fontfamily=FONT, ha='left', va='center')

app_x, app_y = pod_x + 0.6, pod_y + 0.6
app_w, app_h = 3.6, 2.6
ax.add_patch(FancyBboxPatch(
    (app_x, app_y), app_w, app_h,
    boxstyle="round,pad=0.04,rounding_size=0.15",
    facecolor=PANEL, edgecolor=LIGHT, linewidth=3.0))
ax.text(app_x + app_w / 2, app_y + app_h - 0.55, 'app',
        fontsize=26, color=LIGHT, fontweight='bold',
        fontfamily=FONT, ha='center', va='center')
ax.text(app_x + app_w / 2, app_y + app_h / 2 - 0.15,
        'curl localhost:8001',
        fontsize=15, color=GREEN, fontfamily='Menlo',
        ha='center', va='center')
ax.text(app_x + app_w / 2, app_y + 0.45,
        '인증 모름 · plain HTTP',
        fontsize=14, color=TEXT, fontfamily=FONT,
        ha='center', va='center', style='italic')

amb_x = app_x + app_w + 1.4
amb_y = app_y
amb_w, amb_h = 3.6, 2.6
ax.add_patch(FancyBboxPatch(
    (amb_x, amb_y), amb_w, amb_h,
    boxstyle="round,pad=0.04,rounding_size=0.15",
    facecolor=PANEL, edgecolor=GOLD, linewidth=3.0))
ax.text(amb_x + amb_w / 2, amb_y + amb_h - 0.55, 'ambassador',
        fontsize=22, color=GOLD, fontweight='bold',
        fontfamily=FONT, ha='center', va='center')
ax.text(amb_x + amb_w / 2, amb_y + amb_h / 2 + 0.05,
        'kubectl proxy',
        fontsize=15, color=GREEN, fontfamily='Menlo',
        ha='center', va='center')
ax.text(amb_x + amb_w / 2, amb_y + 0.45,
        '토큰 / cert 자동 처리',
        fontsize=14, color=TEXT, fontfamily=FONT,
        ha='center', va='center', style='italic')

api_x, api_y = 12.5, 1.6
api_w, api_h = 2.9, 2.2
ax.add_patch(FancyBboxPatch(
    (api_x, api_y), api_w, api_h,
    boxstyle="round,pad=0.05,rounding_size=0.15",
    facecolor=PANEL, edgecolor=GOLD, linewidth=3.0))
ax.text(api_x + api_w / 2, api_y + api_h - 0.5, 'apiserver',
        fontsize=22, color=GOLD, fontweight='bold',
        fontfamily=FONT, ha='center', va='center')
ax.text(api_x + api_w / 2, api_y + api_h / 2 - 0.25,
        'Kubernetes\nControl Plane',
        fontsize=14, color=TEXT, fontfamily=FONT,
        ha='center', va='center', linespacing=1.3)

y_arr = app_y + app_h / 2
x_s = app_x + app_w + 0.04
x_e = amb_x - 0.04
ax.annotate('', xy=(x_e, y_arr), xytext=(x_s, y_arr),
            arrowprops=dict(
                arrowstyle='-|>,head_length=0.7,head_width=0.45',
                color=LIGHT, lw=4.0, shrinkA=0, shrinkB=0))
ax.text((x_s + x_e) / 2, y_arr + 0.50, 'HTTP',
        fontsize=18, color=LIGHT, fontweight='bold',
        fontfamily=FONT, ha='center', va='bottom')
ax.text((x_s + x_e) / 2, y_arr - 0.50, ':8001',
        fontsize=15, color=DIM, fontfamily='Menlo',
        ha='center', va='top')

y_arr2 = amb_y + amb_h / 2
x_s2 = amb_x + amb_w + 0.04
x_e2 = api_x - 0.04
ax.annotate('', xy=(x_e2, y_arr2), xytext=(x_s2, y_arr2),
            arrowprops=dict(
                arrowstyle='-|>,head_length=0.7,head_width=0.45',
                color=GOLD, lw=4.0, shrinkA=0, shrinkB=0))
ax.text((x_s2 + x_e2) / 2, y_arr2 + 0.50, 'HTTPS',
        fontsize=18, color=GOLD, fontweight='bold',
        fontfamily=FONT, ha='center', va='bottom')
ax.text((x_s2 + x_e2) / 2, y_arr2 - 0.50, '+ Bearer token',
        fontsize=14, color=GREEN, fontfamily=FONT,
        ha='center', va='top')

plt.tight_layout(pad=0.3)
plt.savefig(
    '/Users/wonjunchoi/study/study/kubernetes-in-action/ch08-accessing-pod-metadata/diagrams/ambassador-pattern.png',
    dpi=200, facecolor=BG, bbox_inches='tight', pad_inches=0.25)
plt.close()
print('saved ambassador-pattern.png')
