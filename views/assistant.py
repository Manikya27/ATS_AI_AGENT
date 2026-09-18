"""Assistant view - a grounded chat about what the product does."""
from __future__ import annotations

import streamlit as st

from ats_agent import ATSAgent, ATSAgentError
from ats_agent.knowledge import STARTER_QUESTIONS
from views.common import require_api_key
from views.theme import view_header

HISTORY_KEY = "assistant_history"


def _history() -> list[dict[str, str]]:
    return st.session_state.setdefault(HISTORY_KEY, [])


def _answer(question: str) -> None:
    """Append the question, then the assistant's reply, to the conversation."""
    history = _history()
    api_key = require_api_key()
    if not api_key:
        return

    prior = list(history)
    history.append({"role": "user", "content": question})
    try:
        answer = ATSAgent(api_key=api_key).answer_question(question, prior)
    except ATSAgentError as e:
        # Keep the failure in the transcript so the person can see what happened
        # against their question, rather than a banner that vanishes on rerun.
        history.append({"role": "assistant", "content": f"Sorry - {e}"})
        return
    history.append({"role": "assistant", "content": answer})


def render() -> None:
    view_header(
        "Ask about Employee 360",
        "Questions about how the matching works, what happens to your files, or how "
        "to use either view. The assistant answers from this product's documentation "
        "and will say so when it doesn't know.",
    )

    history = _history()

    if not history:
        st.caption("Try one of these:")
        columns = st.columns(2)
        for i, question in enumerate(STARTER_QUESTIONS):
            with columns[i % 2]:
                if st.button(question, key=f"starter_{i}", width="stretch"):
                    _answer(question)
                    st.rerun()

    for message in history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if question := st.chat_input("Ask a question about the app..."):
        _answer(question)
        st.rerun()

    if history:
        if st.button("Clear conversation", key="assistant_clear"):
            st.session_state[HISTORY_KEY] = []
            st.rerun()
        st.caption(
            "The assistant can't see your CV or your results - those stay in the view "
            "that produced them."
        )
