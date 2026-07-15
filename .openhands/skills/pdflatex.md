---
name: pdflatex
type: knowledge
version: 1.0
agent: Manus
triggers:
  - latex
  - tex
  - pdf
  - thesis
  - compile
---
LaTeX workflow:
1. Keep `.tex`, generated assets, `.log`, and final `.pdf` in the conversation workspace.
2. Compile with `latexmk -pdf -interaction=nonstopmode` when available, otherwise use repeated `pdflatex`.
3. Do not claim success until a non-empty PDF exists.
4. If no PDF exists, inspect the `.log`, fix the first real error, and compile again.
5. Summarize the output filename and any remaining warnings.
