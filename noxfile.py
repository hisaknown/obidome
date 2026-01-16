"""Nox configuration file."""

import nox


@nox.session(venv_backend="uv", python="3.13", tags=["format"])
def format_(session: nox.Session) -> None:
    """Run code formatters."""
    session.install("-e", ".", "--group", "dev")
    session.run("uv", "run", "--active", "ruff", "format", "src")

@nox.session(venv_backend="uv", python="3.13", tags=["lint"])
def lint(session: nox.Session) -> None:
    """Run code linters."""
    session.install("-e", ".", "--group", "dev")
    session.run("uv", "run", "--active", "ruff", "check", "--fix", "src")

@nox.session(venv_backend="uv", python="3.13", tags=["typecheck"])
def typecheck(session: nox.Session) -> None:
    """Run type checker."""
    session.install("-e", ".", "--group", "dev")
    session.run("uv", "run", "--active", "pyright", "src")

@nox.session(venv_backend="uv", python="3.13", tags=["build"])
def build_with_nuitka(session: nox.Session) -> None:
    """Build the application using Nuitka."""
    session.install("-e", ".", "--group", "dev")
    session.run(
        "uv",
        "run",
        "--active",
        "nuitka",
        "--enable-plugin=pyside6",
        "--standalone",
        "--onefile",
        "--follow-imports",
        "--output-dir=.nuitka",
        "src/obidome/main.py",
    )

nox.options.sessions = ["format_", "lint", "typecheck"]
