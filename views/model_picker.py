"""The model chooser, and the one place a view asks which model to run.

The API key remains server-side configuration that no visitor ever sees or
supplies. The model is now a visible, deliberate choice: which one analysed
your CV is something a person reading the result is entitled to know, and
different models genuinely suit different jobs here - a batch of twenty CVs
and one application you care about are not the same task.

The choice rides in the URL rather than session state because navigation is a
full page load. It is validated against the deployment's allowlist on the way
in, so a hand-edited parameter cannot point the agent at an arbitrary model.
"""
from __future__ import annotations

import streamlit as st

from ats_agent.model_catalog import DEFAULT_MODEL_ID, available_models, describe, resolve

MODEL_PARAM = "model"


def selected_model() -> str:
    """The model id to run with, already validated against the allowlist."""
    return resolve(st.query_params.get(MODEL_PARAM))


def render_model_picker() -> None:
    """A compact chooser, shown on every working view.

    Folded into a popover rather than left open: the model matters, but it is
    a setting, and a settings control that pushes the actual work down the page
    is in the wrong place.
    """
    options = available_models()
    if len(options) < 2:
        # One model on offer is not a choice; saying so would be noise.
        return

    ids = [option.id for option in options]
    current = selected_model()
    index = ids.index(current) if current in ids else 0

    _, control = st.columns([3, 1])
    with control:
        with st.popover(f"Model: {current}", width="stretch"):
            st.caption(
                "Which AI model analyses your documents. All of them run on this "
                "deployment's own API key - you are never asked for one."
            )
            chosen = st.radio(
                "Model",
                ids,
                index=index,
                key="model_choice",
                label_visibility="collapsed",
                format_func=lambda model_id: describe(model_id).display,
                captions=[describe(model_id).blurb for model_id in ids],
            )

    if chosen != current:
        # The URL is the source of truth, so a change has to be written back
        # there or the next page load reverts it.
        if chosen == DEFAULT_MODEL_ID:
            st.query_params.pop(MODEL_PARAM, None)
        else:
            st.query_params[MODEL_PARAM] = chosen
        st.rerun()
