from src.agents.state import AgentState
from src.agents.single_agent import CJSSingleAgent
from dotenv import load_dotenv
load_dotenv()

# Initialize unified Single Agent
single_agent = CJSSingleAgent()

class SingleAgentWrapper:
    """Wrapper maintaining 100% interface compatibility for cjs_bot.invoke(state)."""
    def invoke(self, state, config=None):
        if isinstance(state, dict):
            state_obj = AgentState(**state)
        else:
            state_obj = state
        res = single_agent.process(state_obj)
        if hasattr(res, "model_dump"):
            return res.model_dump()
        return res

cjs_bot = SingleAgentWrapper()

if __name__ == "__main__":
    # Test Mixed Intent
    test_state = AgentState(raw_message="Hi Boss, update order CJS-12345 to 8000 stitches. Also, what are my tasks for today?")
    print("--- STARTING SUPERVISOR GRAPH ---")
    final_output = cjs_bot.invoke(test_state)
    print("--- FINAL OUTPUT ---")
    print(final_output.get("aggregated_reasoning"))
    print(f"Final Step: {final_output.get('next_step')}")
