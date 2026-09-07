import pytest
from dotenv import load_dotenv
load_dotenv()

from src.agents.state import AgentState

@pytest.mark.skip(reason="Relies on old SupervisorAgent.router internals removed in single-agent refactor.")
def test_supervisor_missing_info_routing():
    """
    Previously tested that the supervisor routes to END when is_missing_info=True.
    In the new single-agent architecture, this is handled inside CJSSingleAgent.process()
    via deterministic rules — not via a separate mocked router.
    """
    pass

if __name__ == "__main__":
    test_supervisor_missing_info_routing()
