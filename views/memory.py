"""The visitor's agent memory, held for the length of their session.

Changing model rewrites ?model= and reruns the script in the same session, so
session state is where memory has to live to survive the switch. Every view
builds its ATSAgent with `session_memory()`, and the new model picks up the
conversation, the documents and the scores the old one left.

It does not survive a full page load - clicking a nav link starts a fresh
session - and that is the intended edge: memory is for carrying one visit
across models, not for keeping anyone's CV around.
"""
from __future__ import annotations

import streamlit as st

from ats_agent import AgentMemory

MEMORY_KEY = "agent_memory"


def session_memory() -> AgentMemory:
    memory = st.session_state.get(MEMORY_KEY)
    if not isinstance(memory, AgentMemory):
        memory = AgentMemory()
        st.session_state[MEMORY_KEY] = memory
    return memory
