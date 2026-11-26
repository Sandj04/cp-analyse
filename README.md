# Short-form video's en werkgeheugen

Analyse van de relatie tussen het dagelijkse gebruik van short-form video's en werkgeheugenprestaties (2-back-taak) bij studenten. De analyse staat in `notebook.ipynb`.

## Build notebook -> [GH pages](https://sandj04.github.io/cp-analyse/)

De notebook wordt als statische pagina gepubliceerd via GitHub Pages vanuit de map `docs/`.

1. Clear All Outputs -> Run all in `notebook.ipynb`.
2. Run build script:

   ```sh
   uv run build.py
   ```

3. Commit && push `docs/`.

Het script zet de figuren als losse PNG's in `docs/assets/figures/` (`figure-1.png`, `figure-2.png`, …).
