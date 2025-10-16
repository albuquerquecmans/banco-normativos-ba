# scripts/ci_fallback_ingest.py
from pathlib import Path
import pandas as pd, json, unicodedata, re

def norm(s):
    if s is None: return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode("ascii")
    return s.strip().lower()

def safe_slug(*parts, fallback="item"):
    txt = "-".join([p for p in parts if p]).strip().lower()
    if not txt:
        txt = fallback
    # troca qualquer coisa que nao seja [a-z0-9-] por "-"
    txt = re.sub(r"[^a-z0-9\-]+", "-", txt)
    # remove barras, pontos e hifens extras
    txt = txt.replace("/", "-").replace("\\", "-").replace(".", "-")
    txt = re.sub(r"-{2,}", "-", txt).strip("-")
    return txt or fallback

XLSX = "data/Normativas_Beneficios_Assistenciais_CGRAN.xlsx"
OUT  = "data/norms.json"

df = pd.read_excel(XLSX, dtype=str, engine="openpyxl").fillna("")
cols = {norm(c): c for c in df.columns}

def pick(row, *names):
    for name in names:
        col = cols.get(norm(name))
        if col:
            v = row.get(col, "")
            v = "" if v is None else str(v).strip()
            if v:
                return v
    return ""

recs = []
for idx, row in df.iterrows():
    tipo   = pick(row, "tipo", "ato", "tipo do ato")
    numero = pick(row, "numero", "n")
    ano    = pick(row, "ano")

    ident  = pick(row, "identificacao", "identificação", "ato normativo", "referencia", "referência")
    # se a identificacao for vazia/inutil ('/', '-', etc.), cria uma
    if ident in {"", "/", "-", "--"}:
        ident = f"{(tipo or '').strip()} {(numero or '').strip()}/{(ano or '').strip()}".strip()
        if ident in {"/", "-", "", "/ /"}:
            ident = pick(row, "ementa", "descricao", "descrição") or f"Ato-{idx+1}"

    # slug seguro
    slug = safe_slug(tipo, numero, ano, fallback=f"norma-{idx+1}")
    if slug in {"", "-", "/"}:
        slug = safe_slug(ident, fallback=f"norma-{idx+1}")

    # fontes (preferimos campos especificos, caindo para 'link' generico)
    fonte_planalto = pick(row, "link_planalto", "planalto", "url_planalto", "site planalto")
    fonte_dou      = pick(row, "link_dou", "dou", "url_dou", "diario oficial")
    if not (fonte_planalto or fonte_dou):
        link = pick(row, "link", "url", "href")
        if norm(tipo) in {"lei","decreto"}:
            fonte_planalto = link
        else:
            fonte_dou = link

    recs.append({
        "slug": slug,
        "tipo": tipo or "",
        "numero": numero or "",
        "ano": ano or "",
        "identificacao": ident or slug,
        "vigencia": pick(row, "vigencia", "vigência", "status") or "Vigente",
        "tema": pick(row, "tema", "assunto"),
        "subtemas": pick(row, "subtemas", "subtema", "subtema(s)"),
        "fonte_planalto": fonte_planalto,
        "fonte_dou": fonte_dou,
    })

Path("data").mkdir(exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(recs, f, ensure_ascii=False, indent=2)

print("fallback wrote", len(recs), "records to", OUT)
