"""The exported script has to run -- sweep section G.

Every other panel is checked by comparing a number against an independently
computed one. Report can be held to something stricter: it hands the student a
Python script and a Jupyter notebook and says *this is what the tool did*. So
run them and see.

Doing that found the seam nobody had crossed. The loaders name the frame after
its source -- `tips = pd.read_csv(...)` -- because Data > Combine refers to
datasets by name when it merges them. Every other panel emits `df`. Nothing
joined the two, so every exported script died on its second statement with
`NameError: name 'df' is not defined`, and the bundled-dataset line was wrong
twice over: `pd.read_csv("tips.csv")` looks for a file that ships inside the
package and is not on disk where the student runs it.

A second gap sat behind that one: recording starts when the student presses the
button, necessarily after the data is loaded, so the load is almost never one of
the procedure's steps.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from pyanalytica.analyze.means import two_sample_ttest
from pyanalytica.core.codegen import CodeGenerator
from pyanalytica.core.procedure import ProcedureRecorder
from pyanalytica.data.load import load_bundled
from pyanalytica.data.transform import add_column_binned, add_column_conditional
from pyanalytica.explore.summarize import group_summarize
from pyanalytica.report.export import export_python_script


#: A student runs the exported script against an installed pyanalytica. From a
#: source checkout there is nothing installed -- the parent process only finds
#: the package through `pythonpath` in pyproject, which a subprocess does not
#: inherit. Hand the child the same path so the test measures the script, not
#: how the person running it happens to have set their environment up.
_SRC = str(pathlib.Path(__file__).resolve().parents[2] / "src")


def _run(path) -> subprocess.CompletedProcess:
    """Run a script the way a student would: their own interpreter, their cwd."""
    existing = os.environ.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, str(path)],
        capture_output=True,
        text=True,
        cwd=path.parent,
        timeout=300,
        env=dict(
            os.environ,
            MPLBACKEND="Agg",
            PYTHONPATH=os.pathsep.join(p for p in (_SRC, existing) if p),
        ),
    )


@pytest.fixture
def session():
    """A session in the app's own order: load, then start recording, then work."""
    df, load_snippet = load_bundled("tips")
    codegen = CodeGenerator()
    recorder = ProcedureRecorder()
    codegen.set_on_record(
        lambda snippet, *, action=None, description=None: recorder.record_step(
            action or "step", description or "step", snippet, dataset="tips"
        )
    )
    codegen.record(load_snippet, action="data", description="Load tips")
    recorder.start_recording()
    for snippet, description in [
        (add_column_binned(df, "band", "total_bill", 4)[1], "Bin the bill"),
        (add_column_conditional(df, "big_tip", "tip > 3", 1, 0)[1], "Flag big tips"),
        (group_summarize(df, ["day"], ["total_bill"], ["mean", "count"])[1], "By day"),
        (two_sample_ttest(df, "total_bill", "sex").code, "t-test of bill by sex"),
    ]:
        codegen.record(snippet, action="analysis", description=description)
    return codegen, recorder


# ------------------------------------------------------------- the load line


def test_the_bundled_load_line_actually_loads(tmp_path):
    _, snippet = load_bundled("tips")
    script = tmp_path / "load.py"
    script.write_text(
        "import pandas as pd\n" + snippet.code + "\nprint(len(df), len(tips))\n",
        encoding="utf-8",
    )
    result = _run(script)
    assert result.returncode == 0, result.stderr[-400:]
    assert result.stdout.strip() == "244 244"


def test_the_bundled_load_line_does_not_point_at_a_file_that_is_not_there():
    _, snippet = load_bundled("tips")
    assert 'pd.read_csv("tips.csv")' not in snippet.code


def test_every_loader_names_the_frame_df():
    """The panels all say df; the loaders must leave a df to say it about."""
    _, snippet = load_bundled("tips")
    assert "df = " in snippet.code
    assert "tips = " in snippet.code, "the named form is what Combine refers to"


# -------------------------------------------------------- the whole exports


def test_the_session_script_runs(session, tmp_path):
    codegen, _ = session
    script = tmp_path / "session.py"
    script.write_text(export_python_script(codegen), encoding="utf-8")
    result = _run(script)
    assert result.returncode == 0, (
        "the script the tool hands the student does not run:\n" + result.stderr[-800:]
    )


def test_the_procedure_script_runs(session, tmp_path):
    _, recorder = session
    procedure = recorder.build_procedure(name="Tips walkthrough")
    script = tmp_path / "procedure.py"
    script.write_text(ProcedureRecorder.export_python(procedure), encoding="utf-8")
    result = _run(script)
    assert result.returncode == 0, (
        "the exported procedure does not run:\n" + result.stderr[-800:]
    )


def test_the_procedure_script_says_where_the_data_came_from(session):
    _, recorder = session
    procedure = recorder.build_procedure(name="Tips walkthrough")
    script = ProcedureRecorder.export_python(procedure)
    assert "Recording started after the dataset was loaded" in script
    assert 'load_dataset("tips")' in script


def test_a_procedure_that_records_its_own_load_gets_no_preamble():
    """Do not add a second load on top of one the steps already have."""
    df, load_snippet = load_bundled("tips")
    recorder = ProcedureRecorder()
    recorder.start_recording()
    recorder.record_step("data", "Load tips", load_snippet, dataset="tips")
    recorder.record_step(
        "transform", "Bin", add_column_binned(df, "band", "total_bill", 4)[1],
        dataset="tips",
    )
    script = ProcedureRecorder.export_python(recorder.build_procedure(name="p"))
    assert "Recording started after" not in script
    # Once, from the step itself -- the import line mentions it too.
    assert script.count('load_dataset("tips")') == 1


def test_an_uploaded_file_gets_a_read_csv_the_student_can_point_at():
    recorder = ProcedureRecorder()
    recorder.start_recording()
    from pyanalytica.core.codegen import CodeSnippet

    recorder.record_step(
        "transform", "Bin", CodeSnippet(code='df["x"] = df["y"] * 2'),
        dataset="bank_campaign",
    )
    script = ProcedureRecorder.export_python(recorder.build_procedure(name="p"))
    assert 'pd.read_csv("bank_campaign.csv")' in script
    assert "Point it at your file" in script


# ------------------------------------------------------------ the notebook


def test_the_exported_notebook_is_valid_and_carries_the_load(session):
    _, recorder = session
    procedure = recorder.build_procedure(name="Tips walkthrough")
    text = ProcedureRecorder.export_jupyter(procedure)
    notebook = json.loads(text)
    assert notebook["nbformat"] == 4
    sources = "".join("".join(cell["source"]) for cell in notebook["cells"])
    assert 'load_dataset("tips")' in sources, "the notebook has no data to work on"


def test_the_notebook_cells_run_in_order(session, tmp_path):
    """Concatenating the code cells is what "Run All" amounts to."""
    _, recorder = session
    procedure = recorder.build_procedure(name="Tips walkthrough")
    notebook = json.loads(ProcedureRecorder.export_jupyter(procedure))
    code = "\n".join(
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
    script = tmp_path / "from_notebook.py"
    script.write_text(code, encoding="utf-8")
    result = _run(script)
    assert result.returncode == 0, result.stderr[-800:]
