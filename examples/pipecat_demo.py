"""Example: Using PaisaParseProcessor inside a Pipecat voice-agent pipeline."""

from paisa_parse import ConfirmPolicy
from paisa_parse.integrations.pipecat import PaisaParseProcessor


def on_entities(result, frame):
    if result.needs_confirmation():
        for entity in result.entities:
            if entity.confirm_prompt:
                print(f"[Confirm-back] {entity.confirm_prompt}")


def build_processor() -> PaisaParseProcessor:
    return PaisaParseProcessor(
        policy=ConfirmPolicy.balanced(language="hinglish"),
        mode="annotate",
        on_parsed=on_entities,
    )


if __name__ == "__main__":
    print("Instantiate build_processor() and place it between STT and LLM in your Pipecat Pipeline.")
