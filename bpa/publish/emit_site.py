# bpa/publish/emit_site.py
from pathlib import Path
import json, html, re

SEP = " · "

def _a(href, label):
    if not href:
        return ""
    return f'<a href="{html.escape(href)}" target="_blank" rel="noreferrer">{html.escape(label)}</a>'

def _safe_slug(s: str, fallback: str = "norma"):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9\-]+", "-", s)
    s = s.replace("/", "-").replace("\\", "-").replace(".", "-")
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or fallback

def _is_url(v: str) -> bool:
    return bool(v) and re.match(r"^https?://", v)

def build_site(norms_json: str, out_dir: str):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    norms = []
    p = Path(norms_json)
    if p.exists():
        norms = json.loads(p.read_text(encoding="utf-8"))

    # -------- index.html --------
    rows = []
    for n in norms:
        links = []
        if n.get("tipo") in {"Lei", "Decreto", "lei", "decreto"}:
            if n.get("fonte_planalto"):
                links.append(_a(n["fonte_planalto"], "Planalto"))
            if n.get("fonte_dou"):
                links.append(_a(n["fonte_dou"], "DOU"))
        else:
            if n.get("fonte_dou"):
                links.append(_a(n["fonte_dou"], "DOU"))

        links_joined = SEP.join([x for x in links if x]) if links else ""
        titulo = n.get("identificacao") or f'{n.get("tipo","")} {n.get("numero","")}/{n.get("ano","")}' or (n.get("slug") or "")
        slug = _safe_slug(n.get("slug") or titulo, fallback="norma")

        row = (
            "<tr>"
            f'<td><a href="{slug}.html">{html.escape(titulo or slug)}</a></td>'
            f'<td>{html.escape(n.get("vigencia",""))}</td>'
            f'<td>{html.escape(n.get("tema",""))}</td>'
            f"<td>{links_joined}</td>"
            "</tr>"
        )
        rows.append(row)

    rows_html = "".join(rows)
    index_html = (
        "<!doctype html><meta charset='utf-8'>"
        "<title>banco-normativos-ba</title>"
        "<h1>Banco de Normativos de Beneficios Assistenciais</h1>"
        "<p>Lista inicial a partir da planilha.</p>"
        "<table border='1' cellpadding='6' cellspacing='0'>"
        "<thead><tr><th>Identificacao</th><th>Vigencia</th><th>Tema</th><th>Fontes</th></tr></thead>"
        f"<tbody>{rows_html}</tbody></table>"
    )
    (out / "index.html").write_text(index_html, encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")

    # -------- detalhes por norma --------
    for i, n in enumerate(norms, start=1):
        titulo = n.get("identificacao") or n.get("slug") or f"Norma {i}"
        slug = _safe_slug(n.get("slug") or titulo, fallback=f"norma-{i}")

        # construir links “oficiais”
        links = []
        if n.get("tipo") in {"Lei", "Decreto", "lei", "decreto"} and n.get("fonte_planalto"):
            links.append(_a(n["fonte_planalto"], "Ver no Planalto"))
        if n.get("fonte_dou"):
            links.append(_a(n["fonte_dou"], "Ver no DOU"))
        links_html = SEP.join([x for x in links if x])

        # tabela de metadados: todos os campos originais da planilha
        meta_rows = []
        raw = n.get("raw") or {}
        raw_cols = n.get("raw_columns") or list(raw.keys())
        for col in raw_cols:
            val = raw.get(col, "")
            cell = html.escape(val)
            if _is_url(val):
                cell = _a(val, val)
            meta_rows.append(f"<tr><th align='left'>{html.escape(col)}</th><td>{cell}</td></tr>")
        meta_table = (
            "<h3>Metadados da planilha</h3>"
            "<table border='1' cellpadding='6' cellspacing='0'>"
            f"{''.join(meta_rows)}"
            "</table>"
        )

        detail_html = (
            "<!doctype html><meta charset='utf-8'>"
            f"<title>{html.escape(titulo)}</title>"
            '<p><a href="index.html">← Voltar</a></p>'
            f"<h2>{html.escape(titulo)}</h2>"
            f"<p><strong>Vigencia:</strong> {html.escape(n.get('vigencia',''))} | "
            f"<strong>Tema:</strong> {html.escape(n.get('tema',''))}</p>"
            f"<p>{links_html}</p>"
            "<hr>"
            "<p><em>Texto compilado</em> e historico virao aqui em versoes futuras.</p>"
            f"{meta_table}"
        )
        (out / f"{slug}.html").write_text(detail_html, encoding="utf-8")
