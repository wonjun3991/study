"""LangGraph 공식 overview의 hello world — LLM 없이 그래프 골격만 확인한다."""
from langgraph.graph import StateGraph, MessagesState, START, END


def mock_llm(state: MessagesState):
    return {"messages": [{"role": "ai", "content": "hello world"}]}


graph = StateGraph(MessagesState)
graph.add_node(mock_llm)
graph.add_edge(START, "mock_llm")
graph.add_edge("mock_llm", END)
graph = graph.compile()

if __name__ == "__main__":
    result = graph.invoke({"messages": [{"role": "user", "content": "hi!"}]})
    for m in result["messages"]:
        print(f"{m.type:>5}: {m.content}")
    print()
    print(graph.get_graph().draw_mermaid())
