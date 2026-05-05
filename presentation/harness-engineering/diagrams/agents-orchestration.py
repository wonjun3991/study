#!/usr/bin/env python3
"""Agents orchestration — feature-implementer fan-out to implement + validate phases."""
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch

FONT = 'AppleGothic'
plt.rcParams['font.family'] = FONT
plt.rcParams['axes.unicode_minus'] = False

fig, ax = plt.subplots(figsize=(16, 5.8))
ax.set_xlim(0, 16)
ax.set_ylim(0, 5.8)
ax.axis('off')
fig.patch.set_facecolor('#1a1a2e')

orch_x, orch_y = 2.5, 4.65
orch_w, orch_h = 11.0, 1.1
orch = FancyBboxPatch(
    (orch_x, orch_y), orch_w, orch_h,
    boxstyle="round,pad=0.05",
    facecolor='none', edgecolor='#ffd700', linewidth=4.0
)
ax.add_patch(orch)
ax.text(8, orch_y + orch_h / 2, 'feature-implementer  ·  오케스트레이터',
        fontsize=40, color='#ffd700', fontweight='bold',
        fontfamily=FONT, ha='center', va='center')

impl_agents = [
    (0.5, 'liquibase-\nmanager', 'DB 스키마'),
    (3.4, 'jpa-\nguardian',      'Entity · Repo'),
]
validate_agents = [
    (7.3,  'jpa-\nguardian',  'N+1 · soft-delete'),
    (10.2, 'code-\nquality',  'SRP · DRY'),
    (13.1, 'multi-\ntenant',  'tenantId 필터'),
]

box_w, box_h = 2.6, 2.7
y_base = 0.4
hub_y = 3.7

def draw_agent(x, name, role, color):
    ax.add_patch(Rectangle(
        (x, y_base), box_w, box_h,
        facecolor='none', edgecolor=color, linewidth=3.2
    ))
    ax.text(x + box_w / 2, y_base + box_h - 0.85, name,
            fontsize=26, color='#ffffff', fontweight='bold',
            fontfamily=FONT, ha='center', va='center', linespacing=1.15)
    ax.text(x + box_w / 2, y_base + 0.55, role,
            fontsize=17, color=color, fontweight='bold',
            fontfamily=FONT, ha='center', va='center', linespacing=1.3)

for (x, n, r) in impl_agents:
    draw_agent(x, n, r, '#7fdbff')
for (x, n, r) in validate_agents:
    draw_agent(x, n, r, '#52b788')

impl_left_x = impl_agents[0][0] + box_w / 2
impl_right_x = impl_agents[-1][0] + box_w / 2
valid_left_x = validate_agents[0][0] + box_w / 2
valid_right_x = validate_agents[-1][0] + box_w / 2

ax.plot([8, 8], [orch_y, hub_y], color='#ffd700', lw=3.5)
ax.plot([impl_left_x, valid_right_x], [hub_y, hub_y], color='#ffd700', lw=3.5)

impl_center_x = (impl_left_x + impl_right_x) / 2
valid_center_x = (valid_left_x + valid_right_x) / 2
ax.text(impl_center_x, hub_y + 0.4, '구현 (Phase 2)',
        fontsize=22, color='#7fdbff', fontweight='bold',
        fontfamily=FONT, ha='center', va='bottom')
ax.text(valid_center_x, hub_y + 0.4, '검증 (Phase 6.5)',
        fontsize=22, color='#52b788', fontweight='bold',
        fontfamily=FONT, ha='center', va='bottom')

for (x, _, _) in impl_agents:
    top_x = x + box_w / 2
    y_top_box = y_base + box_h
    ax.annotate('',
        xy=(top_x, y_top_box + 0.02),
        xytext=(top_x, hub_y),
        arrowprops=dict(arrowstyle='-|>,head_length=0.5,head_width=0.35',
                        color='#7fdbff', lw=3.5, shrinkA=0, shrinkB=0))

for (x, _, _) in validate_agents:
    top_x = x + box_w / 2
    y_top_box = y_base + box_h
    ax.annotate('',
        xy=(top_x, y_top_box + 0.02),
        xytext=(top_x, hub_y),
        arrowprops=dict(arrowstyle='-|>,head_length=0.5,head_width=0.35',
                        color='#52b788', lw=3.5, shrinkA=0, shrinkB=0))

plt.tight_layout(pad=0.2)
plt.savefig('agents-orchestration.png', dpi=200, facecolor='#1a1a2e',
            bbox_inches='tight', pad_inches=0.2)
plt.close()
print("✅ agents-orchestration.png 생성 완료")
