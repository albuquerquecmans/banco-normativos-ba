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
    txt = re.sub(r"[^a-z0-9\-]+", "-", txt)
    txt = txt.replace("/", "-").replace("\\", "-").replace(".", "-")
    txt = re.sub(r"-{2,}", "-", txt).strip("-")
    return txt or fallback

XLSX = "data/Normativas_Beneficios_Assistenciais_CGRAN.xlsx"
OUT  = "data/norms.json"
MAP  = "data/cols_map.json"

df = pd.read_excel(XLSX, dtype=str, engine="openpyxl").fillna("")
print(">> COLUNAS:", [str(c) for c in df.columns])
print(">> HEAD(3):")
print(df.head(3).to_string(index=False))

# Se existir um mapeamento explícito, use
cols_map = {}
if Path(MAP).exists():
    cols_map = json.loads(Path(MAP).read_text(encoding="utf-8"))
    print(">> cols_map.json encontrado:", cols_map)

# Índice rápido: nome normalizado -> nome original
norm2real = {norm(c): c for c in df.columns}

# Sinônimos default (serão ignorados se cols_map tiver o alvo)
SYN = {
    "tipo": ["tipo", "tipo do ato", "ato", "tipo_ato", "especie", "espécie"],
    "numero": ["numero", "número", "n", "num"],
    "ano": ["ano", "ano do ato", "ano_publicacao", "ano_publicação"],
    "identificacao": ["identificacao", "identificação", "ato normativo", "referencia", "referência", "titulo", "título"],
    "ementa": ["ementa", "descricao", "descrição", "assunto", "descricao resumida", "ementa/assunto"],
    "data": ["data", "data_publicacao", "data publicação", "data de publicacao", "dt_publicacao", "publicacao", "publicação"],
    "vigencia": ["vigencia", "vigência", "status", "situacao", "situação"],
    "tema": ["tema", "assunto principal", "tema principal"],
    "subtemas": ["subtemas", "sub-temas", "subtema", "subtema(s)", "sub-assunto"],
    "link_planalto": ["link_planalto", "planalto", "url_planalto", "site planalto"],
    "link_dou": ["link_dou", "dou", "url_dou", "diario oficial", "diário oficial"],
    "link": ["link", "url", "href"],
}

def resolve_column(target_key):
    """Retorna o nome REAL da coluna para uma chave canônica (tipo, numero, ...)."""
    # 1) Config mapeada
    if target_key in cols_map and cols_map[target_key]:
        return cols_map[target_key]
    # 2) Sinônimos
    for cand in SYN.get(target_key, []):
        c = norm2real.get(norm(cand))
        if c:
            return c
    return None

def pick(row, target_key):
    real = resolve_column(target_key)
    if not real:
        return ""
    v = row.get(real, "")
    if v is None:
        return ""
    v = str(v).strip()
    # Tira lixo comum
    return v if v not in {"/", "-", "--"} else ""

recs = []
for idx, row in df.iterrows():
    tipo   = pick(row, "tipo")
    numero = pick(row, "numero")
    ano    = pick(row, "ano")
    ident  = pick(row, "identificacao")
    if not ident:
        # tenta derivar um título
        ident = f"{(tipo or '').strip()} {(numero or '').strip()}/{(ano or '').strip()}".strip()
        if not ident or ident in {"/", "-", "--", "/ /"}:
            ident = pick(row, "ementa") or f"Ato-{idx+1}"

    slug = safe_slug(tipo, numero, ano, fallback=f"norma-{idx+1}")
    if slug in {"", "-", "/"}:
        slug = safe_slug(ident, fallback=f"norma-{idx+1}")

    fonte_planalto = pick(row, "link_planalto")
    fonte_dou      = pick(row, "link_dou")
    if not (fonte_planalto or fonte_dou):
        link = pick(row, "link")
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
        "ementa": pick(row, "ementa"),
        "data": pick(row, "data"),
        "vigencia": pick(row, "vigencia") or "Vigente",
        "tema": pick(row, "tema"),
        "subtemas": pick(row, "subtemas"),
        "fonte_planalto": fonte_planalto,
        "fonte_dou": fonte_dou,
    })

Path("data").mkdir(exist_ok=True)
Path(OUT).write_text(json.dumps(recs, ensure_ascii=False, indent=2), encoding="utf-8")
print("fallback wrote", len(recs), "records to", OUT)

# Mostra um preview dos 5 primeiros
print(">> PREVIEW (5):", [r.get("identificacao") for r in recs[:5]])
