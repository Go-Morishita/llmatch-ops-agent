# Server operations agent

import argparse
import subprocess
from functools import partial
from typing import Annotated, TypedDict

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_ollama import ChatOllama
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages

from config import (
    STACK_NAME,
    FUNCTION_NAME,
    START_TIME,
    MAX_TOOL_CALLS,
    SYSTEM_PROMPT,
)
from tools import TOOLS


# ============ State ============

class MonitorState(TypedDict):
    messages: Annotated[list, add_messages]


# ============ Nodes ============

def fetch_logs(state: MonitorState) -> MonitorState:
    """Fetch CloudWatch logs via sam logs and build the initial messages."""
    print("=" * 60)
    print(f"Target: {STACK_NAME} / {FUNCTION_NAME}")
    print("=" * 60)
    print("[fetch_logs] Fetching logs...")
    result = subprocess.run(
        ["sam", "logs", "--stack-name", STACK_NAME, "--name", FUNCTION_NAME, "-s", START_TIME],
        capture_output=True,
        text=True,
    )
    logs = result.stdout.strip()
    if result.returncode != 0:
        logs = f"[sam logs failed] {result.stderr.strip()}"
    logs = logs or "(logs were empty)"
    print(f"[fetch_logs] Result:\n{logs}\n")
    return {"messages": [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Here are the target logs:\n\n{logs}"),
    ]}


def agent(state: MonitorState, model: str) -> MonitorState:
    """The LLM analyzes the logs and decides on tool calls if needed."""
    llm = ChatOllama(model=model).bind_tools(TOOLS)
    response = llm.invoke(state["messages"])
    if response.tool_calls:
        for call in response.tool_calls:
            print(f"[agent] Selected tool: {call['name']}(args={call['args']})")
    else:
        print("[agent] No tool used, proceeding to final report")
    return {"messages": [response]}


def call_tools(state: MonitorState) -> MonitorState:
    """Run the selected tools and print the calls and results in order."""
    tools_by_name = {t.name: t for t in TOOLS}
    last = state["messages"][-1]
    results = []
    for call in last.tool_calls:
        print(f"[tools] Running: {call['name']}(args={call['args']})")
        output = tools_by_name[call["name"]].invoke(call["args"])
        print(f"[tools] Result:\n{output}\n")
        results.append(ToolMessage(content=str(output), tool_call_id=call["id"]))
    return {"messages": results}


def report(state: MonitorState) -> MonitorState:
    """Print the final analysis result to stdout."""
    print("=" * 60)
    print("[report] Final report")
    print("=" * 60)
    print(state["messages"][-1].content)
    return state


def should_continue(state: MonitorState) -> str:
    """Route to tools if the latest LLM response has tool calls, otherwise to report.

    Stops after MAX_TOOL_CALLS tool executions so the model can't loop forever
    on failing tool calls.
    """
    last = state["messages"][-1]
    tool_calls_made = sum(1 for m in state["messages"] if isinstance(m, ToolMessage))
    if getattr(last, "tool_calls", None) and tool_calls_made < MAX_TOOL_CALLS:
        return "tools"
    if tool_calls_made >= MAX_TOOL_CALLS:
        print(f"[should_continue] reached MAX_TOOL_CALLS={MAX_TOOL_CALLS}, stopping")
    return "report"


# ============ Graph construction ============

def build_graph(model: str):
    graph = StateGraph(MonitorState)
    graph.add_node("fetch_logs", fetch_logs)
    graph.add_node("agent", partial(agent, model=model))
    graph.add_node("tools", call_tools)
    graph.add_node("report", report)

    graph.add_edge(START, "fetch_logs")
    graph.add_edge("fetch_logs", "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "report": "report"})
    graph.add_edge("tools", "agent")
    graph.add_edge("report", END)
    return graph.compile()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the server operations agent.")
    parser.add_argument("--model", required=True, help="ollama model to use")
    args = parser.parse_args()
    app = build_graph(model=args.model)
    app.invoke({"messages": []})
