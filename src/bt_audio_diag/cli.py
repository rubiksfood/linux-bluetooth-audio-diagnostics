from importlib.metadata import version as distribution_version
from typing import Annotated

import typer

_DISTRIBUTION_NAME = "linux-bluetooth-audio-diagnostics"

app = typer.Typer(
    help="Inspect and diagnose Linux Bluetooth audio environments.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"bt-audio-diag {distribution_version(_DISTRIBUTION_NAME)}")
        raise typer.Exit()


@app.callback()
def root(
    _version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the application version and exit.",
        ),
    ] = None,
) -> None:
    """Inspect and diagnose Linux Bluetooth audio environments."""


def main() -> None:
    app()
