"""AI Assistant module -- Socratic analysis guide.

Provides four modes:
  - Suggest: recommends the next analysis step based on workflow history.
  - Interpret: explains the most recent analysis result in plain language.
  - Challenge: pushes back on the student's interpretation with Socratic
    questions about common statistical pitfalls.
  - Query: translates a natural-language question into pandas code.

All logic is rule-based (no external API key required).
"""

from __future__ import annotations

from shiny import module, reactive, render, req, ui

from pyanalytica.ai import (
    challenge_interpretation,
    interpret_result,
    natural_language_to_pandas,
    suggest_next_step,
)
from pyanalytica.core.state import WorkbenchState
from pyanalytica.ui.components.chat_panel import chat_panel_server, chat_panel_ui


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

@module.ui
def assistant_ui():
    """AI Assistant tab layout with sidebar controls and chat area."""
    return ui.layout_sidebar(
        ui.sidebar(
            ui.input_select(
                "mode",
                "Assistant Mode",
                choices={
                    "suggest": "Suggest Next Step",
                    "interpret": "Interpret Result",
                    "challenge": "Challenge My Thinking",
                    "query": "Natural Language Query",
                },
            ),
            ui.output_ui("context_info"),
            ui.hr(),
            ui.p(
                "The assistant uses rule-based analysis. "
                "No API key required.",
                class_="text-muted small",
            ),
            width=280,
        ),
        chat_panel_ui("chat"),
        ui.output_ui("quick_actions"),
    )


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

@module.server
def assistant_server(input, output, session, state: WorkbenchState, get_current_df):
    """AI Assistant server logic.

    Parameters
    ----------
    state:
        The shared :class:`WorkbenchState` holding datasets and history.
    get_current_df:
        A reactive callable returning the currently-selected DataFrame
        (or ``None``).
    """

    # ---- Build df_info dict from the current DataFrame ----
    def _build_df_info():
        """Return a metadata dict for the current DataFrame."""
        df = get_current_df()
        if df is None:
            return {}
        return {
            "columns": list(df.columns),
            "n_rows": len(df),
            "n_cols": len(df.columns),
            "dtypes": {col: str(dt) for col, dt in df.dtypes.items()},
        }

    # ---- Message handler dispatches to the selected AI mode ----
    def _handle_message(user_msg: str) -> str:
        """Route the user's message to the appropriate AI function."""
        mode = input.mode()

        if mode == "suggest":
            df = get_current_df()
            return suggest_next_step(state.history, df)

        elif mode == "interpret":
            # Without a stored last-result dict we give guidance
            if not state.history:
                return (
                    "Run an analysis first, then ask me to interpret the "
                    "results.  Try Relate > Two Variables, or Model, and "
                    "run something."
                )
            last = state.history[-1]
            result_dict = last.details if last.details else {}
            if not result_dict:
                return (
                    f"Your last action was: {last.description}\n\n"
                    "I don't have detailed numeric results to interpret.  "
                    "Run a statistical test (Relate > Two Variables, or "
                    "Advanced > Means, Correlation, etc.) and I'll explain the output."
                )
            return interpret_result(result_dict, analysis_type=last.action)

        elif mode == "challenge":
            # Use the user's message as their interpretation
            result_dict = {}
            if state.history:
                result_dict = state.history[-1].details or {}
            return challenge_interpretation(user_msg, result_dict or None)

        elif mode == "query":
            df_info = _build_df_info()
            return natural_language_to_pandas(user_msg, df_info)

        return "Unknown mode selected."

    # ---- Wire up the chat panel ----
    prefill = chat_panel_server("chat", on_message=_handle_message)

    # ---- Context info panel (sidebar) ----
    @render.ui
    def context_info():
        df = get_current_df()
        mode = input.mode()

        items = []

        # Dataset summary
        if df is not None:
            n_rows, n_cols = df.shape
            items.append(
                ui.div(
                    ui.tags.strong("Current dataset: "),
                    f"{n_rows} rows, {n_cols} columns",
                    class_="mb-2 small",
                )
            )
        else:
            items.append(
                ui.div(
                    ui.tags.em("No dataset loaded"),
                    class_="mb-2 small text-muted",
                )
            )

        # History summary
        n_ops = len(state.history)
        if n_ops > 0:
            last_action = state.history[-1].description
            items.append(
                ui.div(
                    ui.tags.strong("Operations: "),
                    str(n_ops),
                    class_="mb-1 small",
                )
            )
            items.append(
                ui.div(
                    ui.tags.strong("Last: "),
                    last_action,
                    class_="mb-2 small text-truncate",
                    style="max-width: 240px;",
                )
            )

        # Mode hint
        hints = {
            "suggest": "Ask 'What should I do next?' to get suggestions based on your workflow.",
            "interpret": "Sends your last analysis result to the interpreter.  Run a test first.",
            "challenge": "Type your interpretation and I'll ask Socratic questions to test it.",
            "query": "Ask a question in plain English and I'll generate pandas code.",
        }
        items.append(
            ui.div(
                ui.tags.em(hints.get(mode, "")),
                class_="small text-muted mt-1",
            )
        )

        return ui.div(*items)

    # ---- Quick-action buttons ----
    @render.ui
    def quick_actions():
        mode = input.mode()

        buttons = []
        if mode == "suggest":
            buttons = [
                ("What should I do next?", "next_step_btn"),
                ("Summarize my workflow so far", "workflow_btn"),
            ]
        elif mode == "interpret":
            buttons = [
                ("Interpret my last result", "interpret_btn"),
            ]
        elif mode == "challenge":
            buttons = [
                ("I think the result is significant", "sig_btn"),
                ("There is no effect", "no_effect_btn"),
                ("This proves a causal relationship", "causal_btn"),
            ]
        elif mode == "query":
            buttons = [
                ("How many rows?", "rows_btn"),
                ("Show missing values", "missing_btn"),
                ("Describe the data", "describe_btn"),
            ]

        if not buttons:
            return ui.div()

        action_buttons = []
        for label, btn_id in buttons:
            action_buttons.append(
                ui.input_action_button(
                    btn_id,
                    label,
                    class_="btn-sm btn-outline-secondary me-1 mb-1",
                )
            )

        return ui.div(
            ui.tags.strong("Quick actions:", class_="small me-2"),
            *action_buttons,
            class_="mt-3 p-2 border-top",
        )

    # ---- Quick-action handlers ----
    @reactive.effect
    @reactive.event(input.next_step_btn)
    def _qa_next_step():
        prefill("What should I do next?")

    @reactive.effect
    @reactive.event(input.workflow_btn)
    def _qa_workflow():
        prefill("Summarize my workflow so far")

    @reactive.effect
    @reactive.event(input.interpret_btn)
    def _qa_interpret():
        prefill("Interpret my last result")

    @reactive.effect
    @reactive.event(input.sig_btn)
    def _qa_sig():
        prefill("I think the result is significant")

    @reactive.effect
    @reactive.event(input.no_effect_btn)
    def _qa_no_effect():
        prefill("There is no effect")

    @reactive.effect
    @reactive.event(input.causal_btn)
    def _qa_causal():
        prefill("This proves a causal relationship")

    @reactive.effect
    @reactive.event(input.rows_btn)
    def _qa_rows():
        prefill("How many rows are there?")

    @reactive.effect
    @reactive.event(input.missing_btn)
    def _qa_missing():
        prefill("Show missing values")

    @reactive.effect
    @reactive.event(input.describe_btn)
    def _qa_describe():
        prefill("Describe the data")
