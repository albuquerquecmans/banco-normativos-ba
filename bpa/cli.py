import click
from pathlib import Path

@click.group()
def cli():
    """CLI do Banco de Normativos (BPA)."""
    ...

@cli.command()
@click.argument("xlsx", type=click.Path(exists=True))
def ingest(xlsx):
    click.echo(f"Ingerindo planilha: {xlsx}")

@cli.command()
@click.option("--since", default=None, help="Controle de busca incremental")
def monitor(since):
    click.echo(f"Monitorando DOU/Planalto/LexML desde: {since}")

@cli.command()
def consolidate():
    click.echo("Consolidando versões (multivigente)…")

@cli.command()
@click.option("--out", default="_site")
@click.option("--sqlite", default=None)
def publish(out, sqlite):
    Path(out).mkdir(parents=True, exist_ok=True)
    click.echo(f"Gerando site estático em: {out}")

if __name__ == "__main__":
    cli()

