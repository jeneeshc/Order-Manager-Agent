from src.agents.state import AgentState

class SocialMediaAgent:
    def __init__(self):
        self.name = "Social Media Content Agent"

    def process(self, state: AgentState) -> AgentState:
        """
        Agent 4 Logic:
        - Triggered when an Order changes state to "Produced".
        - Take order context (Fabric, Embroidery Type, Design Image logic).
        - Call `fal.ai` for video generation if Boss uploads static product images.
        - Call Gemini/OpenAI to draft beautiful, engaging captions with Hashtags.
        Sets state.final_reply with the caption — Supervisor sends it verbatim.
        """
        print(f"[{self.name}] Drafting Instagram content for Order: {state.order_id}")
        
        # Mocking content draft
        caption = (f"✨ Beautiful {state.embroidery_type} embroidery on {state.fabric_type}! \n\n"
                   f"Just completed another custom design. With over {state.stitch_count} precise stitches, "
                   f"the detail is unmatched! \n\n"
                   f"#CJSDesigns #MachineEmbroidery #EmbroideryArt #{state.embroidery_type}")
                   
        print(f"[{self.name}] Generated Caption:\n{caption}")
        
        # In reality, trigger fal.ai video/image enhancement API right here
        # E.g. fal_client.run("fal-ai/fast-video", arguments={"image_url": ...})
        
        # Own the reply format — Supervisor sends this verbatim at END.
        state.final_reply = caption
        state.aggregated_reasoning += f"\n[Social Media Agent]: Generated Instagram caption for Order {state.order_id}.\n"
        
        return state
