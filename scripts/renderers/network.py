#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render Reading Map or Knowledge Graph JSON as a standalone interactive HTML.

No third-party dependencies. Layout is deterministic so the same analysis JSON
renders consistently across runs.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from html import escape
import argparse
import json
import math
import os

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("WEREAD_DATA_DIR", ROOT / "data")).expanduser().resolve()

TYPE_STYLE = {
    "theme": ("#C2724B", "主题"),
    "concept": ("#D9A441", "概念"),
    "book": ("#7E9B8E", "书籍"),
    "quote": ("#9B7B6B", "划线"),
    "review": ("#6F8A84", "想法"),
}
TIER_STYLE = {
    "core": ("#C2724B", "核心主题"),
    "secondary": ("#D9A441", "次级主题"),
    "peripheral": ("#8A9A6B", "外围主题"),
}


def clamp(value, low, high):
    return max(low, min(high, value))


def safe_float(value, default=1.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_graph(path: Path, kind: str):
    raw = json.loads(path.read_text(encoding="utf-8"))
    nodes = raw.get("nodes") or []
    edges = raw.get("edges") or []
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ValueError("nodes and edges must be arrays")

    seen = set()
    clean_nodes = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or "").strip()
        label = str(node.get("label") or "").strip()
        if not node_id or not label or node_id in seen:
            continue
        seen.add(node_id)
        clean = dict(node)
        clean["id"] = node_id
        clean["label"] = label
        clean["weight"] = clamp(safe_float(node.get("weight"), 1.0), 0.1, 1000.0)
        if kind == "reading-map":
            tier = str(node.get("tier") or "secondary")
            clean["tier"] = tier if tier in TIER_STYLE else "secondary"
            clean["type"] = "theme"
        else:
            node_type = str(node.get("type") or "concept")
            clean["type"] = node_type if node_type in TYPE_STYLE else "concept"
        clean_nodes.append(clean)

    ids = {node["id"] for node in clean_nodes}
    clean_edges = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        if source not in ids or target not in ids or source == target:
            continue
        clean = dict(edge)
        clean["source"] = source
        clean["target"] = target
        clean["weight"] = clamp(
            safe_float(edge.get("strength", edge.get("weight", 1.0)), 1.0),
            0.1,
            1000.0,
        )
        clean_edges.append(clean)

    return raw, clean_nodes, clean_edges


def scaled_radius(weights):
    if not weights:
        return lambda _: 16.0
    lo, hi = min(weights), max(weights)
    if math.isclose(lo, hi):
        return lambda _: 23.0

    def radius(value):
        t = (value - lo) / (hi - lo)
        return 14 + math.sqrt(clamp(t, 0, 1)) * 21

    return radius


def ring_layout(nodes, kind: str, width=1000, height=720):
    cx, cy = width / 2, height / 2
    positions = {}
    radii = scaled_radius([node["weight"] for node in nodes])

    if kind == "reading-map":
        groups = [("core", 105), ("secondary", 225), ("peripheral", 315)]
        key = lambda n: n.get("tier", "secondary")
    else:
        groups = [("theme", 80), ("concept", 175), ("book", 280), ("review", 330), ("quote", 330)]
        key = lambda n: n.get("type", "concept")

    by_group = defaultdict(list)
    for node in nodes:
        by_group[key(node)].append(node)

    for group_name, ring_radius in groups:
        group = sorted(by_group.get(group_name, []), key=lambda n: (-n["weight"], n["label"]))
        count = len(group)
        if not count:
            continue
        if count == 1 and ring_radius <= 105:
            node = group[0]
            positions[node["id"]] = (cx, cy, radii(node["weight"]))
            continue
        offset = -math.pi / 2
        for i, node in enumerate(group):
            angle = offset + (2 * math.pi * i / count)
            jitter = (i % 2) * 10
            x = cx + math.cos(angle) * (ring_radius + jitter)
            y = cy + math.sin(angle) * (ring_radius + jitter)
            positions[node["id"]] = (x, y, radii(node["weight"]))

    missing = [n for n in nodes if n["id"] not in positions]
    for i, node in enumerate(sorted(missing, key=lambda n: n["label"])):
        angle = -math.pi / 2 + (2 * math.pi * i / max(1, len(missing)))
        positions[node["id"]] = (
            cx + math.cos(angle) * 335,
            cy + math.sin(angle) * 335,
            radii(node["weight"]),
        )

    return positions


def node_color(node, kind):
    if kind == "reading-map":
        return TIER_STYLE.get(node.get("tier"), TIER_STYLE["secondary"])[0]
    return TYPE_STYLE.get(node.get("type"), TYPE_STYLE["concept"])[0]


def build_svg(nodes, edges, positions, kind, width=1000, height=720):
    parts = [
        f'<svg id="network" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{"阅读版图" if kind == "reading-map" else "阅读知识图谱"}">'
    ]

    for radius in (105, 225, 315) if kind == "reading-map" else (80, 175, 280, 330):
        parts.append(f'<circle class="guide-ring" cx="{width/2}" cy="{height/2}" r="{radius}" />')

    for idx, edge in enumerate(edges):
        sx, sy, _ = positions[edge["source"]]
        tx, ty, _ = positions[edge["target"]]
        stroke_width = 0.8 + math.sqrt(edge["weight"]) * 0.7
        reason = edge.get("reason") or edge.get("type") or "related"
        parts.append(
            f'<line class="edge" id="edge-{idx}" data-source="{escape(edge["source"])}" '
            f'data-target="{escape(edge["target"])}" x1="{sx:.1f}" y1="{sy:.1f}" '
            f'x2="{tx:.1f}" y2="{ty:.1f}" stroke-width="{stroke_width:.2f}">'
            f'<title>{escape(str(reason))}</title></line>'
        )

    for node in nodes:
        x, y, radius = positions[node["id"]]
        color = node_color(node, kind)
        short = node["label"] if len(node["label"]) <= 12 else node["label"][:11] + "…"
        parts.append(
            f'<g class="node" tabindex="0" role="button" data-id="{escape(node["id"])}" '
            f'transform="translate({x:.1f},{y:.1f})">'
            f'<circle r="{radius:.1f}" fill="{color}" />'
            f'<text class="node-label" y="{radius + 17:.1f}">{escape(short)}</text>'
            f'<title>{escape(node["label"])}</title></g>'
        )

    parts.append("</svg>")
    return "".join(parts)


def render_html(raw, nodes, edges, kind):
    positions = ring_layout(nodes, kind)
    svg = build_svg(nodes, edges, positions, kind)
    title = "阅读版图" if kind == "reading-map" else "阅读知识图谱"
    subtitle = (
        "主题位置由核心度分层，连线表示主题间的证据关联。"
        if kind == "reading-map"
        else "把书籍、主题、概念、划线与想法放到同一个可追溯网络中。"
    )

    groups = []
    if kind == "reading-map":
        for key, (color, label) in TIER_STYLE.items():
            count = sum(1 for n in nodes if n.get("tier") == key)
            if count:
                groups.append((key, color, label, count))
    else:
        for key, (color, label) in TYPE_STYLE.items():
            count = sum(1 for n in nodes if n.get("type") == key)
            if count:
                groups.append((key, color, label, count))

    filters = "".join(
        f'<button type="button" class="filter active" data-group="{key}">'
        f'<span class="dot" style="background:{color}"></span>{escape(label)} '
        f'<strong>{count}</strong></button>'
        for key, color, label, count in groups
    )

    initial = nodes[0] if nodes else {}
    data_json = json.dumps(
        {"nodes": nodes, "edges": edges, "kind": kind, "insights": raw.get("insights") or []},
        ensure_ascii=False,
    ).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>微信读书 · {title}</title>
<style>
:root {{
  --bg:#F7F3EC; --panel:#FFFCF7; --text:#2B2724; --muted:#7A7066;
  --border:#E6DECF; --accent:#C2724B;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0; background:var(--bg); color:var(--text);
  font-family:"SF Pro Display","Inter","PingFang SC","Microsoft YaHei",sans-serif;
}}
main {{ width:min(1240px,calc(100% - 28px)); margin:0 auto; padding:38px 0 60px; }}
.eyebrow {{ color:var(--accent); font-size:12px; font-weight:750; letter-spacing:.13em; text-transform:uppercase; }}
h1 {{ margin:7px 0; font-size:clamp(30px,5vw,50px); letter-spacing:-.04em; }}
.lead {{ margin:0; color:var(--muted); max-width:760px; line-height:1.7; }}
.filters {{ display:flex; gap:8px; flex-wrap:wrap; margin:22px 0 14px; }}
.filter {{
  border:1px solid var(--border); background:var(--panel); color:var(--text);
  border-radius:999px; padding:8px 12px; cursor:pointer; font:inherit;
}}
.filter:not(.active) {{ opacity:.42; }}
.dot {{ width:9px; height:9px; border-radius:50%; display:inline-block; margin-right:7px; }}
.layout {{ display:grid; grid-template-columns:minmax(0,1fr) 300px; gap:14px; align-items:start; }}
.graph-card,.detail {{ background:var(--panel); border:1px solid var(--border); border-radius:22px; }}
.graph-card {{ overflow:hidden; }}
.svg-wrap {{ overflow:auto; }}
#network {{ min-width:720px; display:block; width:100%; height:auto; }}
.guide-ring {{ fill:none; stroke:#EDE5D9; stroke-dasharray:4 7; }}
.edge {{ stroke:#C9BEB0; opacity:.48; transition:opacity .14s ease,stroke .14s ease; }}
.edge.dim {{ opacity:.07; }}
.edge.active {{ opacity:.95; stroke:#665B52; }}
.node {{ cursor:pointer; outline:none; transition:opacity .14s ease; }}
.node circle {{ stroke:#FFFCF7; stroke-width:3; }}
.node.dim {{ opacity:.12; pointer-events:none; }}
.node.selected circle {{ stroke:#2B2724; stroke-width:4; }}
.node-label {{ text-anchor:middle; font-size:11px; fill:#4B443E; font-weight:650; pointer-events:none; }}
.detail {{ padding:20px; position:sticky; top:12px; min-height:260px; }}
.detail .kind {{ color:var(--accent); font-size:11px; font-weight:750; letter-spacing:.08em; }}
.detail h2 {{ margin:6px 0 10px; font-size:22px; }}
.detail p {{ color:var(--muted); line-height:1.65; }}
.detail dl {{ margin:16px 0 0; }}
.detail dt {{ color:var(--muted); font-size:11px; margin-top:12px; }}
.detail dd {{ margin:4px 0 0; line-height:1.55; }}
.evidence {{ margin:8px 0 0; padding-left:18px; color:var(--text); }}
.evidence li {{ margin:6px 0; line-height:1.5; }}
.meta {{ margin-top:14px; color:var(--muted); font-size:12px; }}
@media (max-width:880px) {{
  .layout {{ grid-template-columns:1fr; }}
  .detail {{ position:static; }}
  main {{ width:min(100% - 18px,1240px); padding-top:26px; }}
}}
</style>
</head>
<body>
<main>
  <div class="eyebrow">WeRead Intelligence · evidence graph</div>
  <h1>{title}</h1>
  <p class="lead">{subtitle} 点击节点可查看权重、关联和证据；筛选按钮可以隐藏某一层。</p>
  <div class="filters">{filters}</div>
  <div class="layout">
    <section class="graph-card"><div class="svg-wrap">{svg}</div></section>
    <aside class="detail" id="detail" aria-live="polite">
      <div class="kind">选择一个节点</div>
      <h2>{escape(str(initial.get("label") or "—"))}</h2>
      <p>点击图中的节点查看证据和关联。</p>
    </aside>
  </div>
  <div class="meta">节点 {len(nodes)} · 连线 {len(edges)} · renderer 不修改分析结论，只负责稳定呈现结构化 JSON。</div>
</main>
<script id="graph-data" type="application/json">{data_json}</script>
<script>
(() => {{
  const data = JSON.parse(document.getElementById('graph-data').textContent);
  const nodes = new Map(data.nodes.map(n => [String(n.id), n]));
  const filters = new Map([...document.querySelectorAll('.filter')].map(b => [b.dataset.group, true]));
  const detail = document.getElementById('detail');
  const nodeEls = [...document.querySelectorAll('.node')];
  const edgeEls = [...document.querySelectorAll('.edge')];

  const groupOf = n => data.kind === 'reading-map' ? (n.tier || 'secondary') : (n.type || 'concept');

  function evidenceText(item) {{
    if (typeof item === 'string') return item;
    if (!item || typeof item !== 'object') return String(item ?? '');
    return item.text || item.title || item.label || item.bookTitle || item.reason || JSON.stringify(item);
  }}

  function select(id) {{
    const n = nodes.get(String(id));
    if (!n) return;
    const incident = data.edges.filter(e => String(e.source) === String(id) || String(e.target) === String(id));
    const evidence = Array.isArray(n.evidence) ? n.evidence : [];
    const intro = n.summary || n.description || '';
    detail.innerHTML = `
      <div class="kind">${{groupOf(n)}} · 权重 ${{Number(n.weight || 0).toFixed(1)}}</div>
      <h2>${{escapeHtml(n.label || '')}}</h2>
      ${{intro ? `<p>${{escapeHtml(intro)}}</p>` : ''}}
      <dl>
        <dt>关联</dt>
        <dd>${{incident.length}} 条</dd>
        ${{evidence.length ? `<dt>证据</dt><dd><ul class="evidence">${{evidence.slice(0,8).map(x => `<li>${{escapeHtml(evidenceText(x))}}</li>`).join('')}}</ul></dd>` : ''}}
      </dl>`;
    nodeEls.forEach(el => el.classList.toggle('selected', el.dataset.id === String(id)));
    edgeEls.forEach(el => {{
      const hit = el.dataset.source === String(id) || el.dataset.target === String(id);
      el.classList.toggle('active', hit);
      el.classList.toggle('dim', !hit);
    }});
  }}

  function escapeHtml(value) {{
    return String(value).replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}})[c]);
  }}

  function applyFilters() {{
    nodeEls.forEach(el => {{
      const n = nodes.get(el.dataset.id);
      el.classList.toggle('dim', !filters.get(groupOf(n)));
    }});
    edgeEls.forEach(el => {{
      const a = nodes.get(el.dataset.source), b = nodes.get(el.dataset.target);
      const visible = filters.get(groupOf(a)) && filters.get(groupOf(b));
      el.style.display = visible ? '' : 'none';
    }});
  }}

  nodeEls.forEach(el => {{
    el.addEventListener('click', () => select(el.dataset.id));
    el.addEventListener('keydown', ev => {{
      if (ev.key === 'Enter' || ev.key === ' ') {{ ev.preventDefault(); select(el.dataset.id); }}
    }});
  }});
  document.querySelectorAll('.filter').forEach(btn => btn.addEventListener('click', () => {{
    const key = btn.dataset.group;
    filters.set(key, !filters.get(key));
    btn.classList.toggle('active', filters.get(key));
    applyFilters();
  }}));
  if (data.nodes.length) select(data.nodes[0].id);
}})();
</script>
</body>
</html>
"""


def parse_args():
    parser = argparse.ArgumentParser(description="Render WeRead reading-map / knowledge-graph JSON.")
    parser.add_argument("--kind", choices=["reading-map", "knowledge-graph"], required=True)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main():
    args = parse_args()
    stem = "reading_map" if args.kind == "reading-map" else "knowledge_graph"
    input_path = args.input or (DATA / "analysis" / f"{stem}.json")
    output_path = args.output or (DATA / "analysis" / f"{stem}.html")
    if not input_path.exists():
        raise SystemExit(f"ERROR: missing {input_path}")

    raw, nodes, edges = load_graph(input_path, args.kind)
    if not nodes:
        raise SystemExit("ERROR: no valid nodes found")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_html(raw, nodes, edges, args.kind), encoding="utf-8")
    print(f"{args.kind}: {output_path} | nodes={len(nodes)} edges={len(edges)}")


if __name__ == "__main__":
    main()
