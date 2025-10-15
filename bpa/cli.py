import click
from pathlib import Path
from bpa.extract.spreadsheet import read_xlsx_to_json
from bpa.publish.emit_site import build_site

@click.group()
def cli():
    """CLI do Banco de Normativos (BPA)."""
    ...

@cli.command()
@click.argument("xlsx", type=click.Path(exists=True))
@click.option("--out-json", default="data/norms.json", help="Arquivo de saida JSON com as normas")
def ingest(xlsx, out_json):
    click.echo(f"Ingerindo planilha: {xlsx}")
    read_xlsx_to_json(xlsx, out_json)
    click.echo(f"OK: {out_json}")

@cli.command()
@click.option("--since", default=None, help="Controle de busca incremental")
def monitor(since):
    click.echo(f"(mock) Monitorando desde: {since}")
    # TODO: implementar DOU/Planalto/LexML

@cli.command()
def consolidate():
    click.echo("(mock) Consolidando versoes (multivigente)...")
    # TODO: provision_versions

@cli.command()
@click.option("--out", default="_site", help="Diretorio de saida do site")
@click.option("--sqlite", default=None, help="Caminho do SQLite (opcional)")
def publish(out, sqlite):
    Path(out).mkdir(parents=True, exist_ok=True)
    click.echo(f"Publicando site em: {out}")
    build_site("data/norms.json", out)
    click.echo("OK: site gerado")
