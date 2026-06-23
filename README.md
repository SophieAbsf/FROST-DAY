# FROST-DAY

![PyPI version](https://img.shields.io/pypi/v/frost_day.svg)

Voici une brève description :

* [GitHub](https://github.com/SophieAbsf/frost_day/) | [PyPI](https://pypi.org/project/frost_day/) | [Documentation](https://SophieAbsf.github.io/frost_day/)
* Created by [Sophie](**Une application dédiée à l'analyse de l'impact du gel sur les cultures et l'environnement, conçue pour accompagner les agriculteurs, les jardiniers, les chercheurs en climatologie et toute personne intéressée par les phénomènes climatiques.**) | GitHub [@SophieAbsf](https://github.com/SophieAbsf) | PyPI [@SophieAbsf](https://pypi.org/user/SophieAbsf/)
* MIT License

## Features

* TODO

## Documentation

Documentation is built with [Zensical](https://zensical.org/) and deployed to GitHub Pages.

* **Live site:** https://SophieAbsf.github.io/frost_day/
* **Preview locally:** `just docs-serve` (serves at http://localhost:8000)
* **Build:** `just docs-build`

API documentation is auto-generated from docstrings using [mkdocstrings](https://mkdocstrings.github.io/).

Docs deploy automatically on push to `main` via GitHub Actions. To enable this, go to your repo's Settings > Pages and set the source to **GitHub Actions**.

## Development

To set up for local development:

```bash
# Clone your fork
git clone git@github.com:your_username/frost_day.git
cd frost_day

# Install in editable mode with live updates
uv tool install --editable .
```

This installs the CLI globally but with live updates - any changes you make to the source code are immediately available when you run `frost_day`.

Run tests:

```bash
uv run pytest
```

Run quality checks (format, lint, type check, test):

```bash
just qa
```

## Author

FROST-DAY was created in 2026 by Sophie.

Built with [Cookiecutter](https://github.com/cookiecutter/cookiecutter) and the [audreyfeldroy/cookiecutter-pypackage](https://github.com/audreyfeldroy/cookiecutter-pypackage) project template.
