from __future__ import annotations
from pathlib import Path
import json, re, unicodedata
from typing import List, Dict, Any, Set
import pandas as pd

# ----------------- utilitários de normalização -----------------

def _strip_accents(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode("ascii")

def _norm_name(s: str) -> str:
    s = str(s or "").strip()
    s = _strip_accents(s).upper()
    return re.sub(r"\s+"," ",s)

def _norm_val(s: Any) -> str:
    return ("" if s is None else str(s)).strip()

def _slugify(s: str) -> str:
    s = _strip_accents(s).lower()
    s = re.sub(r"[^a-z0-9\-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s

# ----------------- heurística de cabeçalho -----------------

EXPECTED_TOKENS = {
    "TIPO","VIGENCIA","IDENTIFICACAO","EMENTA","DATA","ANO",
    "TEMA","SUBTEMA(S)","ORIGEM","SITUACAO","STATUS",
}

def _score_header_row(cells: List[str]) -> int:
    toks = {_norm_name(c) for c in cells if _norm_name(c)}
    return sum(1 for t in EXPECTED_TOKENS if t in toks)

def _find_header_index(df_raw: pd.DataFrame) -> int:
    best_idx,best_score = 0,-1
    for i in range(min(10,len(df_raw))):
        row = [str(x) for x in df_raw.iloc[i].tolist()]
        sc = _score_header_row(row)
        if sc>best_score:
            best_idx,best_score = i,sc
    return best_idx

# ----------------- mapeamento de colunas -----------------

COLS_VARIANTS = {
    "tipo": ["TIPO"],
    "vigencia": ["VIGENCIA","SITUACAO","STATUS"],
    "identificacao": ["IDENTIFICACAO","IDENTIFICAÇÃO","IDENT.","IDENT."],
    "ementa": ["EMENTA","EMENTA RESUMIDA","EMENTA (RESUMO)","RESUMO"],
    "data": ["DATA","DATA DE PUBLICACAO","DATA DA PUBLICACAO","PUBLICACAO","DATA (DOU)","DATA DOU","DATA PUBLICACAO"],
    "ano": ["ANO"],
    "tema": ["TEMA","ASSUNTO","ASSUNTOS"],
    "origem": ["ORIGEM","ORGAO","ORGAO/UNIDADE","ORGAO EMISSOR","ÓRGÃO EMISSOR"],
    "numero": ["NUMERO","NUMERO/ANO","Nº","NO"],
    # fontes/urls usadas nos detalhes
    "fonte_planalto": ["FONTE PLANALTO","URL PLANALTO","PLANALTO"],
    "fonte_dou": ["FONTE DOU","URL DOU","DOU"],
    "texto_original": ["TEXTO ORIGINAL","URL TEXTO ORIGINAL"],
    "texto_compilado": ["TEXTO COMPILADO","URL TEXTO COMPILADO"],
}
COLS_INDEX: Dict[str,str] = {}
for k,variants in COLS_VARIANTS.items():
    for v in variants:
        COLS_INDEX[_norm_name(v)] = k

def _map_columns(header_row: List[str]) -> Dict[str,int]:
    mapping: Dict[str,int] = {}
    for idx,col in enumerate(header_row):
        norm = _norm_name(col)
        if norm and norm in COLS_INDEX:
            mapping.setdefault(COLS_INDEX[norm], idx)
    return mapping

# ----------------- inferências a partir de IDENTIFICAÇÃO -----------------

def _infer_tipo_from_ident(ident: str) -> str:
    s = _strip_accents(ident).lower()
    pairs = [
        ("portaria interministerial","Portaria Interministerial"),
        ("portaria conjunta","Portaria Conjunta"),
        ("portaria inss","Portaria INSS"),
        ("portaria mds","Portaria MDS"),
        ("instrucao normativa","Instrução Normativa"),
        ("instrucao operacional","Instrução Operacional"),
        ("memorando circular","Memorando Circular"),
        ("orientacao interna","Orientação Interna"),
        ("medida provisoria","Medida Provisória"),
        ("resolucao","Resolução"),
        ("decreto","Decreto"),
        ("lei","Lei"),
        ("portaria","Portaria"),
    ]
    for k,v in pairs:
        if k in s:
            return v
    return ""

def _infer_numero_from_ident(ident: str) -> str:
    m = re.search(r"n[ºo]\s*([0-9\.\-\/]+)", ident, flags=re.I)
    if m: return m.group(1)
    m2 = re.search(r"\b(\d{1,6}[\.\/]\d{4})\b", ident)
    return m2.group(1) if m2 else ""

def _year_from_numero(numero: str) -> str:
    m = re.search(r"(\d{4})$", numero or "")
    return m.group(1) if m else ""

def _map_vigencia(v: str) -> str:
    s = _strip_accents(v).lower()
    if not s: return ""
    if "vigente" in s or s=="v": return "Vigente"
    if "revog" in s or s=="r": return "Revogada"
    if "suspens" in s: return "Suspensa"
    if "nao vigente" in s or "não vigente" in v.lower(): return "Não vigente"
    return v.strip()

# ----------------- lógica de slug único -----------------

def _unique_slug(base_slug: str, tipo: str, numero: str, ano: str, taken: Set[str]) -> str:
    """
    Garante unicidade do slug:
      1) base_slug
      2) se ocupar, tenta: tipo-numero-ano
      3) se ainda bater, acrescenta -2, -3, ...
    """
    cand = _slugify(base_slug) or "norma"
    if cand not in taken:
        taken.add(cand)
        return cand

    tna_parts = [p for p in [_slugify(tipo), _slugify(numero), _slugify(ano)] if p]
    if tna_parts:
        cand2 = "-".join(tna_parts)
        if cand2 and cand2 not in taken:
            taken.add(cand2)
            return cand2

    i = 2
    while True:
        c = f"{cand}-{i}"
        if c not in taken:
            taken.add(c)
            return c
        i += 1

# ----------------- principal -----------------

def read_xlsx_to_json(xlsx_path: str | Path):
    df_raw = pd.read_excel(xlsx_path, header=None, dtype=str, engine="openpyxl").fillna("")
    header_idx = _find_header_index(df_raw)
    header = [str(x) for x in df_raw.iloc[header_idx].tolist()]
    col_map = _map_columns(header)
    df = df_raw.iloc[header_idx+1:].reset_index(drop=True)

    records = []
    used_slugs: Set[str] = set()

    for _,row in df.iterrows():
        row_vals = [str(x) for x in row.tolist()]
        if not any(_norm_val(x) for x in row_vals):
            continue

        raw_dict = {str(header[i]): _norm_val(row_vals[i]) for i in range(len(header))}
        raw_cols = [str(h) for h in header]

        def get_can(key: str) -> str:
            return _norm_val(row_vals[col_map[key]]) if key in col_map else ""

        ident = get_can("identificacao")
        tipo = get_can("tipo") or _infer_tipo_from_ident(ident)
        numero = get_can("numero") or _infer_numero_from_ident(ident)
        ano = get_can("ano") or _year_from_numero(numero)
        data = get_can("data")
        ementa = get_can("ementa")
        tema = get_can("tema")
        origem = get_can("origem")
        vigencia = _map_vigencia(get_can("vigencia"))

        fonte_planalto = get_can("fonte_planalto")
        fonte_dou = get_can("fonte_dou")
        texto_original = get_can("texto_original")
        texto_compilado = get_can("texto_compilado")

        base = ident or f"{tipo} {numero or ''} {ano or ''}".strip()
        slug = _unique_slug(base, tipo, numero, ano, used_slugs)

        records.append({
            "slug": slug,
            "tipo": tipo,
            "numero": numero,
            "ano": ano,
            "data": data,
            "vigencia": vigencia,
            "identificacao": ident,
            "ementa": ementa,
            "tema": tema,
            "origem": origem,
            "fonte_planalto": fonte_planalto,
            "fonte_dou": fonte_dou,
            "texto_original": texto_original,
            "texto_compilado": texto_compilado,
            "raw": raw_dict,
            "raw_columns": raw_cols,
        })
    return records

def write_norms_json(xlsx_path: str | Path, out_json: str | Path) -> None:
    data = read_xlsx_to_json(xlsx_path)
    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(out_json).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
