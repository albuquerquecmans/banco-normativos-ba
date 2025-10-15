from pathlib import Path
import json
import html

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
        links_html = " \u00b7 ".join([x for x in links if x]) if links else ""

        titulo = n.get("identificacao") or f'{n.get("tipo","")} {n.get("numero","")}/{n.get("ano","")}'
        rows.append(f"""
        <tr>
          <td><a href="{n['slug']}.html">{html.escape(titulo or n['slug'])}</a></td>
          <td>{html.escape(n.get('vigencia',''))}</td>
          <td>{html.escape(n.get('tema',''))}</td>
          <td>{links_html}</td>
        </tr>""")

    index_html = f"""<!doctype html><meta charset="utf-8">
<title>banco-normativos-ba</title>
<h1>Banco de Normativos de Beneficios Assistenciais</h1>
<p>Lista inicial a partir da planilha.</p>
<table border="1" cellpadding="6" cellspacing="0">
<thead><tr><th>Identificacao</th><th>Vigencia</th><th>Tema</th><th>Fontes</th></tr></thead>
<tbody>
{''.join(rows)}
</tbody></table>
"""
    (out / "index.html").write_text(index_html, encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")

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

        titulo = n.get("identificacao") or n.get("slug")
        detail = f"""<!doctype html><meta charset="utf-8">
<title>{html.escape(titulo or "")}</title>
<p><a href="index.html">← Voltar</a></p>
<h2>{html.escape(titulo or "")}</h2>
<p><strong>Vigencia:</strong> {html.escape(n.get('vigencia',''))} | <strong>Tema:</strong> {html.escape(n.get('tema',''))}</p>
<p>{" \u00b7 ".join([x for x in links if x])}</p>
<hr>
<p><em>Texto compilado</em> e historico virão aqui em versoes futuras.</p>
"""
        (out / f"{n['slug']}.html").write_text(detail, encoding="utf-8")
