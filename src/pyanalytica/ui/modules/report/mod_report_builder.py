"""Report > Report Builder — notebook-style editor with code + markdown cells."""

from __future__ import annotations

import json

from pyanalytica.ui.components.status import status_server, status_ui

from shiny import module, reactive, render, req, ui

from pyanalytica.core.report_builder import CellType
from pyanalytica.core.state import WorkbenchState
from pyanalytica.report.export import export_report_html, export_report_jupyter
from pyanalytica.ui.components.downloads import render_download
from pyanalytica.ui.components.requirements import NO_DATASET, require


# Action badge colours (same palette as mod_procedure)
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
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _badge_html(label: str, bg: str, fg: str) -> str:
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;'
        f'font-size:0.75rem;font-weight:600;text-transform:uppercase;'
        f'background:{bg};color:{fg};">{_esc(label)}</span>'
    )


def _code_block_html(code: str, imports: list[str]) -> str:
    lines: list[str] = []
    if imports:
        for imp in sorted(set(imports)):
            lines.append(imp)
        lines.append("")
    lines.extend(code.split("\n"))
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


def _insert_button_html(after_id: str, cmd_id: str) -> str:
    js = (
        f"Shiny.setInputValue('{cmd_id}', "
        f"'insert_after:{after_id}:' + Date.now())"
    )
    return (
        f'<div style="text-align:center;margin:2px 0;">'
        f'<button type="button" title="Insert text cell here" onclick="{js}" '
        f'style="width:26px;height:26px;border-radius:50%;border:1px dashed #bdbdbd;'
        f'background:transparent;color:#9e9e9e;font-size:1rem;cursor:pointer;'
        f'line-height:24px;padding:0;transition:all 0.15s ease;" '
        f'onmouseover="this.style.borderColor=\'#1976d2\';this.style.color=\'#1976d2\';this.style.background=\'#e3f2fd\'" '
        f'onmouseout="this.style.borderColor=\'#bdbdbd\';this.style.color=\'#9e9e9e\';this.style.background=\'transparent\'"'
        f'>+</button></div>'
    )


def _cell_card_html(c, cmd_id: str, md_update_id: str, total: int) -> str:
    enabled = c.enabled
    opacity = "1" if enabled else "0.5"
    border_color = "#4CAF50" if enabled else "#bdbdbd"

    def _btn(label: str, action: str, color: str, title: str) -> str:
        js = (
            f"Shiny.setInputValue('{cmd_id}', "
            f"'{action}:{c.id}:' + Date.now())"
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
    if c.order > 1:
        btns.append(_btn("&#9650;", "up", "#757575", "Move up"))
    if c.order < total:
        btns.append(_btn("&#9660;", "down", "#757575", "Move down"))
    btns.append(_btn(toggle_lbl, "toggle", toggle_clr, f"{toggle_lbl} this cell"))
    btns.append(_btn("&#10005;", "delete", "#e53935", "Delete cell"))
    btn_row = " ".join(btns)

    if c.cell_type == CellType.MARKDOWN:
        type_badge = _badge_html("MARKDOWN", "#e8f5e9", "#2e7d32")
        js_md = (
            f"Shiny.setInputValue('{md_update_id}', "
            f"JSON.stringify({{id:'{c.id}', markdown:this.value}}))"
        )
        content = (
            f'<textarea rows="4" '
            f'placeholder="Enter markdown text..." '
            f'onchange="{js_md}" '
            f'style="width:100%;border:1px solid #e0e0e0;border-radius:4px;padding:8px;'
            f'font-size:0.85rem;font-family:monospace;resize:vertical;outline:none;'
            f'margin-top:6px;" '
            f'onfocus="this.style.borderColor=\'#90caf9\'" '
            f'onblur="this.style.borderColor=\'#e0e0e0\'"'
            f'>{_esc(c.markdown)}</textarea>'
        )
    else:
        bg, fg = _ACTION_COLORS.get(c.action, _DEFAULT_COLOR)
        type_badge = _badge_html("CODE", "#e3f2fd", "#1565c0")
        action_badge = _badge_html(c.action, bg, fg)
        desc_style = "font-size:0.9rem;margin:4px 0 2px 0;"
        if not enabled:
            desc_style += "text-decoration:line-through;color:#999;"
        content = (
            f'{action_badge}'
            f'<p style="{desc_style}">{_esc(c.description)}</p>'
            f'{_code_block_html(c.code, c.imports)}'
        )
        # Append execution output if present
        if c.output_html:
            content += (
                f'<div style="border-top:1px solid #e0e0e0;margin-top:6px;padding-top:6px;">'
                f'<span style="font-size:0.72rem;color:#888;text-transform:uppercase;'
                f'letter-spacing:0.04em;">Output</span>'
                f'{c.output_html}'
                f'</div>'
            )

    return (
        f'<div style="border:1px solid #e0e0e0;border-left:4px solid {border_color};'
        f'border-radius:6px;padding:10px 14px;margin-bottom:4px;'
        f'background:#fff;opacity:{opacity};transition:opacity 0.2s ease;'
        f'box-shadow:0 1px 3px rgba(0,0,0,0.06);">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:4px;">'
        f'<div>{type_badge}'
        f'<span style="font-weight:600;margin-left:8px;">Cell {c.order}</span></div>'
        f'<div>{btn_row}</div>'
        f'</div>'
        f'{content}'
        f'</div>'
    )


@module.ui
def report_builder_ui():
    return ui.div(
        # --- Top toolbar: two compact rows ---
        ui.div(
            ui.row(
                ui.column(3, ui.input_text("rpt_title", None, value="PyAnalytica Report", placeholder="Report Title")),
                ui.column(2, ui.input_text("rpt_author", None, placeholder="Author")),
                ui.column(
                    7,
                    ui.div(
                        ui.input_action_button("import_proc", "Import from Procedure", class_="btn-primary btn-sm"),
                        ui.input_action_button("run_all", "Run All Cells", class_="btn-success btn-sm"),
                        ui.input_action_button("add_title_cell", "Add Title", class_="btn-outline-secondary btn-sm"),
                        ui.input_action_button("add_text_cell", "Add Text", class_="btn-outline-secondary btn-sm"),
                        ui.input_action_button("clear_report", "Clear", class_="btn-outline-danger btn-sm"),
                        class_="d-flex align-items-center gap-2 flex-wrap mt-1",
                    ),
                ),
            ),
            ui.row(
                ui.column(
                    12,
                    ui.div(
                        ui.input_switch("show_code", "Show Code", value=True),
                        ui.input_action_button("preview_btn", "Preview", class_="btn-info btn-sm"),
                        ui.download_button("dl_html", "HTML", class_="btn-outline-secondary btn-sm"),
                        ui.download_button("dl_jupyter", "Jupyter", class_="btn-outline-secondary btn-sm"),
                        ui.download_button("dl_json", "JSON", class_="btn-outline-secondary btn-sm"),
                        ui.input_file("import_json", None, accept=[".json"], button_label="Load Report"),
                        class_="d-flex align-items-center gap-2 flex-wrap mt-1",
                    ),
                ),
            ),
            class_="border-bottom pb-2 mb-2",
        ),
        # Under the toolbar, above the cells: this panel has no sidebar, and a
        # message about a build belongs next to what was built.
        status_ui("status"),
        # --- Cell editor (full width, no tabs) ---
        ui.div(
            ui.output_ui("cell_editor"),
            style="max-height:78vh;overflow-y:auto;padding-top:8px;",
        ),
    )


@module.server
def report_builder_server(input, output, session, state: WorkbenchState, get_current_df):
    builder = state.report_builder
    refresh = reactive.value(0)
    status = status_server("status")

    # Wire up reactive signal so external "Add to Report" additions trigger refresh
    state._report_change_signal = reactive.value(0)

    cell_cmd_id = session.ns("_cell_cmd")
    md_update_id = session.ns("_md_update")

    def _bump():
        refresh.set(refresh() + 1)

    # Watch for external additions (from "Add to Report" in other modules)
    @reactive.effect
    def _watch_external():
        sig = state._report_change_signal()
        if sig > 0:
            _bump()

    # --- Sync title/author ---
    @reactive.effect
    @reactive.event(input.rpt_title)
    def _sync_title():
        builder.title = input.rpt_title().strip() or "PyAnalytica Report"

    @reactive.effect
    @reactive.event(input.rpt_author)
    def _sync_author():
        builder.author = input.rpt_author().strip()

    # --- Import from Procedure ---
    @reactive.effect
    @reactive.event(input.import_proc)
    def _import_proc():
        recorder = state.procedure_recorder
        steps = recorder.get_steps()
        if not steps:
            status.check("No procedure steps to import. Record some steps first.")
            return
        count = builder.import_from_recorder(recorder)
        status.done(f"Imported {count} code cells from procedure.")
        _bump()

    # --- Run All Cells ---
    @reactive.effect
    @reactive.event(input.run_all)
    def _run_all():
        if builder.cell_count() == 0:
            status.check("No cells to run.")
            return
        df = get_current_df()
        messages = builder.execute_all(df)
        ok = sum(1 for m in messages if "OK" in m)
        err = sum(1 for m in messages if "Error" in m)
        summary = f"Executed {ok + err} cells: {ok} OK"
        if err:
            summary += f", {err} errors"
        if err:
            status.check(summary)
        else:
            status.done(summary)
        _bump()

    # --- Add cells ---
    @reactive.effect
    @reactive.event(input.add_title_cell)
    def _add_title():
        builder.add_title_cell()
        _bump()

    @reactive.effect
    @reactive.event(input.add_text_cell)
    def _add_text():
        builder.add_markdown_cell(markdown="Enter your text here...")
        _bump()

    # --- Clear ---
    @reactive.effect
    @reactive.event(input.clear_report)
    def _clear():
        builder.clear()
        _bump()

    # --- Cell commands (delete/toggle/up/down/insert_after) ---
    @reactive.effect
    @reactive.event(input._cell_cmd)
    def _handle_cell_cmd():
        cmd = input._cell_cmd()
        if not cmd:
            return
        parts = cmd.split(":")
        if len(parts) < 2:
            return
        action, cell_id = parts[0], parts[1]
        if action == "delete":
            builder.remove_cell(cell_id)
        elif action == "toggle":
            builder.toggle_cell(cell_id)
        elif action == "up":
            builder.move_cell(cell_id, "up")
        elif action == "down":
            builder.move_cell(cell_id, "down")
        elif action == "insert_after":
            if cell_id == "__top__":
                cell = builder.add_markdown_cell(markdown="")
                while True:
                    idx = builder._find_index(cell.id)
                    if idx is None or idx == 0:
                        break
                    builder.move_cell(cell.id, "up")
            else:
                builder.add_markdown_cell(after_cell_id=cell_id, markdown="")
        _bump()

    # --- Markdown update ---
    @reactive.effect
    @reactive.event(input._md_update)
    def _handle_md_update():
        raw = input._md_update()
        if not raw:
            return
        try:
            data = json.loads(raw)
            builder.update_markdown(data["id"], data["markdown"])
        except (json.JSONDecodeError, KeyError):
            pass

    # --- Preview in modal ---
    @reactive.effect
    @reactive.event(input.preview_btn)
    def _show_preview():
        if builder.cell_count() == 0:
            status.check("No cells to preview.")
            return
        builder.title = input.rpt_title().strip() or "PyAnalytica Report"
        builder.author = input.rpt_author().strip()
        builder.execute_all(get_current_df())
        html_content = export_report_html(builder, show_code=input.show_code())
        escaped_html = html_content.replace("&", "&amp;").replace('"', "&quot;")
        iframe = (
            f'<iframe srcdoc="{escaped_html}" '
            f'style="width:100%;height:80vh;border:none;background:#fff;"></iframe>'
        )
        m = ui.modal(
            ui.HTML(iframe),
            title="Report Preview",
            size="xl",
            easy_close=True,
            footer=ui.modal_button("Close"),
        )
        ui.modal_show(m)

    # --- Import JSON ---
    @reactive.effect
    @reactive.event(input.import_json)
    def _import_json():
        file_info = input.import_json()
        if not require(file_info, "Choose a report file to import first."):
            return
        try:
            path = file_info[0]["datapath"]
            with open(path, "r", encoding="utf-8") as f:
                json_str = f.read()
            builder.import_json(json_str)
            ui.update_text("rpt_title", value=builder.title)
            ui.update_text("rpt_author", value=builder.author)
            status.done(
                f"Loaded report '{builder.title}' ({builder.cell_count()} cells)."
            )
            _bump()
        except Exception as e:
            status.failed(str(e))

    # --- Cell Editor ---
    @render.ui
    def cell_editor():
        refresh()
        # Also react to external "Add to Report" additions
        if state._report_change_signal is not None:
            state._report_change_signal()
        cells = builder.get_cells()
        if not cells:
            return ui.div(
                ui.p("No cells yet.", class_="text-muted"),
                ui.p(
                    "Import steps from the Procedure tab or add text cells manually.",
                    class_="text-muted small",
                ),
                class_="text-center py-4",
            )

        total = len(cells)
        parts: list[ui.TagChild] = []
        parts.append(ui.HTML(_insert_button_html("__top__", cell_cmd_id)))
        for c in cells:
            parts.append(ui.HTML(_cell_card_html(c, cell_cmd_id, md_update_id, total)))
            parts.append(ui.HTML(_insert_button_html(c.id, cell_cmd_id)))

        return ui.tags.div(
            ui.div(f"{total} cell{'s' if total != 1 else ''}", class_="text-muted small mb-2"),
            *parts,
        )

    # --- Downloads ---
    @render_download(filename="report.html")
    def dl_html():
        builder.title = input.rpt_title().strip() or "PyAnalytica Report"
        builder.author = input.rpt_author().strip()
        builder.execute_all(get_current_df())
        yield export_report_html(builder, show_code=input.show_code()).encode("utf-8")

    @render_download(filename="report.ipynb")
    def dl_jupyter():
        builder.title = input.rpt_title().strip() or "PyAnalytica Report"
        builder.author = input.rpt_author().strip()
        yield export_report_jupyter(builder).encode("utf-8")

    @render_download(filename="report.json")
    def dl_json():
        builder.title = input.rpt_title().strip() or "PyAnalytica Report"
        builder.author = input.rpt_author().strip()
        yield builder.export_json().encode("utf-8")
