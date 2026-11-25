"""Example: Using PaisaParseAgentMixin in a LiveKit Agents voice assistant."""

from paisa_parse import ConfirmPolicy
from paisa_parse.integrations.livekit import PaisaParseAgentMixin, PaisaParseHook

try:
    from livekit.agents import Agent
except ImportError:  # Allow running syntax checks without livekit-agents installed
    class Agent:  # type: ignore[no-redef]
        async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
            pass


class HinglishBankingAgent(PaisaParseAgentMixin, Agent):
    def __init__(self) -> None:
        super().__init__()
        self.paisa_hook = PaisaParseHook(
            policy=ConfirmPolicy.strict(language="en-IN"),
            inject_context=True,
        )


if __name__ == "__main__":
    agent = HinglishBankingAgent()
    print("Initialized HinglishBankingAgent with", type(agent.paisa_hook).__name__)
