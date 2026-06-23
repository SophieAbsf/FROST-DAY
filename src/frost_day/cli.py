"""Console script for frost_day."""

import typer
from rich.console import Console

from frost_day import utils

app = typer.Typer()
console = Console()


@app.command()
def main() -> None:
    """Console script for frost_day."""
    console.print("Replace this message by putting your code into frost_day.cli.main")
    console.print("See Typer documentation at https://typer.tiangolo.com/")
    utils.do_something_useful()


if __name__ == "__main__":
    app()
