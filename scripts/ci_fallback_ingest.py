# scripts/ci_fallback_ingest.py
from pathlib import Path
import pandas as pd, json, unicodedata

def norm(s):
    if s is None: return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode("ascii")
    return s.strip().lower()

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
for _, row in df.iterrows():
    tipo  = pick(row, "tipo", "ato", "tipo do ato")
    numero= pick(row, "numero", "n")
    ano   = pick(row, "ano")
    ident = pick(row, "identificacao", "identificação", "ato normativo", "referencia", "referência") or f"{tipo} {numero}/{ano}".strip()
    if not (tipo or numero or ano or ident):
        continue
    slug = "-".join([x for x in [tipo, numero, ano] if x]).replace(" ", "-").lower() or ident.replace(" ", "-").lower()

    fonte_planalto = pick(row, "link_planalto", "planalto", "url_planalto")
    fonte_dou      = pick(row, "link_dou", "dou", "url_dou")
    if not (fonte_planalto or fonte_dou):
        link = pick(row, "link", "url", "href")
        if norm(tipo) in {"lei","decreto"}:
            fonte_planalto = link
        else:
            fonte_dou = link

    recs.append({
        "slug": slug,
        "tipo": tipo, "numero": numero, "ano": ano,
        "identificacao": ident,
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
