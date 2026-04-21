"""
=====================================================================================
👋 AI WELCOME SERVICE (First-Impression Generator)
=====================================================================================
This file generates the welcome message when user opens the AI chat panel.

TWO SCENARIOS:
  1. User hasn't searched yet → Generic welcome with starter suggestions
  2. User was searching "shoes" → Context-aware welcome about shoes
  
WHY THIS MATTERS:
  - First impression matters — dynamic welcomes feel more "alive"
  - Context-aware suggestions get higher click-through
  - Shows users the AI actually "sees" what they're doing

FALLBACK BEHAVIOR:
  If OpenAI is down, we return hardcoded friendly welcomes (never blank screen)
=====================================================================================
"""

import json
import logging

from app.config import openai_client

# Prompt + fallback texts (separated for easy tuning)
from app.prompts.ai_welcome_prompt import (
    build_ai_welcome_prompt,
    WELCOME_FALLBACK_MESSAGE,
    WELCOME_FALLBACK_SUGGESTIONS,
    WELCOME_DEFAULT_MESSAGE,
    WELCOME_DEFAULT_SUGGESTIONS,
)

from app.core.constants import (
    AI_CHAT_MODEL,
    AI_TEMPERATURE_CREATIVE,
    MAX_AI_SUGGESTIONS
)

logger = logging.getLogger(__name__)


# =========================================================================
# 👋 GENERATE AI WELCOME
# =========================================================================
async def generate_ai_welcome(current_query: str) -> dict:
    """
    Generates a dynamic welcome message + suggestion chips.
    
    ARGS:
        current_query: What user was searching before opening chat
                       Empty string "" if fresh open (no context)
    
    RETURNS:
        dict: {
            "ai_message": "Welcome text with emojis ✨",
            "suggestions": ["Suggestion 1", "Suggestion 2", ...]
        }
    """
    
    # =====================================================================
    # STEP 1: BUILD THE PROMPT
    # =====================================================================
    # Use our separated prompt file
    system_prompt = build_ai_welcome_prompt(current_query)
    
    try:
        # =====================================================================
        # STEP 2: CALL OPENAI
        # =====================================================================
        llm_response = await openai_client.chat.completions.create(
            model=AI_CHAT_MODEL,
            # Force JSON response (so we can parse it reliably)
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt}
            ],
            # Temperature 0.7 = more creative/varied welcomes
            # (Unlike AI assistant which uses 0.0 for deterministic filter extraction)
            temperature=AI_TEMPERATURE_CREATIVE
        )
        
        # =====================================================================
        # STEP 3: PARSE THE RESPONSE
        # =====================================================================
        parsed = json.loads(llm_response.choices[0].message.content)
        
        # =====================================================================
        # STEP 4: RETURN WITH FALLBACKS FOR MISSING FIELDS
        # =====================================================================
        return {
            # If AI didn't provide ai_message, use default friendly one
            "ai_message": parsed.get("ai_message", WELCOME_DEFAULT_MESSAGE),
            
            # Get suggestions, use defaults if missing
            # Cap at MAX_AI_SUGGESTIONS (4)
            "suggestions": parsed.get(
                "suggestions",
                WELCOME_DEFAULT_SUGGESTIONS
            )[:MAX_AI_SUGGESTIONS]
        }
    
    except Exception as e:
        # =====================================================================
        # SAFETY NET: OpenAI down or error
        # =====================================================================
        # Return hardcoded welcome — user never sees a blank chat panel
        logger.error(f"❌ AI Welcome Error: {e}")
        
        return {
            "ai_message": WELCOME_FALLBACK_MESSAGE,
            "suggestions": WELCOME_FALLBACK_SUGGESTIONS
        }