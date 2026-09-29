"""Assistant view - a grounded chat about what the product does."""
from __future__ import annotations

import streamlit as st

from ats_agent import ATSAgent
from ats_agent.knowledge import STARTER_QUESTIONS
from views.memory import session_memory
from views.model_picker import selected_model
from views.common import require_api_key
from views.theme import view_header


def _answer(question: str) -> None:
    """Append the question, then the assistant's reply, to the conversation.

    The conversation lives in the session's agent memory rather than with the
    model, so switching model mid-chat continues the same thread.
    """
    api_key = require_api_key()
    if not api_key:
        return

    # A failed answer is written into the transcript by the graph itself, so
    # the person sees it against their question.
    session_memory().ask(ATSAgent(api_key=api_key, model=selected_model()), question)


def render() -> None:
    view_header(
        "Ask about Employee 360",
        "Questions about how the matching works, what happens to your files, or how "
        "to use either view. The assistant answers from this product's documentation "
        "and will say so when it doesn't know.",
    )

    memory = session_memory()
    history = memory.turns

    if not history:
        st.caption("Try one of these:")
        columns = st.columns(2)
        for i, question in enumerate(STARTER_QUESTIONS):
            with columns[i % 2]:
                if st.button(question, key=f"starter_{i}", width="stretch"):
                    _answer(question)
                    st.rerun()

    for turn in history:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"])
            if turn["model"]:
                st.caption(f"Answered by {turn['model']}")

    if question := st.chat_input("Ask a question about the app..."):
        _answer(question)
        st.rerun()

    if history:
        if st.button("Clear conversation", key="assistant_clear"):
            memory.clear_conversation()
            st.rerun()
        st.caption(
            "The assistant can't see your CV or your results - those stay in the view "
            "that produced them. Switching model keeps this conversation."
        )
