---
paths:
  - "docs/**/*.md"
  - "mkdocs.yml"
  - "README.md"
  - "CHANGELOG.md"
---

# Documentation Rules

- After ANY code change (new features, API changes, fixes), immediately update the corresponding docs
- New feature → update relevant guide + API page + CHANGELOG.md
- API change → update the api/ page for that module
- New example → update examples/index.md
- Build: `PYTHONIOENCODING=utf-8 python -m mkdocs build` (Windows needs UTF-8 env var)
- Serve: `PYTHONIOENCODING=utf-8 python -m mkdocs serve -a 127.0.0.1:8100`
- Deploy: `mkdocs gh-deploy` (GitHub Pages)
- API reference is auto-generated from docstrings via `mkdocstrings` — use `::: module.Class` directives
- Docs structure: `docs/` → index.md, getting-started/ (3), guides/ (15), api/ (10), examples/, changelog.md
