"""Procedure builder — record, save, replay analytics workflows."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime

from pyanalytica.core.codegen import CodeSnippet


@dataclass
class ProcedureStep:
    """A single step in a recorded procedure."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    order: int = 0
    action: str = ""  # "load", "transform", "merge", "visualize", etc.
    description: str = ""  # Auto-generated human-readable comment
    code: str = ""  # The pandas/sklearn code for this step
    imports: list[str] = field(default_factory=list)
    enabled: bool = True
    user_comment: str = ""
    dataset: str = ""  # Which dataset this step operates on
    # When the step ran. Recorded because a homework submission carries the
    # procedure as evidence of the work, and "in what order, how far apart"
    # is part of what makes it evidence.
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


@dataclass
class Procedure:
    """A named, reusable analytics workflow."""
    name: str = ""
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    steps: list[ProcedureStep] = field(default_factory=list)
    version: int = 1


def _defines_the_frame(steps) -> bool:
    """Does any enabled step assign df, so the script can stand on its own?"""
    for step in steps:
        if not step.enabled:
            continue
        for line in step.code.splitlines():
            stripped = line.strip()
            if stripped.startswith("df ") and "=" in stripped.split("df ", 1)[1][:3]:
                return True
            if stripped.startswith("df="):
                return True
    return False


def _load_preamble(procedure) -> str:
    """A line to load the data, for a procedure that does not include one.

    Recording is off until the student turns it on, and they cannot analyse
    anything before loading, so the load is almost never one of the steps. The
    exported script then opens by indexing a dataset it never read.
    """
    dataset = next((s.dataset for s in procedure.steps if s.dataset), "")

    bundled: set[str] = set()
    try:
        from pyanalytica.datasets import list_datasets

        bundled = set(list_datasets())
    except Exception:  # the dataset list is not essential to exporting
        pass

    note = (
        "# Recording started after the dataset was loaded, so loading it is not\n"
        "# one of the steps below. This line puts it back."
    )
    if dataset and dataset in bundled:
        return (
            note
            + "\nfrom pyanalytica.datasets import load_dataset"
            + f'\ndf = load_dataset("{dataset}")\n'
        )

    name = dataset or "your_data"
    if not name.endswith((".csv", ".xlsx", ".xls")):
        name = name + ".csv"
    reader = "pd.read_excel" if name.endswith((".xlsx", ".xls")) else "pd.read_csv"
    return note + " Point it at your file." + f'\ndf = {reader}("{name}")\n'


class ProcedureRecorder:
    """Records analytics steps and builds reusable procedures."""

    def __init__(self) -> None:
        self._steps: list[ProcedureStep] = []
        self._recording: bool = False

    def start_recording(self) -> None:
        self._recording = True

    def stop_recording(self) -> None:
        self._recording = False

    def is_recording(self) -> bool:
        return self._recording

    def record_step(self, action: str, description: str, code_snippet: CodeSnippet,
                    dataset: str = "") -> ProcedureStep | None:
        """Record a step if recording is active. Returns the step or None."""
        if not self._recording:
            return None
        step = ProcedureStep(
            order=len(self._steps) + 1,
            action=action,
            description=description,
            code=code_snippet.code,
            imports=list(code_snippet.imports),
            dataset=dataset,
        )
        self._steps.append(step)
        return step

    def get_steps(self) -> list[ProcedureStep]:
        return list(self._steps)

    def clear(self) -> None:
        self._steps = []

    def remove_step(self, step_id: str) -> None:
        self._steps = [s for s in self._steps if s.id != step_id]
        self._renumber()

    def reorder_step(self, step_id: str, new_order: int) -> None:
        """Move a step to a new position (1-based)."""
        step = None
        for s in self._steps:
            if s.id == step_id:
                step = s
                break
        if step is None:
            return
        self._steps.remove(step)
        idx = max(0, min(new_order - 1, len(self._steps)))
        self._steps.insert(idx, step)
        self._renumber()

    def toggle_step(self, step_id: str) -> None:
        for s in self._steps:
            if s.id == step_id:
                s.enabled = not s.enabled
                break

    def set_comment(self, step_id: str, comment: str) -> None:
        for s in self._steps:
            if s.id == step_id:
                s.user_comment = comment
                break

    def _renumber(self) -> None:
        for i, s in enumerate(self._steps):
            s.order = i + 1

    def build_procedure(self, name: str, description: str = "") -> Procedure:
        """Build a Procedure from the currently recorded steps."""
        return Procedure(
            name=name,
            description=description,
            steps=list(self._steps),
        )

    @staticmethod
    def export_json(procedure: Procedure) -> str:
        """Export a procedure as a JSON string."""
        data = {
            "name": procedure.name,
            "description": procedure.description,
            "created_at": procedure.created_at,
            "version": procedure.version,
            "steps": [
                {
                    "id": s.id,
                    "order": s.order,
                    "action": s.action,
                    "description": s.description,
                    "code": s.code,
                    "imports": s.imports,
                    "enabled": s.enabled,
                    "user_comment": s.user_comment,
                    "dataset": s.dataset,
                }
                for s in procedure.steps
            ],
        }
        return json.dumps(data, indent=2)

    @staticmethod
    def import_json(json_str: str) -> Procedure:
        """Import a procedure from a JSON string."""
        data = json.loads(json_str)
        steps = []
        for s in data.get("steps", []):
            steps.append(ProcedureStep(
                id=s.get("id", str(uuid.uuid4())[:8]),
                order=s.get("order", 0),
                action=s.get("action", ""),
                description=s.get("description", ""),
                code=s.get("code", ""),
                imports=s.get("imports", []),
                enabled=s.get("enabled", True),
                user_comment=s.get("user_comment", ""),
                dataset=s.get("dataset", ""),
                timestamp=s.get("timestamp", ""),
            ))
        return Procedure(
            name=data.get("name", ""),
            description=data.get("description", ""),
            created_at=data.get("created_at", ""),
            version=data.get("version", 1),
            steps=steps,
        )

    @staticmethod
    def export_python(procedure: Procedure) -> str:
        """Export a procedure as a runnable Python script."""
        all_imports: set[str] = {"import pandas as pd"}
        code_blocks: list[str] = []
        current_dataset = ""

        for step in procedure.steps:
            if not step.enabled:
                continue
            for imp in step.imports:
                all_imports.add(imp)
            # Add dataset header when dataset changes between steps
            lines = []
            if step.dataset and step.dataset != current_dataset:
                lines.append(f"# --- Dataset: {step.dataset} ---")
                current_dataset = step.dataset
            comment = f"# Step {step.order}: {step.description}"
            if step.user_comment:
                comment += f"\n# Note: {step.user_comment}"
            lines.append(f"{comment}\n{step.code}")
            code_blocks.append("\n".join(lines))

        if not _defines_the_frame(procedure.steps):
            code_blocks.insert(0, _load_preamble(procedure))

        header = sorted(all_imports)
        script = (
            f'"""Procedure: {procedure.name}\n'
            f'\n'
            f'{procedure.description}\n'
            f'\n'
            f'Generated by PyAnalytica on {procedure.created_at}\n'
            f'"""\n\n'
        )
        script += "\n".join(header) + "\n\n"
        script += "\n\n".join(code_blocks) + "\n"
        return script

    @staticmethod
    def export_jupyter(procedure: Procedure) -> str:
        """Export a procedure as a Jupyter notebook JSON string."""
        cells = []

        # Title cell
        cells.append({
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                f"# {procedure.name}\n",
                f"\n",
                f"{procedure.description}\n",
                f"\n",
                f"*Generated by PyAnalytica on {procedure.created_at}*\n",
            ],
        })

        # Import cell
        all_imports: set[str] = {"import pandas as pd"}
        for step in procedure.steps:
            if step.enabled:
                for imp in step.imports:
                    all_imports.add(imp)

        cells.append({
            "cell_type": "code",
            "metadata": {},
            "source": [line + "\n" for line in sorted(all_imports)],
            "execution_count": None,
            "outputs": [],
        })

        # The notebook has the same gap the script had: recording begins after
        # the data is loaded, so the first step would run against a name that
        # was never defined.
        if not _defines_the_frame(procedure.steps):
            cells.append({
                "cell_type": "code",
                "metadata": {},
                "source": [
                    line + "\n"
                    for line in _load_preamble(procedure).rstrip().splitlines()
                ],
                "execution_count": None,
                "outputs": [],
            })

        # Step cells
        current_dataset = ""
        for step in procedure.steps:
            if not step.enabled:
                continue
            # Dataset header when dataset changes
            if step.dataset and step.dataset != current_dataset:
                cells.append({
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": [f"---\n", f"### Dataset: {step.dataset}\n"],
                })
                current_dataset = step.dataset
            # Markdown description
            desc = f"## Step {step.order}: {step.description}"
            if step.user_comment:
                desc += f"\n\n*{step.user_comment}*"
            cells.append({
                "cell_type": "markdown",
                "metadata": {},
                "source": [desc + "\n"],
            })
            # Code cell
            cells.append({
                "cell_type": "code",
                "metadata": {},
                "source": [line + "\n" for line in step.code.split("\n")],
                "execution_count": None,
                "outputs": [],
            })

        notebook = {
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {"name": "python", "version": "3.11.0"},
            },
            "cells": cells,
        }
        return json.dumps(notebook, indent=1)
