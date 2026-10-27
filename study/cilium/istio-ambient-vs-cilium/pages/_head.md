---
marp: true
theme: default
paginate: true
backgroundColor: "#1a1a2e"
color: "#e0e0e0"
style: |
  section {
    font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
    background-color: #1a1a2e;
    font-size: 30px;
    line-height: 1.5;
    padding: 48px 60px;
  }
  h1 {
    color: #00d4ff;
    border-bottom: 2px solid #00d4ff;
    padding-bottom: 8px;
    font-size: 1.32em;
    margin-bottom: 16px;
  }
  h2 { color: #00d4ff; font-size: 1.1em; }
  h3 { color: #7fdbff; font-size: 0.92em; margin-bottom: 6px; }
  strong { color: #ffd700; }
  em { color: #ff9e64; font-style: normal; }
  code {
    background-color: #16213e;
    color: #00ff88;
    font-size: 0.86em;
    padding: 1px 6px;
    border-radius: 4px;
  }
  pre {
    background-color: #0d1117 !important;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px 14px;
  }
  pre code {
    background-color: transparent !important;
    color: #e6edf3;
    font-size: 0.58em;
    line-height: 1.5;
  }
  table { font-size: 0.62em; margin: 10px auto; border-collapse: separate; border-spacing: 0; border-radius: 6px; overflow: hidden; }
  th { background-color: #16213e; color: #00d4ff; padding: 8px 13px; }
  td { background-color: #0f3460; padding: 8px 13px; }
  blockquote {
    border-left: 4px solid #ffd700;
    background-color: #2a1f3d;
    padding: 10px 18px;
    margin: 14px 0;
    font-style: normal;
    font-size: 0.82em;
    border-radius: 4px;
  }
  section.lead h1 { text-align: center; font-size: 1.95em; border: none; }
  section.lead p { text-align: center; font-size: 1.05em; }
  ul, ol { padding-left: 22px; }
  li { margin: 5px 0; }
  .columns { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
  .small { font-size: 0.76em; color: #9aa0b0; }
  .src { font-size: 0.58em; color: #9aa0b0; margin-top: 8px; }

  /* ── 다이어그램 킷 ───────────────────────────── */
  .seq { display: flex; align-items: stretch; justify-content: center; margin: 24px 0 10px 0; }
  .seq-node {
    flex: 1 1 0; border: 2px solid #00d4ff; border-radius: 10px;
    background: #16213e; padding: 14px 8px; text-align: center;
    font-size: 0.56em; line-height: 1.35; color: #e0e0e0;
    display: flex; align-items: center; justify-content: center;
  }
  .seq-arrow { flex: 0 0 42px; align-self: center; position: relative; height: 3px; background: #ffd700; }
  .seq-arrow::after {
    content: ''; position: absolute; right: -1px; top: -7px;
    border-left: 13px solid #ffd700;
    border-top: 8px solid transparent; border-bottom: 8px solid transparent;
  }

  .stack { display: flex; flex-direction: column; align-items: center; margin: 22px 0 10px 0; }
  .stack-layer {
    border: 2px solid #00d4ff; border-radius: 8px; background: #16213e;
    padding: 11px 16px; margin: 5px 0; text-align: center;
    font-size: 0.56em; line-height: 1.35; box-sizing: border-box;
  }

  .steps { position: relative; margin: 20px 0 8px 0; }
  .steps::before { content: ''; position: absolute; left: 20px; top: 26px; bottom: 26px; width: 2px; background: #30363d; }
  .step { position: relative; padding: 9px 0 9px 60px; min-height: 42px; display: flex; align-items: center; }
  .step-num {
    position: absolute; left: 0; top: 50%; transform: translateY(-50%);
    width: 42px; height: 42px; border-radius: 50%;
    background: #0f3460; border: 2px solid #00d4ff; color: #00d4ff;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.6em; font-weight: 700;
  }
  .step-txt { font-size: 0.62em; line-height: 1.42; }

  .cmp { display: grid; grid-template-columns: 1fr 1fr; gap: 22px; margin: 20px 0 8px 0; }
  .cmp-col { border: 2px solid #5a6070; border-radius: 10px; padding: 14px 18px; background: #16213e88; }
  .cmp-col.left { border-color: #ff6b6b; }
  .cmp-col.right { border-color: #00ff88; }
  .cmp-title { font-size: 0.66em; font-weight: 700; text-align: center; margin-bottom: 10px; }
  .cmp-col.left .cmp-title { color: #ff6b6b; }
  .cmp-col.right .cmp-title { color: #00ff88; }
  .cmp-item { font-size: 0.58em; line-height: 1.45; margin: 7px 0; padding-left: 15px; position: relative; }
  .cmp-item::before { content: '·'; position: absolute; left: 3px; color: #9aa0b0; }

  .badge {
    display: inline-block; background: #0f3460; border: 1px solid #00d4ff;
    color: #00d4ff; border-radius: 999px; padding: 0 11px; margin: 0 3px;
    font-size: 0.76em; line-height: 1.6;
  }
  .badge.gold { border-color: #ffd700; color: #ffd700; }
  .badge.red { border-color: #ff6b6b; color: #ff6b6b; }
  .badge.green { border-color: #00ff88; color: #00ff88; }
---
