# bpa/publish/emit_site.py
from pathlib import Path
import json, html, re

SEP = " · "

def _a(href, label):
    if not href:
        return ""
    return f'<a href="{html.escape(href)}" target="_blank" rel="noreferrer">{html.escape(label)}</a>'

def _is_url(v: str) -> bool:
    return bool(v) and re.match(r"^https?://", v)

def _safe_slug(s: str, fallback: str = "norma"):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9\-]+", "-", s)
    s = s.replace("/", "-").replace("\\", "-").replace(".", "-")
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or fallback

def _css():
    return """
    <style>
      body{font:16px/1.35 system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,sans-serif;margin:24px;max-width:1100px}
      h1{margin:0 0 12px}
      table{border-collapse:collapse;width:100%}
      th,td{border:1px solid #ccc;padding:8px;vertical-align:top}
      thead th{background:#f7f7f7}
      .meta h3{margin:24px 0 8px}
      .btns a{display:inline-block;border:1px solid #444;padding:6px 10px;margin-right:8px;text-decoration:none}
      .muted{color:#666}
      .pill{display:inline-block;background:#eef;border:1px solid #cde;border-radius:12px;padding:2px 8px;margin-right:6px}
      .section{margin:18px 0}
    </style>
    """

def build_site(norms_json: str, out_dir: str):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    norms = []
    p = Path(norms_json)
    if p.exists():
        norms = json.loads(p.read_text(encoding="utf-8"))

    # índice auxiliar: slug e identificação -> slug
    slug_by_key = {}
    for n in norms:
        slug = _safe_slug(n.get("slug") or n.get("identificacao") or "")
        if not slug:
            continue
        slug_by_key[slug] = slug
        ident = (n.get("identificacao") or "").strip().lower()
        if ident:
            slug_by_key[ident] = slug

    # ===== index.html =====
    rows = []
    for n in norms:
        titulo = n.get("identificacao") or f"{n.get('tipo','')} {n.get('numero','')}/{n.get('ano','')}" or (n.get("slug") or "")
        slug = _safe_slug(n.get("slug") or titulo, fallback="norma")
        links = []
        # política de fontes
        if n.get("tipo") in {"Lei", "Decreto", "lei", "decreto"} and n.get("fonte_planalto"):
            links.append(_a(n["fonte_planalto"], "Planalto"))
        if n.get("fonte_dou"):
            links.append(_a(n["fonte_dou"], "DOU"))
        links_html = SEP.join([x for x in links if x]) or "<span class='muted'>—</span>"

        rows.append(
            "<tr>"
            f'<td><a href="{slug}.html">{html.escape(titulo)}</a></td>'
            f"<td>{html.escape(n.get('vigencia','')) or '—'}</td>"
            f"<td>{html.escape(n.get('tema','')) or '—'}</td>"
            f"<td>{links_html}</td>"
            "</tr>"
        )

    index_html = (
        "<!doctype html><meta charset='utf-8'>"
        "<title>banco-normativos-ba</title>"
        f"{_css()}"
        "<h1>Banco de Normativos de Beneficios Assistenciais</h1>"
        "<p>Lista inicial a partir da planilha.</p>"
        "<table>"
        "<thead><tr><th>Identificacao</th><th>Vigencia</th><th>Tema</th><th>Fontes</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )
    (out / "index.html").write_text(index_html, encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")

    # ===== páginas de detalhe =====
    for i, n in enumerate(norms, start=1):
        titulo = n.get("identificacao") or n.get("slug") or f"Norma {i}"
        slug = _safe_slug(n.get("slug") or titulo, fallback=f"norma-{i}")

        # botões de texto (se existirem)
        btns = []
        if _is_url(n.get("texto_original")):
            btns.append(_a(n["texto_original"], "Texto original"))
        if _is_url(n.get("texto_compilado")):
            btns.append(_a(n["texto_compilado"], "Texto compilado"))
        btns_html = " ".join([f"<span class='btns'>{b}</span>" for b in btns])

        # fontes
        fontes = []
        if n.get("tipo") in {"Lei", "Decreto", "lei", "decreto"} and n.get("fonte_planalto"):
            fontes.append(_a(n["fonte_planalto"], "Ver no Planalto"))
        if n.get("fonte_dou"):
            fontes.append(_a(n["fonte_dou"], "Ver no DOU"))
        fontes_html = SEP.join([x for x in fontes if x]) or "<span class='muted'>—</span>"

        # listas de relações — aceitam identificações ou slugs, separados por ';' na planilha
        def _resolve_list(val):
            if not val:
                return []
            items = [x.strip() for x in str(val).split(";") if x.strip()]
            out_links = []
            for it in items:
                key = it.strip().lower()
                target_slug = slug_by_key.get(key) or slug_by_key.get(_safe_slug(key))
                label = it
                if target_slug:
                    out_links.append(f'<a href="{target_slug}.html">{html.escape(label)}</a>')
                else:
                    out_links.append(html.escape(label))
            return out_links

        altera = _resolve_list(n.get("altera") or n.get("altera_ids") or n.get("alteracoes"))
        alterado_por = _resolve_list(n.get("alterado_por") or n.get("alterado_por_ids"))
        correlatas = _resolve_list(n.get("relacionados") or n.get("legislacao_correlata"))

        # tabela de metadados (todas as colunas da planilha)
        meta_rows = []
        raw = n.get("raw") or {}
        raw_cols = n.get("raw_columns") or list(raw.keys())
        for col in raw_cols:
            val = raw.get(col, "")
            cell = _a(val, val) if _is_url(val) else html.escape(val)
            meta_rows.append(f"<tr><th align='left'>{html.escape(col)}</th><td>{cell}</td></tr>")
        meta_table = (
            "<div class='meta section'>"
            "<h3>Metadados da planilha</h3>"
            "<table>" + "".join(meta_rows) + "</table>"
            "</div>"
        )

        detail_html = (
            "<!doctype html><meta charset='utf-8'>"
            f"<title>{html.escape(titulo)}</title>"
            f"{_css()}"
            '<p><a href="index.html">← Voltar</a></p>'
            f"<h2>{html.escape(titulo)}</h2>"
            f"<p><strong>Vigencia:</strong> {html.escape(n.get('vigencia','')) or '—'} "
            f"{SEP}<strong>Tema:</strong> {html.escape(n.get('tema','')) or '—'}</p>"
            f"{('<div class=\"section\">' + btns_html + '</div>') if btns_html else ''}"
            f"<div class='section'><strong>Fontes oficiais:</strong> {fontes_html}</div>"
            f"{('<div class=\"section\"><strong>Alterações que ESTE ato faz:</strong> ' + SEP.join(altera) + '</div>') if altera else ''}"
            f"{('<div class=\"section\"><strong>Este ato foi ALTERADO por:</strong> ' + SEP.join(alterado_por) + '</div>') if alterado_por else ''}"
            f"{('<div class=\"section\"><strong>Legislação correlata:</strong> ' + SEP.join(correlatas) + '</div>') if correlatas else ''}"
            "<hr>"
            "<p><em>Texto compilado</em> e histórico detalhado virão aqui em versões futuras.</p>"
            f"{meta_table}"
        )
        (out / f"{slug}.html").write_text(detail_html, encoding="utf-8")
