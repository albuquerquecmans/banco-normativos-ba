# scripts/ci_fallback_ingest.py
from pathlib import Path
import pandas as pd, json, unicodedata, re

XLSX = "data/Normativas_Beneficios_Assistenciais_CGRAN.xlsx"
OUT  = "data/norms.json"
MAP  = "data/cols_map.json"

# ---------- util ----------
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

def looks_url(v: str) -> bool:
    return bool(v) and isinstance(v, str) and re.match(r"^https?://", v.strip())

# ---------- carga ----------
df = pd.read_excel(XLSX, dtype=str, engine="openpyxl").fillna("")
print(">> COLUNAS:", [str(c) for c in df.columns])
print(">> HEAD(3):")
print(df.head(3).to_string(index=False))

# mapeamento opcional
cols_map = {}
pmap = Path(MAP)
if pmap.exists():
    cols_map = json.loads(pmap.read_text(encoding="utf-8"))
    print(">> cols_map.json:", cols_map)

norm2real = {norm(c): c for c in df.columns}

# sinônimos default (se não houver cols_map)
SYN = {
    "tipo": ["tipo", "tipo do ato", "ato", "especie", "espécie"],
    "numero": ["numero", "número", "n", "num"],
    "ano": ["ano", "ano do ato", "ano_publicacao", "ano_publicação"],
    "identificacao": ["identificacao", "identificação", "ato normativo", "referencia", "referência", "titulo", "título"],
    "ementa": ["ementa", "descricao", "descrição", "assunto", "ementa/assunto", "resumo"],
    "data": ["data", "data_publicacao", "publicacao", "publicação", "data de publicacao", "dt_publicacao"],
    "vigencia": ["vigencia", "vigência", "status", "situacao", "situação"],
    "tema": ["tema", "assunto principal", "tema principal"],
    "subtemas": ["subtemas", "sub-temas", "subtema", "subtema(s)", "sub-assunto"],
    "link_planalto": ["link_planalto", "planalto", "url_planalto", "site planalto"],
    "link_dou": ["link_dou", "dou", "url_dou", "diario oficial", "diário oficial"],
    "link": ["link", "url", "href"],
}

def resolve_column(target_key):
    # 1) explícito em cols_map
    if target_key in cols_map and cols_map[target_key]:
        return cols_map[target_key]
    # 2) sinônimos
    for cand in SYN.get(target_key, []):
        c = norm2real.get(norm(cand))
        if c:
            return c
    return None

def pick(row, target_key):
    real = resolve_column(target_key)
    if not real: return ""
    v = row.get(real, "")
    if v is None: return ""
    v = str(v).strip()
    return "" if v in {"/", "-", "--"} else v

# ---------- transformação ----------
records = []
for i, row in df.iterrows():
    # dict com TODOS os campos originais, preservando nomes da planilha
    raw = {str(k): ("" if v is None else str(v).strip()) for k, v in row.items()}

    # campos canônicos (se houver)
    tipo   = pick(row, "tipo")
    numero = pick(row, "numero")
    ano    = pick(row, "ano")
    ident  = pick(row, "identificacao")

    if not ident:
        ident = f"{(tipo or '').strip()} {(numero or '').strip()}/{(ano or '').strip()}".strip()
        if not ident or ident in {"/", "-", "--", "/ /"}:
            ident = pick(row, "ementa") or f"Ato-{i+1}"

    slug = safe_slug(tipo, numero, ano, fallback=f"norma-{i+1}")
    if slug in {"", "-", "/"}:
        slug = safe_slug(ident, fallback=f"norma-{i+1}")

    # links: tenta campos específicos; senão, varre colunas com URL
    fonte_planalto = pick(row, "link_planalto")
    fonte_dou      = pick(row, "link_dou")
    if not (fonte_planalto or fonte_dou):
        gen = pick(row, "link")
        if gen:
            if norm(tipo) in {"lei", "decreto"}:
                fonte_planalto = gen
            else:
                fonte_dou = gen
        else:
            # varredura: qualquer coluna que pareça URL
            for k, v in raw.items():
                if looks_url(v):
                    nk = norm(k)
                    if "planalto" in nk and not fonte_planalto:
                        fonte_planalto = v
                    elif any(x in nk for x in ["dou", "diario", "in.gov"]) and not fonte_dou:
                        fonte_dou = v

    rec = {
        # canônicos (para navegação e renderização)
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

        # TUDO que veio da planilha:
        "raw": raw,                   # dict com todos os campos originais
        "raw_columns": list(raw.keys())  # ordem dos campos (ajuda a exibir)
    }
    records.append(rec)

Path("data").mkdir(parents=True, exist_ok=True)
Path(OUT).write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
print(f">> Gravado {len(records)} registros em {OUT}")
print(">> PREVIEW (5):", [r["identificacao"] for r in records[:5]])
