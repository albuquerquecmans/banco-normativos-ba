from pathlib import Path
import json
import html

SEP = " · "  # separador de links

def _a(href, label):
    if not href:
        return ""
    return f'<a href="{html.escape(href)}" target="_blank" rel="noreferrer">{html.escape(label)}</a>'

def build_site(norms_json: str, out_dir: str):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    norms = []
    p = Path(norms_json)
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            norms = json.load(f)

    # -------- index.html --------
    rows = []
    for n in norms:
        links = []
        if n.get("tipo") in {"Lei", "Decreto"}:
            if n.get("fonte_planalto"):
                links.append(_a(n["fonte_planalto"], "Planalto"))
            if n.get("fonte_dou"):
                links.append(_a(n["fonte_dou"], "DOU"))
        else:
            if n.get("fonte_dou"):
                links.append(_a(n["fonte_dou"], "DOU"))

        links_joined = SEP.join([x for x in links if x]) if links else ""
        titulo = n.get("identificacao") or f'{n.get("tipo","")} {n.get("numero","")}/{n.get("ano","")}'

        row = (
            "<tr>"
            f'<td><a href="{n["slug"]}.html">{html.escape(titulo or n["slug"])}</a></td>'
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
    for n in norms:
        links = []
        if n.get("tipo") in {"Lei", "Decreto"}:
            if n.get("fonte_planalto"):
                links.append(_a(n["fonte_planalto"], "Ver no Planalto"))
            if n.get("fonte_dou"):
                links.append(_a(n["fonte_dou"], "Ver no DOU"))
        else:
            if n.get("fonte_dou"):
                links.append(_a(n["fonte_dou"], "Ver no DOU"))

        links_joined = SEP.join([x for x in links if x])
        titulo = n.get("identificacao") or n.get("slug") or "Detalhe"

        detail_html = (
            "<!doctype html><meta charset='utf-8'>"
            f"<title>{html.escape(titulo)}</title>"
            '<p><a href="index.html">← Voltar</a></p>'
            f"<h2>{html.escape(titulo)}</h2>"
            f"<p><strong>Vigencia:</strong> {html.escape(n.get('vigencia',''))} | "
            f"<strong>Tema:</strong> {html.escape(n.get('tema',''))}</p>"
            f"<p>{links_joined}</p>"
            "<hr>"
            "<p><em>Texto compilado</em> e historico virao aqui em versoes futuras.</p>"
        )
        (out / f"{n['slug']}.html").write_text(detail_html, encoding="utf-8")
