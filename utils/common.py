import sys
sys.path.append("../")

import json
import re
from typing import Dict, Optional, List
from loguru import logger



def extract_pattern(content: str, pattern: str) -> Optional[str]:
    try:
        _pattern = fr"<{pattern}>(.*?)</{pattern}>"
        match = re.search(_pattern, content, re.DOTALL)
        if match:
            text = match.group(1)
            return text.strip()
        else:
            return None
    except Exception as e:
        logger.warning(f"Error extracting answer: {e}, current content: {content}")
        return None
        
        
def extract_dict_from_str(text: str) -> Optional[Dict]:
    r"""Extract dict from LLM's outputs including "```json ```" tag."""
    text = text.replace("\\", "")
    pattern = r'```json\s*(.*?)```'
    match = re.search(pattern, text, re.DOTALL)
    
    if match:
        json_str = match.group(1).strip()
        try:
            # Parse the JSON string into a dictionary
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None
    return None 
