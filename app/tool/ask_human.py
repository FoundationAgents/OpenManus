# Removed imports for asyncio, sys, Path, and gui.backend.agent_manager
# Removed _gui_interaction_available flag and related logic

from app.tool.base import BaseTool # Ensure BaseTool is imported

class AskHuman(BaseTool):
    name: str = "AskHuman"
    description: str = (
        "Asks the human user for input. Useful when the agent needs clarification, "
        "guidance, or when it's stuck and needs human intervention. "
        "The 'inquire' parameter should be a clear question or prompt for the user."
    )
    parameters: dict = { # Changed from str to dict based on BaseTool
        "type": "object",
        "properties": {
            "inquire": {
                "type": "string",
                "description": "The question or prompt to ask the human user.",
            },
        },
        "required": ["inquire"],
    }

    # Making it async for consistency with other tools, even if it uses sync input() for non-GUI mode.
    async def execute(self, inquire: str, **kwargs) -> str:
        from app.logger import logger # Ensure logger is available

        # This is the fallback console interaction if GUI is not used or wrapper not in place.
        print(f"--- HUMAN INPUT REQUIRED ---")
        print(inquire)
        
        user_response = "" # Default to empty string
        try:
            user_response = input("Your response: ")
            logger.info(f"AskHuman: User responded with: '{user_response[:200]}'") # Log first 200 chars
        except EOFError:
            logger.warning("AskHuman: EOFError caught when attempting to read user input. Assuming non-interactive environment. Returning empty string.")
            user_response = "" # Default response for non-interactive environment
        except Exception as e:
            logger.error(f"AskHuman: An unexpected error occurred while getting user input: {e}")
            # Returning an error message or empty string, as per example
            user_response = f"Error in AskHuman: {str(e)}" # Or simply "" if preferred

        print(f"--- END HUMAN INPUT ---")
        return user_response.strip() # Added strip() for consistency
