"""Report > Procedure Builder — record, edit, export, and replay procedures."""

from __future__ import annotations

import json

from shiny import module, reactive, render, req, ui

from pyanalytica.core.procedure import ProcedureRecorder
from pyanalytica.core.state import WorkbenchState
from pyanalytica.ui.components.downloads import render_download
from pyanalytica.ui.components.requirements import NO_DATASET, require
from pyanalytica.ui.components.status import status_server, status_ui


# Action badge colours (same palette as mod_notebook)
_ACTION_COLORS: dict[str, tuple[str, str]] = {
    "load":      ("#e3f2fd", "#1565c0"),
    "transform": ("#fff3e0", "#e65100"),
    "visualize": ("#e8f5e9", "#2e7d32"),
    "analyze":   ("#f3e5f5", "#6a1b9a"),
    "model":     ("#ede7f6", "#4527a0"),
    "merge":     ("#e0f7fa", "#00695c"),
    "filter":    ("#fff9c4", "#f57f17"),
    "export":    ("#fce4ec", "#b71c1c"),
}
_DEFAULT_COLOR = ("#f5f5f5", "#424242")


def _esc(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _badge_html(action: str) -> str:
    bg, fg = _ACTION_COLORS.get(action, _DEFAULT_COLOR)
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;'
        f'font-size:0.75rem;font-weight:600;text-transform:uppercase;'
        f'background:{bg};color:{fg};">{_esc(action)}</span>'
    )


def _code_block_html(code: str, imports: list[str]) -> str:
    """Render a dark-themed code block with imports and line numbers."""
    lines: list[str] = []
    if imports:
        for imp in sorted(set(imports)):
            lines.append(imp)
        lines.append("")  # blank separator after imports
    lines.extend(code.split("\n"))
    # strip trailing empty lines
    while lines and not lines[-1].strip():
        lines.pop()

    rows = []
    for i, line in enumerate(lines, 1):
        num = (
            f'<span style="color:#6e7681;user-select:none;display:inline-block;'
            f'min-width:2em;text-align:right;padding-right:1em;">{i}</span>'
        )
        rows.append(f"{num}{_esc(line)}")
    inner = "\n".join(rows)
    return (
        f'<pre style="background:#1e1e1e;color:#d4d4d4;padding:0.6rem 0.8rem;'
        f'border-radius:4px;font-size:0.78rem;'
        f"font-family:'Consolas','Monaco','Courier New',monospace;"
        f'max-height:250px;overflow-y:auto;margin:6px 0 4px 0;'
        f'white-space:pre;line-height:1.5;">'
        f'{inner}</pre>'
    )


def _step_card_html(
    s, step_cmd_id: str, comment_update_id: str, total: int,
) -> str:
    """Build the full HTML for one procedure step card."""
    enabled = s.enabled
    opacity = "1" if enabled else "0.5"
    border_color = "#4CAF50" if enabled else "#bdbdbd"

    # --- Action buttons (JS -> hidden Shiny input) ---
    def _btn(label: str, action: str, color: str, title: str) -> str:
        js = (
            f"Shiny.setInputValue('{step_cmd_id}', "
            f"'{action}:{s.id}:' + Date.now())"
        )
        return (
            f'<button type="button" title="{_esc(title)}" onclick="{js}" '
            f'style="border:1px solid {color};background:transparent;color:{color};'
            f'border-radius:3px;padding:1px 7px;font-size:0.75rem;cursor:pointer;'
            f'margin-left:3px;transition:all 0.15s ease;" '
            f'onmouseover="this.style.background=\'{color}\';this.style.color=\'#fff\'" '
            f'onmouseout="this.style.background=\'transparent\';this.style.color=\'{color}\'"'
            f'>{label}</button>'
        )

    toggle_lbl = "Disable" if enabled else "Enable"
    toggle_clr = "#ff9800" if enabled else "#4CAF50"
    btns: list[str] = []
    if s.order > 1:
        btns.append(_btn("&#9650;", "up", "#757575", "Move up"))
    if s.order < total:
        btns.append(_btn("&#9660;", "down", "#757575", "Move down"))
    btns.append(_btn(toggle_lbl, "toggle", toggle_clr, f"{toggle_lbl} this step"))
    btns.append(_btn("&#10005;", "delete", "#e53935", "Delete step"))
    btn_row = " ".join(btns)

    # --- Description ---
    desc_style = "font-size:0.9rem;margin:4px 0 2px 0;"
    if not enabled:
        desc_style += "text-decoration:line-through;color:#999;"

    # --- Code block ---
    code_block = _code_block_html(s.code, s.imports)

    # --- Comment input (JS -> JSON -> server) ---
    js_comment = (
        f"Shiny.setInputValue('{comment_update_id}', "
        f"JSON.stringify({{id:'{s.id}', comment:this.value}}))"
    )
    comment_section = (
        f'<div style="margin-top:4px;display:flex;align-items:center;gap:6px;">'
        f'<span style="font-size:0.75rem;color:#888;white-space:nowrap;">Comment:</span>'
        f'<input type="text" value="{_esc(s.user_comment)}" '
        f'placeholder="Add a note..." '
        f'onchange="{js_comment}" '
        f'style="flex:1;border:1px solid #e0e0e0;border-radius:3px;padding:3px 8px;'
        f'font-size:0.8rem;outline:none;" '
        f'onfocus="this.style.borderColor=\'#90caf9\'" '
        f'onblur="this.style.borderColor=\'#e0e0e0\'"/>'
        f'</div>'
    )

    # Dataset tag
    dataset_tag = ""
    if s.dataset:
        dataset_tag = (
            f'<span style="display:inline-block;padding:1px 6px;border-radius:3px;'
            f'font-size:0.7rem;background:#e8eaf6;color:#283593;margin-left:6px;'
            f'font-weight:500;">{_esc(s.dataset)}</span>'
        )

    return (
        f'<div style="border:1px solid #e0e0e0;border-left:4px solid {border_color};'
        f'border-radius:6px;padding:10px 14px;margin-bottom:12px;'
        f'background:#fff;opacity:{opacity};transition:opacity 0.2s ease;'
        f'box-shadow:0 1px 3px rgba(0,0,0,0.06);">'
        # Header: badge + step number + dataset tag + action buttons
        f'<div style="display:flex;align-items:center;justify-content:space-between;">'
        f'<div>{_badge_html(s.action)}'
        f'<span style="font-weight:600;margin-left:8px;">Step {s.order}</span>'
        f'{dataset_tag}</div>'
        f'<div>{btn_row}</div>'
        f'</div>'
        # Description
        f'<p style="{desc_style}">{_esc(s.description)}</p>'
        # Code
        f'{code_block}'
        # Comment
        f'{comment_section}'
        f'</div>'
    )


@module.ui
def procedure_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.output_ui("record_toggle_ui"),
            ui.tags.hr(),
            ui.input_text("proc_name", "Procedure Name", placeholder="My Procedure"),
            ui.input_text_area(
                "proc_desc", "Description",
                placeholder="What this procedure does...", rows=2,
            ),
            ui.input_action_button(
                "save_proc", "Build Procedure", class_="btn-primary w-100 mt-2",
            ),
            ui.input_action_button(
                "clear_steps", "Clear Steps", class_="btn-outline-danger w-100 mt-1",
            ),
            ui.tags.script(ui.HTML("""
                $(document).on('click', '[id$="clear_steps"]', function(e) {
                    if (!confirm('Clear all recorded steps? This cannot be undone.')) {
                        e.preventDefault();
                        e.stopImmediatePropagation();
                    }
                });
            """)),
            ui.tags.hr(),
            ui.h6("Import / Export"),
            ui.input_file("import_file", "Load Procedure (JSON)", accept=[".json"]),
            ui.download_button(
                "export_json", "Download JSON",
                class_="btn-outline-secondary w-100 mt-1",
            ),
            ui.download_button(
                "export_python", "Download Python",
                class_="btn-outline-secondary w-100 mt-1",
            ),
            ui.download_button(
                "export_jupyter", "Download Jupyter",
                class_="btn-outline-secondary w-100 mt-1",
            ),
            width=300,
        ),
        # Above the output: a failure belongs where the result would be.
        status_ui("status"),
        ui.output_ui("recording_indicator"),
        ui.output_ui("step_list"),
    )


@module.server
def procedure_server(input, output, session, state: WorkbenchState, get_current_df):
    recorder = state.procedure_recorder
    refresh = reactive.value(0)
    status = status_server("status")
    built_procedure = reactive.value(None)

    # Fully-namespaced IDs for JavaScript Shiny.setInputValue() calls
    step_cmd_id = session.ns("_step_cmd")
    comment_update_id = session.ns("_comment_update")

    def _bump():
        refresh.set(refresh() + 1)

    # --- Record toggle ---
    @render.ui
    def record_toggle_ui():
        refresh()
        if recorder.is_recording():
            return ui.input_action_button(
                "toggle_record", "Stop Recording", class_="btn-danger w-100",
            )
        return ui.input_action_button(
            "toggle_record", "Start Recording", class_="btn-success w-100",
        )

    @reactive.effect
    @reactive.event(input.toggle_record)
    def _toggle():
        if recorder.is_recording():
            recorder.stop_recording()
        else:
            recorder.start_recording()
        _bump()

    # --- Clear ---
    @reactive.effect
    @reactive.event(input.clear_steps)
    def _clear():
        recorder.clear()
        built_procedure.set(None)
        _bump()

    # --- Build procedure ---
    @reactive.effect
    @reactive.event(input.save_proc)
    def _save():
        name = input.proc_name().strip() or "Untitled"
        desc = input.proc_desc().strip()
        proc = recorder.build_procedure(name, desc)
        built_procedure.set(proc)
        status.done(
            f"Procedure '{name}' built with {len(proc.steps)} steps."
        )

    # --- Import ---
    @reactive.effect
    @reactive.event(input.import_file)
    def _import():
        file_info = input.import_file()
        if not require(file_info, "Choose a procedure file to import first."):
            return
        try:
            path = file_info[0]["datapath"]
            with open(path, "r", encoding="utf-8") as f:
                json_str = f.read()
            proc = ProcedureRecorder.import_json(json_str)
            recorder.clear()
            recorder._steps = list(proc.steps)
            built_procedure.set(proc)
            status.done(f"Loaded '{proc.name}' ({len(proc.steps)} steps).")
            _bump()
        except Exception as e:
            status.failed(str(e))

    # --- Step action handler (delete / toggle / up / down) ---
    @reactive.effect
    @reactive.event(input._step_cmd)
    def _handle_step_cmd():
        cmd = input._step_cmd()
        if not cmd:
            return
        parts = cmd.split(":")
        if len(parts) < 2:
            return
        action, step_id = parts[0], parts[1]
        if action == "delete":
            recorder.remove_step(step_id)
        elif action == "toggle":
            recorder.toggle_step(step_id)
        elif action == "up":
            for s in recorder.get_steps():
                if s.id == step_id:
                    recorder.reorder_step(step_id, s.order - 1)
                    break
        elif action == "down":
            for s in recorder.get_steps():
                if s.id == step_id:
                    recorder.reorder_step(step_id, s.order + 1)
                    break
        _bump()

    # --- Comment update handler (JSON from JS) ---
    @reactive.effect
    @reactive.event(input._comment_update)
    def _handle_comment():
        raw = input._comment_update()
        if not raw:
            return
        try:
            data = json.loads(raw)
            recorder.set_comment(data["id"], data["comment"])
            _bump()
        except (json.JSONDecodeError, KeyError):
            pass

    # --- Recording indicator ---
    @render.ui
    def recording_indicator():
        refresh()
        if recorder.is_recording():
            return ui.div(
                ui.tags.span(
                    style=(
                        "display:inline-block;width:10px;height:10px;border-radius:50%;"
                        "background:red;margin-right:6px;"
                        "animation:blink-dot 1.5s infinite;"
                    ),
                ),
                "Recording... ",
                ui.tags.small(
                    "(actions you perform will be captured as steps)",
                    class_="text-muted",
                ),
                ui.tags.style(
                    "@keyframes blink-dot {0%,100%{opacity:1}50%{opacity:0.3}}"
                ),
                class_="alert alert-danger d-flex align-items-center py-2 mb-3",
            )
        n = len(recorder.get_steps())
        if n > 0:
            return ui.div(
                f"{n} step{'s' if n != 1 else ''} recorded.",
                class_="alert alert-secondary py-2 mb-3",
            )
        return ui.div(
            "Start recording to capture your analytics workflow as a reusable procedure.",
            class_="text-muted mb-3",
        )

    # --- Step list ---
    @render.ui
    def step_list():
        refresh()
        if state._change_signal is not None:
            state._change_signal()
        steps = recorder.get_steps()
        if not steps:
            return ui.div(
                ui.p("No steps recorded yet.", class_="text-muted"),
                ui.p(
                    "Click 'Start Recording', then perform analytics operations. "
                    "Each operation will appear here as a replayable step.",
                    class_="text-muted small",
                ),
                class_="text-center py-4",
            )

        total = len(steps)
        cards = [
            ui.HTML(_step_card_html(s, step_cmd_id, comment_update_id, total))
            for s in steps
        ]
        return ui.tags.div(ui.h5(f"Procedure Steps ({total})"), *cards)

    # --- Export handlers ---
    @render_download(filename="procedure.json")
    def export_json():
        proc = built_procedure()
        if proc is None:
            proc = recorder.build_procedure(
                input.proc_name().strip() or "Untitled",
                input.proc_desc().strip(),
            )
        yield ProcedureRecorder.export_json(proc).encode("utf-8")

    @render_download(filename="procedure.py")
    def export_python():
        proc = built_procedure()
        if proc is None:
            proc = recorder.build_procedure(
                input.proc_name().strip() or "Untitled",
                input.proc_desc().strip(),
            )
        yield ProcedureRecorder.export_python(proc).encode("utf-8")

    @render_download(filename="procedure.ipynb")
    def export_jupyter():
        proc = built_procedure()
        if proc is None:
            proc = recorder.build_procedure(
                input.proc_name().strip() or "Untitled",
                input.proc_desc().strip(),
            )
        yield ProcedureRecorder.export_jupyter(proc).encode("utf-8")
