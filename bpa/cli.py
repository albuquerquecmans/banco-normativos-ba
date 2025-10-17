from __future__ import annotations
from pathlib import Path
import click

from bpa.extract.xlsx_ingest import write_norms_json
from bpa.publish.emit_site import build_site

@click.group()
def cli():
    """Ferramentas do Banco de Normativos (ingest / publish)."""
    pass

@cli.command()
@click.argument("xlsx", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--out-json", "out_json", type=click.Path(dir_okay=False, path_type=Path), default=Path("data/norms.json"))
def ingest(xlsx: Path, out_json: Path):
    """Lê a PLANILHA XLSX e gera data/norms.json normalizado."""
    click.echo(f">> Lendo: {xlsx}")
    write_norms_json(xlsx, out_json)
    click.echo(f">> Gravado: {out_json}")

@cli.command()
@click.option("--json", "json_path", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=Path("data/norms.json"))
@click.option("--out", "out_dir", type=click.Path(file_okay=False, path_type=Path), default=Path("_site"))
@click.option("--sqlite", "sqlite_path", type=click.Path(dir_okay=False, path_type=Path), default=Path("_site/bpc_normativos.sqlite"))
def publish(json_path: Path, out_dir: Path, sqlite_path: Path):
    """Gera o site estático em OUT a partir do JSON (sqlite reservado para uso futuro)."""
    click.echo(">> Publicando site...")
    out_dir.mkdir(parents=True, exist_ok=True)
    build_site(str(json_path), str(out_dir))
    click.echo(f">> Arquivos em: {out_dir}")

if __name__ == "__main__":
    cli()
