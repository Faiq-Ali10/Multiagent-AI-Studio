from typing import TypedDict, Sequence
from langgraph.graph import StateGraph
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage

from prompts.planner.planner_system_prompt import planner_system_prompt


class PlannerState(TypedDict, total=False):
    messages: Sequence[BaseMessage]
    planner_summary: str
    safety_violation: bool


class PlannerAgent:
    def __init__(self, creative_llm) -> None:
        self.llm = creative_llm

    def chat_node(self, state: PlannerState) -> PlannerState:
        messages = state.get("messages", [])
        summary = state.get("planner_summary", "")
        is_violation = state.get("safety_violation", False)  # <--- 2. Extract the flag

        # 1. Prepare the System Prompt with the rolling summary
        sys_prompt = planner_system_prompt(summary)
        system_msg = SystemMessage(content=sys_prompt)

        print("@@ Planner Agent is thinking... @@", flush=True)

        try:
            if self.llm is not None:
                # 3. Create a TEMPORARY message list just for the LLM to read
                llm_messages = list(messages)
                if is_violation and len(llm_messages) > 0:
                    print(
                        "@@ Planner caught safety violation, applying alert! @@",
                        flush=True,
                    )
                    last_msg = llm_messages[-1].content
                    llm_messages[-1] = HumanMessage(
                        content=f"SYSTEM ALERT: The following user request violates studio safety guidelines for explicit/NSFW content. Politely refuse to generate it, remind them to keep requests family-friendly, and ask what safe media they would like to create instead.\n\nUser Request: {last_msg}"
                    )

                # Pass the TEMPORARY messages to the LLM
                llm_input = [system_msg] + llm_messages
                response = self.llm.invoke(llm_input)
                ai_reply = str(response.content).strip()

                # 4. Append the AI reply to the ORIGINAL CLEAN messages list
                updated_messages = list(messages)
                updated_messages.append(
                    AIMessage(content=ai_reply, name="planner_node")
                )

                # 5. Generate a new summary (This now uses the perfectly clean original prompt!)
                last_human_text = ""
                for msg in reversed(updated_messages):
                    if isinstance(msg, HumanMessage):
                        last_human_text = msg.content
                        break

                summary_sys = SystemMessage(
                    content=(
                        "You are a memory manager for an AI Creative Studio. "
                        "Update the project summary with the new interaction. "
                        "Write a concise, updated paragraph about the project goals."
                    )
                )

                summary_human = HumanMessage(
                    content=(
                        f"Old Summary: {summary}\n\n"
                        f"New User Request: {last_human_text}\n\n"
                        f"New AI Response: {ai_reply}"
                    )
                )

                summary_input_list = [summary_sys, summary_human]
                new_summary_response = self.llm.invoke(summary_input_list)
                new_summary = str(new_summary_response.content).strip()

            else:
                raise Exception("LLM Object is None")

        except Exception as e:
            print(f"@@ Chat Error: {str(e)} @@", flush=True)
            updated_messages = list(messages)
            error_msg = "I am having trouble connecting to my brain. Let us try again!"
            updated_messages.append(AIMessage(content=error_msg, name="planner_node"))
            new_summary = summary

        # 6. Return the clean messages back to the global state
        return {"messages": updated_messages, "planner_summary": new_summary}

    def get_app(self):
        workflow = StateGraph(PlannerState)

        workflow.add_node("chat", self.chat_node)

        workflow.set_entry_point("chat")
        workflow.set_finish_point("chat")

        return workflow.compile()
