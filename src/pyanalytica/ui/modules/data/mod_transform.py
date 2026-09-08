"""Data > Transform module — missing values, dtypes, duplicates, new columns, string ops."""

from __future__ import annotations

from shiny import module, reactive, render, req, ui

import pandas as pd

from pyanalytica.core import round_df
from pyanalytica.core.state import Operation, WorkbenchState
from pyanalytica.data import transform
from pyanalytica.ui.components.code_panel import code_panel_server, code_panel_ui
from pyanalytica.ui.components.decimals_control import decimals_server, decimals_ui
from pyanalytica.ui.components.requirements import NO_DATASET, require
from pyanalytica.ui.components.status import status_server, status_ui

from datetime import datetime


def _coerce_literal(text: str | None):
    """Read a typed value as a number when it looks like one, else as text.

    Lets "Add Conditional Column" produce a numeric 1/0 indicator rather than
    the strings "1"/"0", which would not average.
    """
    if text is None:
        return ""
    text = text.strip()
    for cast in (int, float):
        try:
            return cast(text)
        except (TypeError, ValueError):
            continue
    return text


@module.ui
def transform_ui():
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("action", "Transform Action", choices={
                "fill_missing": "Fill Missing Values",
                "drop_missing": "Drop Missing Rows",
                "rename_column": "Rename Column",
                "drop_columns": "Drop Column(s)",
                "convert_dtype": "Convert Data Type",
                "drop_duplicates": "Drop Duplicates",
                "dummy_encode": "Dummy Encode (One-Hot)",
                "ordinal_encode": "Ordinal Encode",
                "add_arithmetic": "Add Calculated Column",
                "add_conditional": "Add Conditional Column",
                "add_binned": "Add Binned Column",
                "add_log": "Add Log Column",
                "add_zscore": "Add Z-score Column",
                "add_rank": "Add Rank Column",
                "str_lower": "String: Lowercase",
                "str_upper": "String: Uppercase",
                "str_strip": "String: Strip Whitespace",
                "str_replace": "String: Replace",
                "str_extract": "String: Extract",
            }),
            ui.output_ui("action_controls"),
            ui.input_action_button("preview_btn", "Preview", class_="btn-outline-info w-100 mt-2"),
            ui.input_action_button("apply_btn", "Apply", class_="btn-primary w-100 mt-1"),
            width=300,
        ),
        # Above the output: a failure belongs where the result would be.
        status_ui("status"),
        ui.output_text("transform_info"),
        decimals_ui("dec"),
        ui.output_data_frame("preview"),
        code_panel_ui("code"),
    )


@module.server
def transform_server(input, output, session, state: WorkbenchState, get_current_df):
    last_code = reactive.value("")
    get_dec = decimals_server("dec")
    _prev_ds_id = reactive.value(None)
    _preview_result = reactive.value(None)  # (df, snippet) or None
    status = status_server("status")

    @reactive.effect
    def _track_dataset_change():
        """Force UI refresh when the active dataset changes."""
        df = get_current_df()
        new_id = id(df) if df is not None else None
        if new_id != _prev_ds_id():
            _prev_ds_id.set(new_id)
            _preview_result.set(None)

    def _prior(name: str, valid=None, default=None):
        """Value an input already holds, if it is still usable.

        ``action_controls`` re-renders whenever the active dataset changes, and
        applying a transform replaces the dataset. Without carrying the previous
        selection across, every Apply silently reset Column to the first column,
        so a second Apply would land on the wrong one.
        """
        with reactive.isolate():
            try:
                value = getattr(input, name)()
            except Exception:
                return default
        if value is None or value == "":
            return default
        if valid is not None and value not in valid:
            return default
        return value

    @render.ui
    def action_controls():
        _prev_ds_id()  # re-render when dataset changes
        df = get_current_df()
        cols = list(df.columns) if df is not None else []
        action = input.action()

        # For encoding actions, show only object/category columns
        if action in ("dummy_encode", "ordinal_encode") and df is not None:
            cat_cols = [c for c in cols if df[c].dtype == object
                        or isinstance(df[c].dtype, pd.CategoricalDtype)]
            col_choices = cat_cols if cat_cols else cols
        else:
            col_choices = cols

        if action == "drop_columns":
            kept = [c for c in (_prior("drop_cols") or ()) if c in cols]
            controls = [ui.input_selectize("drop_cols", "Columns to Drop",
                choices=cols, multiple=True, selected=kept or None)]
        else:
            controls = [ui.input_select("col", "Column", choices=col_choices,
                selected=_prior("col", valid=col_choices))]

        if action == "rename_column":
            controls.append(ui.input_text("new_col_name", "New Column Name",
                value=_prior("new_col_name", default="")))
        elif action == "fill_missing":
            controls.append(ui.input_select("fill_method", "Method",
                choices=["mean", "median", "mode", "ffill", "bfill", "value"],
                selected=_prior("fill_method",
                    valid=["mean", "median", "mode", "ffill", "bfill", "value"])))
            controls.append(ui.input_text("fill_value", "Value (if method=value)",
                value=_prior("fill_value", default="")))
        elif action == "convert_dtype":
            dtypes = ["int", "float", "str", "category", "datetime", "bool"]
            controls.append(ui.input_select("target_dtype", "Target Type",
                choices=dtypes, selected=_prior("target_dtype", valid=dtypes)))
        elif action in ("add_log", "add_zscore", "add_rank"):
            controls.append(ui.input_text("new_col_name", "New Column Name",
                value=_prior("new_col_name", default="")))
        elif action == "add_arithmetic":
            controls.append(ui.input_text("new_col_name", "New Column Name",
                value=_prior("new_col_name", default="")))
            controls.append(ui.input_text("expr", "Expression",
                value=_prior("expr", default=""),
                placeholder="e.g. salary / 12"))
        elif action == "add_conditional":
            controls.append(ui.input_text("new_col_name", "New Column Name",
                value=_prior("new_col_name", default="")))
            controls.append(ui.input_text("condition", "Condition",
                value=_prior("condition", default=""),
                placeholder="e.g. attendance_pct > 90"))
            controls.append(ui.input_text("true_val", "Value when true",
                value=_prior("true_val", default="1")))
            controls.append(ui.input_text("false_val", "Value when false",
                value=_prior("false_val", default="0")))
        elif action == "add_binned":
            controls.append(ui.input_text("new_col_name", "New Column Name",
                value=_prior("new_col_name", default="")))
            controls.append(ui.input_numeric("n_bins", "Number of bins",
                value=_prior("n_bins", default=3), min=2, max=20))
            controls.append(ui.input_text("bin_labels",
                "Bin labels (comma-separated, optional)",
                value=_prior("bin_labels", default=""),
                placeholder="e.g. low, medium, high"))
        elif action == "str_replace":
            controls.append(ui.input_text("find_text", "Find",
                value=_prior("find_text", default=""), placeholder="e.g. %"))
            controls.append(ui.input_text("replace_text", "Replace with (may be blank)",
                value=_prior("replace_text", default="")))
            controls.append(ui.input_checkbox("use_regex", "Find is a regular expression",
                value=bool(_prior("use_regex", default=False))))
        elif action == "str_extract":
            controls.append(ui.input_text("new_col_name", "New Column Name",
                value=_prior("new_col_name", default="")))
            controls.append(ui.input_text("pattern", "Regular expression",
                value=_prior("pattern", default=""), placeholder=r"e.g. \d+"))
        elif action == "dummy_encode":
            controls.append(ui.input_checkbox("drop_first", "Drop first level",
                value=bool(_prior("drop_first", default=False))))
            controls.append(ui.input_checkbox("keep_original", "Keep original column",
                value=bool(_prior("keep_original", default=False))))
        elif action == "ordinal_encode":
            controls.append(ui.input_text("ordinal_order",
                "Category order (comma-separated, optional)",
                value=_prior("ordinal_order", default=""),
                placeholder="e.g. low, medium, high"))

        return ui.TagList(*controls)

    def _run_transform(df):
        """Execute the current transform settings. Returns (result_df, snippet) or raises."""
        action = input.action()

        if action == "drop_columns":
            drop_cols = list(input.drop_cols())
            if not require(drop_cols, "Choose at least one column to drop."):
                return None
            return transform.drop_columns(df, drop_cols)

        col = input.col()
        if not require(col, "Choose the column to transform."):
            return None

        if action == "rename_column":
            new_name = input.new_col_name()
            if not require(new_name and new_name.strip(), "Type the new column name."):
                return None
            return transform.rename_column(df, col, new_name.strip())
        elif action == "fill_missing":
            method = input.fill_method()
            val = input.fill_value() if method == "value" else None
            return transform.fill_missing(df, col, method, val)
        elif action == "drop_missing":
            return transform.drop_missing(df, [col])
        elif action == "convert_dtype":
            return transform.convert_dtype(df, col, input.target_dtype())
        elif action == "drop_duplicates":
            return transform.drop_duplicates(df, [col])
        elif action == "add_log":
            new_name = input.new_col_name() or f"{col}_log"
            return transform.add_column_log(df, new_name, col)
        elif action == "add_zscore":
            new_name = input.new_col_name() or f"{col}_zscore"
            return transform.add_column_zscore(df, new_name, col)
        elif action == "add_rank":
            new_name = input.new_col_name() or f"{col}_rank"
            return transform.add_column_rank(df, new_name, col)
        elif action == "add_arithmetic":
            expr = (input.expr() or "").strip()
            if not require(expr, "Type an expression, e.g. salary / 12."):
                return None
            new_name = (input.new_col_name() or "").strip() or "calculated"
            return transform.add_column_arithmetic(df, new_name, expr)
        elif action == "add_conditional":
            condition = (input.condition() or "").strip()
            if not require(condition, "Type a condition, e.g. salary > 50000."):
                return None
            new_name = (input.new_col_name() or "").strip() or "flag"
            return transform.add_column_conditional(
                df, new_name, condition,
                _coerce_literal(input.true_val()),
                _coerce_literal(input.false_val()),
            )
        elif action == "add_binned":
            new_name = (input.new_col_name() or "").strip() or f"{col}_bin"
            n_bins = int(input.n_bins() or 3)
            raw_labels = (input.bin_labels() or "").strip()
            labels = [s.strip() for s in raw_labels.split(",") if s.strip()] or None
            return transform.add_column_binned(df, new_name, col, n_bins, labels)
        elif action == "str_lower":
            return transform.str_lower(df, col)
        elif action == "str_upper":
            return transform.str_upper(df, col)
        elif action == "str_strip":
            return transform.str_strip(df, col)
        elif action == "str_replace":
            find_text = input.find_text() or ""
            if not require(find_text, "Type the text to find."):
                return None
            return transform.str_replace(
                df, col, find_text, input.replace_text() or "",
                regex=bool(input.use_regex()),
            )
        elif action == "str_extract":
            pattern = (input.pattern() or "").strip()
            if not require(pattern, "Type a regular expression to extract."):
                return None
            new_name = (input.new_col_name() or "").strip() or f"{col}_extracted"
            return transform.str_extract(df, new_name, col, pattern)
        elif action == "dummy_encode":
            return transform.dummy_encode(
                df, col,
                drop_first=bool(input.drop_first()),
                keep_original=bool(input.keep_original()),
            )
        elif action == "ordinal_encode":
            order_str = input.ordinal_order().strip()
            order = [s.strip() for s in order_str.split(",") if s.strip()] if order_str else None
            return transform.ordinal_encode(df, col, order=order)
        else:
            return None

    @reactive.effect
    @reactive.event(input.preview_btn)
    def _preview():
        df = get_current_df()
        if not require(df is not None, NO_DATASET):
            return
        try:
            result = _run_transform(df)
            if result is not None:
                result_df, snippet = result
                _preview_result.set((result_df, snippet))
                last_code.set(snippet.code)
                status.done(
                    f"Preview: {result_df.shape[0]} rows x {result_df.shape[1]} cols"
                )
        except Exception as e:
            _preview_result.set(None)
            _preview_result.set(None)
            status.failed(str(e))

    @reactive.effect
    @reactive.event(input.apply_btn)
    def _apply():
        df = get_current_df()
        if not require(df is not None, NO_DATASET):
            return
        action = input.action()

        try:
            # Use preview result if available, otherwise compute fresh
            pr = _preview_result()
            if pr is not None:
                result, snippet = pr
            else:
                out = _run_transform(df)
                if out is None:
                    return
                result, snippet = out

            if action == "fill_missing":
                col = input.col()
                n_missing = df[col].isna().sum()
                if n_missing == 0:
                    status.check(
                        f"Column '{col}' has no missing values. Nothing to fill."
                    )
                    return

            # Find and update the dataset
            desc = f"{action}" if action == "drop_columns" else f"{action} on '{input.col()}'"
            for name in state.dataset_names():
                if state.get(name) is get_current_df():
                    state.update(name, result, Operation(
                        timestamp=datetime.now(), action="transform",
                        description=desc, dataset=name,
                    ))
                    state.codegen.record(snippet)
                    last_code.set(snippet.code)
                    _preview_result.set(None)
                    status.done(f"Transform applied: {action}")
                    break

        except Exception as e:
            status.failed(str(e))

    @render.text
    def transform_info():
        df = get_current_df()
        if df is None:
            return "No dataset selected."
        pr = _preview_result()
        if pr is not None:
            result_df, _ = pr
            orig_rows = df.shape[0]
            new_rows = result_df.shape[0]
            new_cols = result_df.shape[1]
            return f"PREVIEW: {new_rows} rows x {new_cols} cols (original: {orig_rows} rows) | Click Apply to commit"
        n_missing = df.isna().sum().sum()
        return f"{df.shape[0]} rows x {df.shape[1]} columns | {n_missing} missing values"

    @render.data_frame
    def preview():
        # Show preview result if available, otherwise show raw data
        pr = _preview_result()
        if pr is not None:
            result_df, _ = pr
            return render.DataGrid(round_df(result_df.head(100), get_dec()), height="400px")
        df = get_current_df()
        req(df is not None)
        return render.DataGrid(round_df(df.head(100), get_dec()), height="400px")

    code_panel_server("code", get_code=last_code)
