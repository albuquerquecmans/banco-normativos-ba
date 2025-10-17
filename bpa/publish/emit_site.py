# bpa/publish/emit_site.py
from pathlib import Path
import json, html, re

SEP = " · "

TIPOS_FIXOS = [
    "Lei", "Medida Provisória", "Decreto",
    "Instrução Normativa", "Instrução Operacional",
    "Memorando Circular", "Mensagem", "Orientação Interna",
    "Portaria", "Portaria Conjunta", "Portaria INSS",
    "Portaria Interministerial", "Portaria MDS", "Resolução",
]

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
    return (
        "<style>"
        "body{font:16px/1.35 system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,sans-serif;margin:24px;max-width:1200px}"
        "h1{margin:0 0 12px}"
        ".panel{background:#0c9a8a;color:#fff;padding:10px 14px;font-weight:700;border-radius:6px 6px 0 0}"
        ".search{border:1px solid #ddd;border-top:0;border-radius:0 0 6px 6px;padding:18px}"
        ".grid{display:grid;grid-template-columns:repeat(12,1fr);gap:12px}"
        ".col-3{grid-column:span 3}.col-4{grid-column:span 4}.col-6{grid-column:span 6}.col-12{grid-column:span 12}"
        "label{display:block;font-size:13px;color:#333;margin-bottom:6px}"
        "input[type=text],input[type=number],select{width:100%;padding:10px;border:1px solid #ccc;border-radius:6px}"
        ".chips{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:8px}"
        ".chip{display:flex;align-items:center;gap:8px;font-size:14px}"
        ".btn{background:#0c9a8a;color:#fff;border:0;padding:12px 18px;border-radius:8px;cursor:pointer}"
        ".btn:disabled{opacity:.6;cursor:not-allowed}"
        "table{border-collapse:collapse;width:100%;margin-top:16px}"
        "th,td{border:1px solid #ddd;padding:10px;vertical-align:top}"
        "thead th{background:#f7f7f7}"
        ".muted{color:#666}"
        ".section{margin:18px 0}"
        ".pill{display:inline-block;background:#eef;border:1px solid #cde;border-radius:12px;padding:2px 8px;margin-right:6px}"
        ".btns a{display:inline-block;border:1px solid #444;padding:6px 10px;margin-right:8px;text-decoration:none}"
        "</style>"
    )

def build_site(norms_json: str, out_dir: str):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    norms = []
    p = Path(norms_json)
    if p.exists():
        norms = json.loads(p.read_text(encoding="utf-8"))

    # índice auxiliar para cruzar relações
    slug_by_key = {}
    for n in norms:
        s = _safe_slug(n.get("slug") or n.get("identificacao") or "")
        if not s:
            continue
        slug_by_key[s] = s
        ident = (n.get("identificacao") or "").strip().lower()
        if ident:
            slug_by_key[ident] = s

    # ===== INDEX (UI) =====
    # embute o JSON no HTML para a tabela dinâmica
    data_js = json.dumps(norms, ensure_ascii=False)

    tipos_check = "".join(
        "<label class='chip'><input type='checkbox' name='tipo' value='" + html.escape(t) + "'> " + html.escape(t) + "</label>"
        for t in TIPOS_FIXOS
    )

    search_ui = (
        "<!doctype html><meta charset='utf-8'>"
        "<title>banco-normativos-ba</title>"
        f"{_css()}"
        "<h1>Banco de Normativos de Beneficios Assistenciais</h1>"
        "<div class='panel'>Pesquisa</div>"
        "<div class='search'>"
        "<div class='chips'>" + tipos_check + "</div>"
        "<div class='grid'>"
        "<div class='col-3'><label>Número</label><input id='f-numero' type='text' placeholder='ex: 123'></div>"
        "<div class='col-3'><label>Ano</label><input id='f-ano' type='number' min='1900' max='2100' placeholder='ex: 2025'></div>"
        "<div class='col-6'><label>Argumento (identificação/ementa)</label><input id='f-arg' type='text' placeholder='palavra-chave'></div>"
        "<div class='col-4'><label>Temas</label><input id='f-tema' type='text' placeholder='ex: BPC'></div>"
        "<div class='col-4'><label>Origem</label><select id='f-origem'><option value=''>—</option></select></div>"
        "<div class='col-4'><label>Situação</label><select id='f-situacao'><option value=''>—</option><option value='Vigente'>Vigente</option><option value='Não vigente'>Não vigente</option></select></div>"
        "<div class='col-12' style='text-align:right'><button id='btn-buscar' class='btn'>Pesquisar</button></div>"
        "</div>"
        "<table>"
        "<thead><tr><th>Tipo</th><th>Número</th><th>Data</th><th>Origem</th><th>Situação</th><th>Ementa</th></tr></thead>"
        "<tbody id='grid'></tbody>"
        "</table>"
        "</div>"
        "<script>"
        "const DATA = " + data_js + ";"
        "function slug(s){return (s||'').toLowerCase().normalize('NFKD').replace(/[^a-z0-9\\- ]/g,'').replace(/[\\s_]+/g,'-').replace(/-+/g,'-').replace(/^-|-$/g,'');}"
        "function val(x){return (x||'').toString();}"
        "function getOrigem(n){return val(n.origem|| (n.raw && (n.raw['Origem']||n.raw['Órgão']||n.raw['ORIGEM'])) );}"
        "function getTema(n){return val(n.tema|| (n.raw && (n.raw['TEMA']||n.raw['Tema'])) );}"
        "function getData(n){return val(n.data|| (n.raw && (n.raw['DATA']||n.raw['Data'])) );}"
        "function unique(xs){return Array.from(new Set(xs.filter(Boolean)));}"
        "function fillOrigem(){"
        "  const opts = unique(DATA.map(getOrigem)).sort();"
        "  const sel = document.getElementById('f-origem');"
        "  opts.forEach(o=>{const op=document.createElement('option');op.value=o;op.textContent=o||'—';sel.appendChild(op);});"
        "}"
        "function render(rows){"
        "  const tb=document.getElementById('grid'); tb.innerHTML='';"
        "  if(rows.length===0){tb.innerHTML='<tr><td colspan=6 class=\"muted\">Nenhum resultado.</td></tr>';return;}"
        "  rows.forEach(n=>{"
        "    const id = n.identificacao || (n.tipo+' '+(n.numero||'')+'/'+(n.ano||''));"
        "    const s = slug(n.slug || id);"
        "    const ementa = val(n.ementa || (n.raw && (n.raw['EMENTA']||n.raw['Ementa'])));"
        "    const linha = '<tr>' +"
        "      '<td>'+ (n.tipo||'') +'</td>' +"
        "      '<td><a href=\"'+ s +'.html\">'+ (n.numero||'') +'</a></td>' +"
        "      '<td>'+ (getData(n)||'') +'</td>' +"
        "      '<td>'+ (getOrigem(n)||'') +'</td>' +"
        "      '<td>'+ (n.vigencia||'') +'</td>' +"
        "      '<td>'+ (ementa||'') +'</td>' +"
        "    '</tr>';"
        "    tb.insertAdjacentHTML('beforeend', linha);"
        "  });"
        "}"
        "function doSearch(){"
        "  const tipos = Array.from(document.querySelectorAll('input[name=tipo]:checked')).map(i=>i.value.toLowerCase());"
        "  const num = document.getElementById('f-numero').value.trim().toLowerCase();"
        "  const ano = document.getElementById('f-ano').value.trim();"
        "  const arg = document.getElementById('f-arg').value.trim().toLowerCase();"
        "  const tema = document.getElementById('f-tema').value.trim().toLowerCase();"
        "  const origem = document.getElementById('f-origem').value.trim().toLowerCase();"
        "  const sit = document.getElementById('f-situacao').value.trim().toLowerCase();"
        "  const out = DATA.filter(n=>{"
        "    const t = (n.tipo||'').toLowerCase();"
        "    const okTipo = (tipos.length===0) || tipos.includes(t);"
        "    const okNum = !num || (val(n.numero).toLowerCase().includes(num));"
        "    const okAno = !ano || (val(n.ano)===ano);"
        "    const pack = (val(n.identificacao)+' '+val(n.ementa)).toLowerCase();"
        "    const okArg = !arg || pack.includes(arg);"
        "    const okTema = !tema || getTema(n).toLowerCase().includes(tema);"
        "    const okOrigem = !origem || getOrigem(n).toLowerCase()===origem;"
        "    const okSit = !sit || (val(n.vigencia).toLowerCase()===sit);"
        "    return okTipo && okNum && okAno && okArg && okTema && okOrigem && okSit;"
        "  });"
        "  render(out);"
        "}"
        "fillOrigem();"
        "document.getElementById('btn-buscar').addEventListener('click', doSearch);"
        "render(DATA);"
        "</script>"
    )

    (out / "index.html").write_text(search_ui, encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")

    # ===== DETALHE =====
    def links_oficiais(n):
        links = []
        if n.get("tipo") in {"Lei", "Decreto", "lei", "decreto"} and n.get("fonte_planalto"):
            links.append(_a(n["fonte_planalto"], "Ver no Planalto"))
        if n.get("fonte_dou"):
            links.append(_a(n["fonte_dou"], "Ver no DOU"))
        return SEP.join([x for x in links if x]) or "<span class='muted'>—</span>"

    for i, n in enumerate(norms, start=1):
        titulo = n.get("identificacao") or n.get("slug") or f"Norma {i}"
        slug = _safe_slug(n.get("slug") or titulo, fallback="norma-" + str(i))

        btns = []
        if _is_url(n.get("texto_original")):
            btns.append(_a(n["texto_original"], "Texto original"))
        if _is_url(n.get("texto_compilado")):
            btns.append(_a(n["texto_compilado"], "Texto compilado"))
        btns_html = " ".join(btns)

        def _resolve_list(val):
            if not val:
                return []
            items = [x.strip() for x in str(val).split(";") if x.strip()]
            out_links = []
            for it in items:
                key = it.strip().lower()
                target_slug = slug_by_key.get(key) or slug_by_key.get(_safe_slug(key))
                label = html.escape(it)
                if target_slug:
                    out_links.append(f'<a href="{target_slug}.html">{label}</a>')
                else:
                    out_links.append(label)
            return out_links

        altera = _resolve_list(n.get("altera") or n.get("altera_ids") or n.get("alteracoes"))
        alterado_por = _resolve_list(n.get("alterado_por") or n.get("alterado_por_ids"))
        correlatas = _resolve_list(n.get("relacionados") or n.get("legislacao_correlata"))

        # metadados
        meta_rows = []
        raw = n.get("raw") or {}
        raw_cols = n.get("raw_columns") or list(raw.keys())
        for col in raw_cols:
            val = raw.get(col, "")
            cell = _a(val, val) if _is_url(val) else html.escape(val)
            meta_rows.append(f"<tr><th align='left'>{html.escape(col)}</th><td>{cell}</td></tr>")
        meta_table = (
            "<div class='section'>"
            "<h3>Metadados da planilha</h3>"
            "<table>" + "".join(meta_rows) + "</table>"
            "</div>"
        )

        detail_html = (
            "<!doctype html><meta charset='utf-8'>"
            "<title>" + html.escape(titulo) + "</title>"
            + _css() +
            '<p><a href="index.html">← Voltar</a></p>'
            "<h2>" + html.escape(titulo) + "</h2>"
            "<p><strong>Vigência:</strong> " + html.escape(n.get("vigencia","") or "—") +
            SEP + "<strong>Tema:</strong> " + html.escape(n.get("tema","") or "—") + "</p>" +
            ("<div class='section'>" + btns_html + "</div>" if btns_html else "") +
            "<div class='section'><strong>Fontes oficiais:</strong> " + links_oficiais(n) + "</div>" +
            (("<div class='section'><strong>Alterações que ESTE ato faz:</strong> " + SEP.join(altera) + "</div>") if altera else "") +
            (("<div class='section'><strong>Este ato foi ALTERADO por:</strong> " + SEP.join(alterado_por) + "</div>") if alterado_por else "") +
            (("<div class='section'><strong>Legislação correlata:</strong> " + SEP.join(correlatas) + "</div>") if correlatas else "") +
            "<hr><p><em>Texto compilado</em> e histórico virão aqui em versões futuras.</p>" +
            meta_table
        )
        (out / (slug + ".html")).write_text(detail_html, encoding="utf-8")
