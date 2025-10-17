# bpa/extract/xlsx_ingest.py
from __future__ import annotations

from pathlib import Path
import json
import re
import unicodedata
from typing import List, Dict, Any

import pandas as pd


# ------- Normalização de textos/nomes -------

def _strip_accents(s: str) -> str:
    return (
        unicodedata.normalize("NFKD", s)
        .encode("ascii", "ignore")
        .decode("ascii")
    )


def _norm_name(s: str) -> str:
    s = str(s or "").strip()
    s = _strip_accents(s).upper()
    s = re.sub(r"\s+", " ", s)
    return s


def _norm_val(s: Any) -> str:
    s = "" if s is None else str(s)
    return s.strip()


# ------- Heurística para detectar a linha de cabeçalho real -------

EXPECTED_TOKENS = {
    "TIPO", "VIGENCIA", "IDENTIFICACAO", "EMENTA", "DATA", "ANO",
    "TEMA", "SUBTEMA(S)", "ORIGEM", "SITUACAO", "STATUS",
}

def _score_header_row(cells: List[str]) -> int:
    """Conta quantos 'tokens esperados' aparecem nessa linha (normalizados)."""
    toks = {_norm_name(c) for c in cells if _norm_name(c)}
    hits = 0
    for t in EXPECTED_TOKENS:
        if t in toks:
            hits += 1
    return hits


def _find_header_index(df_raw: pd.DataFrame) -> int:
    """
    Procura nas primeiras ~10 linhas qual parece ser o cabeçalho verdadeiro.
    Retorna o índice dessa linha no df_raw.
    """
    best_idx, best_score = 0, -1
    max_probe = min(10, len(df_raw))
    for i in range(max_probe):
        row = [str(x) for x in df_raw.iloc[i].tolist()]
        score = _score_header_row(row)
        if score > best_score:
            best_idx, best_score = i, score
    return best_idx


# ------- Mapeamento de colunas possíveis -> chaves canônicas -------

COLS_VARIANTS = {
    "tipo": ["TIPO"],
    "vigencia": ["VIGENCIA", "SITUACAO", "STATUS"],
    "identificacao": ["IDENTIFICACAO", "IDENTIFICAÇÃO", "IDENT.", "IDENT."],
    "ementa": ["EMENTA", "EMENTA RESUMIDA", "EMENTA (RESUMO)", "RESUMO"],
    "data": [
        "DATA", "DATA DE PUBLICACAO", "DATA DA PUBLICACAO",
        "PUBLICACAO", "DATA (DOU)", "DATA DOU", "DATA PUBLICACAO",
    ],
    "ano": ["ANO"],
    "tema": ["TEMA", "ASSUNTO", "ASSUNTOS"],
    "origem": ["ORIGEM", "ORGAO", "ORGAO/UNIDADE", "ORGAO EMISSOR", "ÓRGÃO EMISSOR"],
    "numero": ["NUMERO", "NUMERO/ANO", "Nº", "NO"],
    # fontes (opcionais, usados nos detalhes)
    "fonte_planalto": ["FONTE PLANALTO", "URL PLANALTO", "PLANALTO"],
    "fonte_dou": ["FONTE DOU", "URL DOU", "DOU"],
    "texto_original": ["TEXTO ORIGINAL", "URL TEXTO ORIGINAL"],
    "texto_compilado": ["TEXTO COMPILADO", "URL TEXTO COMPILADO"],
}

# Index auxiliar: de nome normalizado -> chave canônica
COLS_INDEX: Dict[str, str] = {}
for k, variants in COLS_VARIANTS.items():
    for v in variants:
        COLS_INDEX[_norm_name(v)] = k


def _map_columns(header_row: List[str]) -> Dict[str, int]:
    """
    Recebe a linha de cabeçalho (lista de strings) e devolve um mapa:
      chave_canônica -> índice da coluna no DF
    """
    mapping: Dict[str, int] = {}
    for idx, col in enumerate(header_row):
        norm = _norm_name(col)
        if not norm:
            continue
        if norm in COLS_INDEX:
            can = COLS_INDEX[norm]
            # guarda o primeiro que aparecer
            mapping.setdefault(can, idx)
    return mapping


# ------- Extração de número/ano/tipo pela identificação -------

def _infer_tipo_from_ident(ident: str) -> str:
    s = _strip_accents(ident).lower()
    pairs = [
        ("portaria interministerial", "Portaria Interministerial"),
        ("portaria conjunta", "Portaria Conjunta"),
        ("portaria inss", "Portaria INSS"),
        ("portaria mds", "Portaria MDS"),
        ("instrucao normativa", "Instrução Normativa"),
        ("instrucao operacional", "Instrução Operacional"),
        ("memorando circular", "Memorando Circular"),
        ("orientacao interna", "Orientação Interna"),
        ("medida provisoria", "Medida Provisória"),
        ("resolucao", "Resolução"),
        ("decreto", "Decreto"),
        ("lei", "Lei"),
        ("portaria", "Portaria"),
    ]
    for needle, label in pairs:
        if needle in s:
            return label
    return ""


def _infer_numero_from_ident(ident: str) -> str:
    # n° 123/2020  | nº 123, de ... | 123/2020 etc.
    m = re.search(r"n[ºo]\s*([0-9\.\-\/]+)", ident, flags=re.I)
    if m:
        return m.group(1)
    m2 = re.search(r"\b(\d{1,6}[\.\/]\d{4})\b", ident)
    if m2:
        return m2.group(1)
    return ""


def _year_from_numero(numero: str) -> str:
    m = re.search(r"(\d{4})$", numero or "")
    return m.group(1) if m else ""


def _map_vigencia(v: str) -> str:
    s = _strip_accents(v).lower()
    if not s:
        return ""
    if "vigente" in s or s == "v":
        return "Vigente"
    if "revog" in s or s == "r":
        return "Revogada"
    if "suspens" in s:
        return "Suspensa"
    if "nao vigente" in s or "não vigente" in v.lower():
        return "Não vigente"
    return v.strip()


# ------- Função principal -------

def read_xlsx_to_json(xlsx_path: str | Path) -> List[Dict[str, Any]]:
    """
    Lê a planilha e devolve uma lista de registros prontos para o site.
    """
    df_raw = pd.read_excel(xlsx_path, header=None, dtype=str, engine="openpyxl")
    df_raw = df_raw.fillna("")

    header_idx = _find_header_index(df_raw)
    header = [str(x) for x in df_raw.iloc[header_idx].tolist()]
    col_map = _map_columns(header)

    # dados a partir da linha seguinte ao cabeçalho detectado
    df = df_raw.iloc[header_idx + 1 :].reset_index(drop=True)

    # records
    records: List[Dict[str, Any]] = []

    for _, row in df.iterrows():
        row_vals = [str(x) for x in row.tolist()]
        # pular linhas totalmente vazias
        if not any(_norm_val(x) for x in row_vals):
            continue

        raw_dict = {str(header[i]): _norm_val(row_vals[i]) for i in range(len(header))}
        raw_cols = [str(h) for h in header]

        def get_can(key: str) -> str:
            if key in col_map:
                return _norm_val(row_vals[col_map[key]])
            return ""

        ident = get_can("identificacao")
        tipo = get_can("tipo") or _infer_tipo_from_ident(ident)
        numero = get_can("numero") or _infer_numero_from_ident(ident)
        ano = get_can("ano") or _year_from_numero(numero)
        data = get_can("data")
        ementa = get_can("ementa")
        tema = get_can("tema")
        origem = get_can("origem")
        vigencia = _map_vigencia(get_can("vigencia"))

        # fontes/urls opcionais
        fonte_planalto = get_can("fonte_planalto")
        fonte_dou = get_can("fonte_dou")
        texto_original = get_can("texto_original")
        texto_compilado = get_can("texto_compilado")

        # slug estável (ident -> slug)
        base_slug = ident or f"{tipo} {numero or ''} {ano or ''}".strip()
        slug = re.sub(r"-+", "-", re.sub(r"[^a-z0-9\-]+", "-", _strip_accents(base_slug).lower())).strip("-") or "norma"

        rec = {
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
            # fontes/links (usados na página de detalhe)
            "fonte_planalto": fonte_planalto,
            "fonte_dou": fonte_dou,
            "texto_original": texto_original,
            "texto_compilado": texto_compilado,
            # para depuração / tabela de metadados
            "raw": raw_dict,
            "raw_columns": raw_cols,
        }

        records.append(rec)

    return records


def write_norms_json(xlsx_path: str | Path, out_json: str | Path) -> None:
    data = read_xlsx_to_json(xlsx_path)
    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(out_json).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
