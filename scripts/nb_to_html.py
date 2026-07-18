#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nb_to_html.py —— 把 Jupyter Notebook 转成自带样式的 HTML(零依赖,仅标准库)
=====================================================================
用途: 生成可挂到 GitHub Pages 的分析报告网页。
特点:
  * Markdown 单元 -> HTML(支持标题/列表/表格/引用/粗体/行内代码/链接/分隔线)
  * 代码单元 -> 带 In[] 标记的代码块
  * 若 Notebook 已执行, 自动嵌入输出(文本 / base64 图片 / HTML)
  * CryptoLake 配色, 深浅色自适应

用法:
  python scripts/nb_to_html.py analysis/CryptoLake_分析报告.ipynb report.html
"""
import html
import json
import re
import sys


# ---------- 行内 Markdown ----------
def inline(text):
    # 先转义,再逐步还原受控标记
    out = html.escape(text)
    # 行内代码 `code`
    out = re.sub(r'`([^`]+)`', lambda m: f'<code>{m.group(1)}</code>', out)
    # 粗体 **x**
    out = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', out)
    # 链接 [t](u)
    out = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', out)
    return out


# ---------- 块级 Markdown ----------
def md_to_html(src):
    lines = src.split('\n')
    html_parts, i, n = [], 0, len(lines)
    list_open = None  # 'ul' / 'ol' / None

    def close_list():
        nonlocal list_open
        if list_open:
            html_parts.append(f'</{list_open}>')
            list_open = None

    while i < n:
        line = lines[i]
        s = line.strip()

        # 表格: 当前行含 | 且下一行是分隔行
        if '|' in line and i + 1 < n and re.match(r'^\s*\|?[\s:|-]+\|[\s:|-]*$', lines[i + 1]):
            close_list()
            header = [c.strip() for c in line.strip().strip('|').split('|')]
            html_parts.append('<table><thead><tr>' +
                              ''.join(f'<th>{inline(c)}</th>' for c in header) +
                              '</tr></thead><tbody>')
            i += 2
            while i < n and '|' in lines[i]:
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                html_parts.append('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in cells) + '</tr>')
                i += 1
            html_parts.append('</tbody></table>')
            continue

        if s.startswith('### '):
            close_list(); html_parts.append(f'<h3>{inline(s[4:])}</h3>')
        elif s.startswith('## '):
            close_list(); html_parts.append(f'<h2>{inline(s[3:])}</h2>')
        elif s.startswith('# '):
            close_list(); html_parts.append(f'<h1>{inline(s[2:])}</h1>')
        elif s in ('---', '***', '___'):
            close_list(); html_parts.append('<hr>')
        elif s.startswith('> '):
            close_list(); html_parts.append(f'<blockquote>{inline(s[2:])}</blockquote>')
        elif re.match(r'^[-*] ', s):
            if list_open != 'ul':
                close_list(); html_parts.append('<ul>'); list_open = 'ul'
            html_parts.append(f'<li>{inline(s[2:])}</li>')
        elif re.match(r'^\d+\. ', s):
            if list_open != 'ol':
                close_list(); html_parts.append('<ol>'); list_open = 'ol'
            item = re.sub(r'^\d+\. ', '', s)
            html_parts.append(f'<li>{inline(item)}</li>')
        elif s == '':
            close_list()
        else:
            close_list(); html_parts.append(f'<p>{inline(s)}</p>')
        i += 1

    close_list()
    return '\n'.join(html_parts)


# ---------- 代码单元输出 ----------
def render_outputs(outputs):
    if not outputs:
        return ''
    parts = ['<div class="outputs">']
    for o in outputs:
        ot = o.get('output_type')
        if ot == 'stream':
            parts.append(f'<pre class="stdout">{html.escape("".join(o.get("text", [])))}</pre>')
        elif ot in ('execute_result', 'display_data'):
            data = o.get('data', {})
            if 'image/png' in data:
                img = data['image/png']
                if isinstance(img, list):
                    img = ''.join(img)
                parts.append(f'<img alt="output" src="data:image/png;base64,{img}">')
            elif 'text/html' in data:
                parts.append(''.join(data['text/html']))
            elif 'text/plain' in data:
                parts.append(f'<pre class="result">{html.escape("".join(data["text/plain"]))}</pre>')
        elif ot == 'error':
            parts.append(f'<pre class="err">{html.escape(chr(10).join(o.get("traceback", [])))}</pre>')
    parts.append('</div>')
    return '\n'.join(parts)


TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root{{--bg:#f4f2ec;--surface:#fbfaf6;--surface2:#efece3;--ink:#1a1f29;--soft:#4b5261;--faint:#8a8f9c;--line:#ded9cd;--accent:#b6791b;--accentink:#8a5a10;--bull:#1c8f79;
--mono:ui-monospace,"SF Mono","JetBrains Mono",Menlo,monospace;--sans:-apple-system,"PingFang SC","Microsoft YaHei","Segoe UI",system-ui,sans-serif;}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0d1119;--surface:#141a26;--surface2:#1a2130;--ink:#e7e9ee;--soft:#a3abbb;--faint:#6b7488;--line:#232c3d;--accent:#e8b341;--accentink:#f0c869;--bull:#2bb596;}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);line-height:1.65;font-size:16px;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:860px;margin:0 auto;padding:40px 24px 80px}}
.banner{{background:color-mix(in srgb,var(--accent) 12%,transparent);border:1px solid color-mix(in srgb,var(--accent) 32%,transparent);border-radius:8px;padding:14px 18px;margin-bottom:28px;font-size:14px;color:var(--soft)}}
.banner b{{color:var(--accentink)}}
h1{{font-size:30px;letter-spacing:-.02em;margin:30px 0 12px}}h2{{font-size:23px;margin:34px 0 12px;padding-bottom:6px;border-bottom:2px solid var(--accent)}}h3{{font-size:18px;margin:22px 0 8px}}
p{{color:var(--soft)}}a{{color:var(--accentink)}}strong{{color:var(--ink)}}
code{{font-family:var(--mono);font-size:.88em;background:var(--surface2);padding:1px 5px;border-radius:4px;color:var(--accentink)}}
blockquote{{margin:12px 0;padding:8px 16px;border-left:3px solid var(--accent);background:var(--surface);color:var(--soft);border-radius:0 6px 6px 0}}
hr{{border:0;border-top:1px solid var(--line);margin:24px 0}}
ul,ol{{color:var(--soft);padding-left:22px}}li{{margin:4px 0}}
table{{border-collapse:collapse;width:100%;font-size:14px;margin:14px 0;display:block;overflow-x:auto}}
th,td{{border:1px solid var(--line);padding:7px 11px;text-align:left}}th{{background:var(--surface2);color:var(--ink);font-family:var(--mono);font-size:12px}}td{{color:var(--soft)}}
.cell{{margin:16px 0}}
.code{{background:var(--surface);border:1px solid var(--line);border-radius:8px;overflow:hidden}}
.code .lbl{{font-family:var(--mono);font-size:11px;color:var(--faint);padding:6px 12px;border-bottom:1px solid var(--line);background:var(--surface2)}}
.code pre{{margin:0;padding:14px 16px;overflow-x:auto;font-family:var(--mono);font-size:13px;line-height:1.6;color:var(--ink)}}
.outputs{{padding:10px 14px;border:1px solid var(--line);border-top:0;border-radius:0 0 8px 8px;background:var(--bg)}}
.outputs pre{{font-family:var(--mono);font-size:12.5px;white-space:pre-wrap;color:var(--soft);margin:4px 0}}
.outputs img{{max-width:100%;height:auto;border-radius:4px}}
.outputs .err{{color:#cf4b47}}
footer{{margin-top:50px;padding-top:20px;border-top:1px solid var(--line);color:var(--faint);font-size:13px}}
.topnav{{position:sticky;top:0;z-index:9;display:flex;gap:3px;flex-wrap:wrap;align-items:center;padding:9px 24px;border-bottom:1px solid var(--line);background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(8px);font-family:var(--mono)}}
.topnav .brand{{font-weight:700;color:var(--ink);margin-right:auto;font-size:12.5px;letter-spacing:.04em}}
.topnav .brand b{{color:var(--accent)}}
.topnav a{{font-size:11.5px;text-decoration:none;color:var(--soft);padding:4px 9px;border-radius:4px;border:1px solid transparent}}
.topnav a:hover{{color:var(--ink);border-color:var(--line)}}
.topnav a.active{{color:var(--accentink);background:color-mix(in srgb,var(--accent) 12%,transparent);border-color:color-mix(in srgb,var(--accent) 30%,transparent)}}
</style></head><body>
<nav class="topnav"><span class="brand">CRYPTO<b>LAKE</b></span>
<a href="https://lizhi5753186.github.io/CryptoLake/roadmap.html">路线图</a>
<a href="https://lizhi5753186.github.io/CryptoLake/report.html" class="active">分析报告</a>
<a href="https://lizhi5753186.github.io/CryptoLake/resume.html">简历</a>
<a href="https://github.com/lizhi5753186/CryptoLake">GitHub ↗</a></nav>
<div class="wrap">
<div class="banner">📊 <b>CryptoLake 分析报告</b> · 本页由 <code>scripts/nb_to_html.py</code> 从 Notebook 生成。{note}</div>
{body}
<footer>由 CryptoLake · nb_to_html.py 生成 · <a href="index.html">← 返回路线图</a> · <a href="https://github.com/lizhi5753186/CryptoLake">GitHub 仓库</a></footer>
</div></body></html>'''


def main():
    if len(sys.argv) < 3:
        print('用法: python scripts/nb_to_html.py <notebook.ipynb> <output.html>')
        sys.exit(1)
    nb = json.load(open(sys.argv[1], encoding='utf-8'))
    body, has_output = [], False
    for c in nb['cells']:
        src = ''.join(c.get('source', []))
        if c['cell_type'] == 'markdown':
            body.append(f'<div class="cell">{md_to_html(src)}</div>')
        elif c['cell_type'] == 'code':
            if not src.strip():
                continue
            ec = c.get('execution_count')
            lbl = f'In [{ec if ec is not None else " "}]'
            out = render_outputs(c.get('outputs', []))
            if out:
                has_output = True
            body.append(f'<div class="cell"><div class="code"><div class="lbl">{lbl}</div>'
                        f'<pre>{html.escape(src)}</pre></div>{out}</div>')
    note = ('' if has_output else
            ' 当前 Notebook <b>尚未执行</b>,故只展示分析思路与代码;'
            '在本地跑通数据库后重新执行并转换,图表会自动嵌入本页。')
    title = 'CryptoLake · 加密货币交易平台数据分析报告'
    open(sys.argv[2], 'w', encoding='utf-8').write(
        TEMPLATE.format(title=title, body='\n'.join(body), note=note))
    print(f'✔ 已生成 {sys.argv[2]}  (含输出: {has_output})')


if __name__ == '__main__':
    main()
