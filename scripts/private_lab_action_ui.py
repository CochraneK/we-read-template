#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add Private Lab action/report hub for Alchemy, Advisor, Path and Review."""
from __future__ import annotations
import html

CSS = r'''
.action-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.action-card{border:1px solid var(--line);background:var(--paper2);border-radius:14px;padding:13px;text-decoration:none}.action-card strong,.action-card span{display:block}.action-card span{font-size:11px;color:var(--muted);margin-top:5px}.action-card.ready{border-color:color-mix(in srgb,var(--accent2) 55%,var(--line))}.action-card.missing{opacity:.65}.action-code{margin-top:10px;border:1px dashed var(--line);border-radius:12px;padding:10px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10px;white-space:pre-wrap;overflow:auto;color:var(--muted)}@media(max-width:800px){.action-grid{grid-template-columns:1fr}}
'''


def augment(page: str, assets: dict[str, bool]) -> str:
    if 'id="actions"' in page:
        return page
    def card(label, path, desc, key):
        if assets.get(key):
            return f'<a class="action-card ready" href="{html.escape(path, quote=True)}"><strong>{html.escape(label)}</strong><span>{html.escape(desc)}</span></a>'
        return f'<div class="action-card missing"><strong>{html.escape(label)}</strong><span>本次未生成。{html.escape(desc)}</span></div>'
    cards = ''.join([
        card('Narrative Review','narrative_review.html','周期事实 → 平台化可编辑草稿；未知原因不会自动编造。','review'),
        card('Alchemy · 单书','alchemy_book.html','章节证据 → 启发式议题聚类 → 来源/我的想法对照。','alchemyBook'),
        card('Alchemy · 跨主题','alchemy_topic.html','跨书证据景观；证据过大时会先触发 scope gate。','alchemyTopic'),
        card('Advisor shortlist','advisor.html','实时微信读书目录核验后的候选；先看目录层。','advisor'),
        card('Advisor 语义审阅','advisor_semantic_editor.html','为观点/范式/抽象层级/相邻学科和 conceptual fit 补证据。','advisorSemanticEditor'),
        card('Advisor 最终语义结果','advisor_semantic.html','只有完整 evidence + confidence 通过 gate 的候选。','advisorSemanticResult'),
        card('Reading Path 候选池','reading_path_discovery.html','实时目录发现池；此时阶段仍只是候选。','pathDiscovery'),
        card('Reading Path 语义审阅','reading_path_semantic_editor.html','为候选补语义轴与 intro/framework/frontier 阶段证据。','pathSemanticEditor'),
        card('Reading Path 语义结果','reading_path_semantic.html','查看通过/未通过语义 gate 的候选。','pathSemanticResult'),
        card('Reading Path 最终计划','reading_path.html','阶段确认 + 实时核验 + 每阶段候选足够后生成 6 本路径。','pathPlan'),
    ])
    command = '''# 周期复盘成稿\npython scripts/build_private_reading_lab.py --include-private --review-platform 公众号\n\n# Advisor：先发现候选并生成语义编辑页\npython scripts/build_private_reading_lab.py --include-private --advisor-query "主题"\n# 编辑 advisor_semantic_editor.html 并导出 JSON 后，再运行：\npython scripts/build_private_reading_lab.py --include-private --advisor-query "主题" --advisor-semantic-annotations /path/to/weread-semantic-advisor.json\n\n# Path：先生成候选池和语义编辑页\npython scripts/build_private_reading_lab.py --include-private --path-topic "主题"\n# 编辑并导出后，再运行：\npython scripts/build_private_reading_lab.py --include-private --path-topic "主题" --path-semantic-annotations /path/to/weread-semantic-path.json --path-confirmed-level beginner'''
    section = f'''<section class="panel" id="actions" style="margin-top:14px"><div class="section-head"><div><h2>Knowledge Actions</h2><p>从“看数据”进入“复盘 / 重新理解 / 找下一本 / 构建路径”。实时目录动作需要本地 <code>WEREAD_API_KEY</code>；语义层必须有显式 evidence。</p></div></div><div class="action-grid">{cards}</div><div class="action-code">{html.escape(command)}</div></section>'''
    page = page.replace('</style>', CSS + '\n</style>', 1)
    page = page.replace('<a href="#books">Books</a>', '<a href="#actions">Actions</a><a href="#books">Books</a>', 1)
    page = page.replace('<section class="panel" id="books"', section + '\n<section class="panel" id="books"', 1)
    return page
