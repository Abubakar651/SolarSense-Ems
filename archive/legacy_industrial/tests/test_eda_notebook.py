"""
Smoke Test for the Industrial Load & MDI EDA Notebook
=====================================================
Executes every code cell of notebooks/01_industrial_load_eda.ipynb in order (headless
Agg backend), so the notebook's own assertions re-check the 169 grid-connected breaches,
outage MDI immunity and the 2,360,353.20 PKR baseline on every test run.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import nbformat
import pytest

NOTEBOOK_PATH = Path(__file__).resolve().parent.parent / "notebooks" / "01_industrial_load_eda.ipynb"


def test_eda_notebook_executes_and_exports_figure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """All cells run without error and the combined MDI figure is exported."""
    saved: list[Path] = []

    def fake_savefig(fname, *args, **kwargs):
        # Redirect the docs/samples export so test runs never overwrite the committed PNG
        target = tmp_path / Path(fname).name
        saved.append(target)
        plt.gcf().savefig(target, *args, **kwargs)

    plt.switch_backend("Agg")
    monkeypatch.setattr(plt, "savefig", fake_savefig)
    monkeypatch.setattr(plt, "show", lambda *args, **kwargs: plt.close("all"))
    monkeypatch.chdir(NOTEBOOK_PATH.parent)

    notebook = nbformat.read(NOTEBOOK_PATH, as_version=4)
    namespace: dict = {"__name__": "__main__"}
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type == "code":
            exec(compile(cell.source, f"{NOTEBOOK_PATH.name}[cell {index}]", "exec"), namespace)

    assert [p.name for p in saved] == ["load_and_mdi_spikes.png"]
    assert saved[0].stat().st_size > 0
