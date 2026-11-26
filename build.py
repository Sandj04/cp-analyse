# /// script
# requires-python = ">=3.10"
# dependencies = ["nbconvert>=7.16", "nbformat>=5.10", "ipython>=8"]
# ///
"""Build a static site from a notebook into docs/ (served by GitHub Pages).

    uv run build.py                 # notebook.ipynb -> docs/
    uv run build.py other.ipynb -o site

Output:
    docs/index.html           the notebook page
    docs/assets/jupyter.css   nbconvert's JupyterLab styles
    docs/assets/notebook.css  our styles (copied from style/notebook.css)
    docs/assets/figures/*.png every plot, as a separate file (usable in the paper)
    docs/assets/variables.tex LaTeX macros, written by the notebook (kept across builds)
    docs/.nojekyll            so GitHub Pages serves the files as-is

Links in the notebook that point into the output dir (e.g. `docs/assets/x`) are
rewritten relative to index.html, so they work both in Jupyter and on the site.

Figures are named figure-1.png, figure-2.png, ... in notebook order. To give a
figure a fixed name, add a cell tag `fig:<name>` (e.g. `fig:scatter-accuracy`).
The notebook is not executed: run all cells and save it before building.
"""

from __future__ import annotations

import argparse
import base64
import html
import re
import shutil
from pathlib import Path

import nbformat
from nbconvert import HTMLExporter

ROOT = Path(__file__).resolve().parent
STYLESHEET = ROOT / "style" / "notebook.css"
# Files the notebook writes into the output dir itself; kept when the dir is wiped.
KEEP = ["assets/variables.tex"]
IMAGE_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/svg+xml": ".svg"}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "figure"


def extract_figures(nb, fig_dir: Path) -> list[Path]:
    """Write image outputs to fig_dir and point the outputs at those files."""
    written: list[Path] = []
    counter = 0
    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        tag = next((t[4:] for t in cell.metadata.get("tags", []) if t.startswith("fig:")), None)
        in_cell = 0
        for output in cell.get("outputs", []):
            data = output.get("data", {})
            mime = next((m for m in IMAGE_TYPES if m in data), None)
            if mime is None:
                continue
            counter += 1
            in_cell += 1
            if tag:
                stem = slug(tag) + (f"-{in_cell}" if in_cell > 1 else "")
            else:
                stem = f"figure-{counter}"
            path = fig_dir / (stem + IMAGE_TYPES[mime])
            if path in written:
                raise SystemExit(f"Duplicate figure name: {path.name} (check your fig: tags)")
            payload = data[mime]
            if isinstance(payload, list):
                payload = "".join(payload)
            if mime == "image/svg+xml":
                path.write_text(payload, encoding="utf-8")
            else:
                path.write_bytes(base64.b64decode(payload))
            # The lab template uses metadata.filenames as <img src> instead of base64.
            output.setdefault("metadata", {}).setdefault("filenames", {})[mime] = (
                path.relative_to(fig_dir.parent.parent).as_posix()
            )
            written.append(path)
    return written


def notebook_title(nb, fallback: str) -> str:
    for cell in nb.cells:
        if cell.cell_type == "markdown":
            match = re.search(r"^#\s+(.+)$", cell.source, re.MULTILINE)
            if match:
                return match.group(1).strip()
    return fallback


def split_head_styles(page: str) -> tuple[str, str]:
    """Move the <style> blocks in <head> into one CSS string; return (page, css)."""
    head_end = page.index("</head>")
    head, rest = page[:head_end], page[head_end:]
    blocks = re.findall(r"<style[^>]*>(.*?)</style>", head, flags=re.DOTALL)
    head = re.sub(r"\s*<style[^>]*>.*?</style>", "", head, flags=re.DOTALL)
    links = (
        '\n<link rel="stylesheet" href="assets/jupyter.css"/>'
        '\n<link rel="stylesheet" href="assets/notebook.css"/>\n'
    )
    return head + links + rest, "\n\n".join(b.strip() for b in blocks) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("notebook", nargs="?", default="notebook.ipynb", type=Path)
    parser.add_argument("-o", "--out", default="docs", type=Path)
    args = parser.parse_args()

    nb_path: Path = args.notebook if args.notebook.is_absolute() else ROOT / args.notebook
    out: Path = args.out if args.out.is_absolute() else ROOT / args.out
    assets = out / "assets"
    fig_dir = assets / "figures"

    kept: dict[str, bytes] = {}
    if out.exists():
        # The output dir is wiped on every build; never wipe one we didn't create.
        if any(out.iterdir()) and not (out / ".nojekyll").exists():
            raise SystemExit(f"{out} exists and was not created by build.py; refusing to overwrite it")
        kept = {rel: (out / rel).read_bytes() for rel in KEEP if (out / rel).is_file()}
        shutil.rmtree(out)
    fig_dir.mkdir(parents=True)
    for rel, content in kept.items():
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_bytes(content)
    for rel in KEEP:
        if rel not in kept:
            print(f"  warning: {out.name}/{rel} not found (run the notebook first)")

    nb = nbformat.read(nb_path, as_version=4)
    figures = extract_figures(nb, fig_dir)
    title = notebook_title(nb, nb_path.stem)

    exporter = HTMLExporter(template_name="lab")
    exporter.exclude_input_prompt = True
    exporter.exclude_output_prompt = True
    page, _ = exporter.from_notebook_node(nb, resources={"metadata": {"name": title}})

    page, jupyter_css = split_head_styles(page)
    page = re.sub(
        r'<img alt="No description has been provided for this image"([^>]*src="assets/figures/([^"/]+)\.\w+")',
        lambda m: f'<img alt="{m.group(2)}"{m.group(1)}',
        page,
    )
    page = re.sub(r"<title>.*?</title>", f"<title>{html.escape(title)}</title>", page, count=1, flags=re.DOTALL)
    # `docs/assets/x` is right from the notebook's dir, but index.html lives inside docs/.
    if out.is_relative_to(nb_path.parent):
        prefix = re.escape(out.relative_to(nb_path.parent).as_posix() + "/")
        page = re.sub(rf'(href|src)="(?:\./)?{prefix}', r'\1="', page)

    (out / "index.html").write_text(page, encoding="utf-8")
    (assets / "jupyter.css").write_text(jupyter_css, encoding="utf-8")
    shutil.copyfile(STYLESHEET, assets / "notebook.css")
    (out / ".nojekyll").touch()

    print(f"Built {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}/index.html from {nb_path.name}")
    for fig in figures:
        print(f"  figure: {fig.relative_to(out)}")
    for rel in kept:
        print(f"  kept:   {rel}")


if __name__ == "__main__":
    main()
