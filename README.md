# Short-form video's en werkgeheugen

Analyse van de relatie tussen dagelijks gebruik van short-form video's en werkgeheugenprestatie (2-back-taak) bij studenten. De analyse staat in `notebook.ipynb`.

## Website bouwen

De notebook wordt als statische pagina gepubliceerd via GitHub Pages vanuit de map `docs/`.

1. Draai alle cellen in `notebook.ipynb` en sla de notebook op (het script voert de notebook niet zelf uit).
2. Bouw de site:

   ```sh
   uv run build.py
   ```

3. Commit en push `docs/`.

Het script zet de figuren als losse PNG's in `docs/assets/figures/` (`figure-1.png`, `figure-2.png`, …), zodat je ze ook in het paper kunt gebruiken. Geef een figuur een vaste naam met een cell tag `fig:<naam>`, bijvoorbeeld `fig:scatter-accuracy`.
