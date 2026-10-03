"""Every panel's code panel carries Add to Report, and names what it needs."""

import ast
from pathlib import Path

from pyanalytica.ui.components.code_panel import infer_imports

MODULES = Path(__file__).resolve().parents[2] / "src" / "pyanalytica" / "ui" / "modules"


def test_infer_imports_reads_the_prefixes_used():
    code = 'fig, ax = plt.subplots()\nsns.histplot(df["x"], ax=ax)\nresult = pd.DataFrame()'
    assert infer_imports(code) == [
        "import pandas as pd", "import matplotlib.pyplot as plt", "import seaborn as sns",
    ]
    assert infer_imports("x = 1") == []
    assert infer_imports('r, p = stats.pearsonr(df["a"], df["b"])') == ["from scipy import stats"]


def test_every_panel_with_a_code_panel_wires_the_report():
    """A code panel without state renders a button that can only apologise."""
    bare = []
    for path in sorted(MODULES.rglob("mod_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name != "code_panel_server":
                continue
            keywords = {k.arg for k in node.keywords}
            if "state" not in keywords:
                bare.append(f"{path.name}:{node.lineno}")
    assert not bare, (
        "these code panels show Add to Report but were not given the state to "
        "add to:\n  " + "\n  ".join(bare)
    )
