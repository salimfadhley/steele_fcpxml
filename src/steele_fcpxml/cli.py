"""Command-line interface for steele-fcpxml.

Exposes ``steele-fcpxml validate <file>`` to validate an FCPXML file for
DaVinci Resolve compatibility. Structured as a :func:`click.group` so further
subcommands can be added without changing the entry point.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

import click

from steele_fcpxml.validator import FCPXMLValidator


@click.group()
@click.version_option(package_name="steele-fcpxml")
def main() -> None:
    """steele-fcpxml: tools for Final Cut Pro XML timelines."""


@main.command()
@click.argument("fcpxml_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed validation information",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON",
)
@click.option(
    "--fail-on-warning",
    is_flag=True,
    help="Treat warnings as errors (exit code 1)",
)
def validate(
    fcpxml_file: Path,
    verbose: bool,
    output_json: bool,
    fail_on_warning: bool,
) -> None:
    """Validate an FCPXML file for DaVinci Resolve compatibility.

    Examples:

        \b
        # Validate a single file
        steele-fcpxml validate timeline.fcpxml

        \b
        # Validate with verbose output
        steele-fcpxml validate -v timeline.fcpxml

        \b
        # Output as JSON
        steele-fcpxml validate --json timeline.fcpxml

        \b
        # Fail on warnings (useful in CI/CD)
        steele-fcpxml validate --fail-on-warning timeline.fcpxml
    """
    try:
        validator = FCPXMLValidator(fcpxml_file)
        result = validator.validate()

        if output_json:
            output = {
                "valid": result.valid,
                "errors": result.errors,
                "warnings": result.warnings,
                "info": {
                    k: v
                    for k, v in result.info.items()
                    if isinstance(v, (str, int, float, bool)) or v is None
                },
            }
            click.echo(json.dumps(output, indent=2))
        else:
            report = validator.generate_report(result)
            click.echo(report)

            if verbose and result.info.get("clips"):
                click.echo("\nClip Details:")
                click.echo("-" * 70)
                for i, clip in enumerate(result.info["clips"], 1):
                    click.echo(f"\nClip {i}: {clip.name}")
                    click.echo(f"  Offset: {clip.offset:.1f}s")
                    click.echo(f"  Duration: {clip.duration:.1f}s")
                    click.echo(f"  Timeline Start: {clip.start:.1f}s")
                    if clip.note:
                        click.echo(f"  Note: {clip.note}")

        # Exit code
        if not result.valid:
            sys.exit(1)
        elif fail_on_warning and result.warnings:
            sys.exit(1)
        else:
            sys.exit(0)

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:  # noqa: BLE001 - CLI boundary backstop (standards §2)
        click.echo(f"Unexpected error: {e}", err=True)
        if verbose:
            traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
