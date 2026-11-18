import json
import re
import logging
import os
import sys

logger = logging.getLogger(__name__)

def repair_json(json_str: str) -> any:
    """
    [V25.0] ULTIMATE JSON HUNTER (GLOBAL)
    Surgically isolates JSON objects from LLM prose using brace matching
    and multi-strategy recovery.
    """
    if not json_str:
        return None

    # 1. Strip common LLM non-standard chars and invalid escapes
    json_str = json_str.replace("Π", "3.14159").replace("M-^@", "3.14159")

    # [TITAN V212.0] SCIENTIFIC BACKSLASH SANITIZATION
    # Physically sanitize non-JSON escapes (like LaTeX \lambda, \nabla, \frac, \beta, \tau, \rho) 
    # to prevent parser collapse or control-character corruption during extraction.
    latex_prefixes = (
        "nabla", "nu", "neq", "notin", "norm", "natural",
        "tau", "theta", "times", "text", "tilde", "to", "top", "triangle",
        "rho", "rightarrow", "right", "real",
        "beta", "bar", "begin", "binom", "big", "bf", "mathbf", "mathbb",
        "frac", "forall", "phi", "footnotesize"
    )
    sanitized_chars = []
    i = 0
    n = len(json_str)
    while i < n:
        if json_str[i] == '\\':
            if i + 1 < n:
                next_char = json_str[i+1]
                if next_char in ['"', '\\', '/']:
                    sanitized_chars.append('\\')
                    sanitized_chars.append(next_char)
                    i += 2
                    continue
                elif next_char in ['n', 'r', 't', 'b', 'f']:
                    rest = json_str[i+1:i+15]
                    if any(rest.startswith(lp) for lp in latex_prefixes):
                        sanitized_chars.append('\\\\')
                        i += 1
                        continue
                    sanitized_chars.append('\\')
                    sanitized_chars.append(next_char)
                    i += 2
                    continue
                elif next_char == 'u':
                    # Check if followed by 4 hex digits
                    if i + 5 < n and all(c in '0123456789abcdefABCDEF' for c in json_str[i+2:i+6]):
                        sanitized_chars.append('\\')
                        sanitized_chars.append('u')
                        sanitized_chars.append(json_str[i+2:i+6])
                        i += 6
                        continue
            # If not a valid JSON escape, escape it!
            sanitized_chars.append('\\\\')
            i += 1
        else:
            sanitized_chars.append(json_str[i])
            i += 1
    json_str = "".join(sanitized_chars)

    json_str = json_str.replace(r"\*", "*").replace(r"\_", "_")
    # Strip trailing commas before closing braces/brackets (e.g. {"a": 1,} or [1, 2,])
    json_str = re.sub(r",\s*([}\]])", r"\1", json_str)
    
    # 2. Markdown Block Hunter
    block_match = re.search(r'```(?:json)?\s*(.*?)\s*```', json_str, re.DOTALL | re.IGNORECASE)
    if block_match:
        try:
            return json.loads(block_match.group(1).strip())
        except:
            pass

    # 3. Strategy: Brace counting method (non-greedy, finds all valid JSON objects)
    potential_matches = []
    
    def find_objects(s, start_char='{', end_char='}'):
        objs = []
        for i in range(len(s)):
            if s[i] == start_char:
                count = 0
                for j in range(i, len(s)):
                    if s[j] == start_char:
                        count += 1
                    elif s[j] == end_char:
                        count -= 1
                    if count == 0:
                        try:
                            parsed = json.loads(s[i:j+1])
                            objs.append(parsed)
                        except:
                            pass
                        break
        return objs

    objs = find_objects(json_str, '{', '}') + find_objects(json_str, '[', ']')
    
    if objs:
        # Return the most complex one (longest likely has most data)
        return sorted(objs, key=lambda x: len(str(x)), reverse=True)[0]

    # 4. Strategy: Aggressive Truncated JSON recovery
    # Isolate the starting block
    first_brace = json_str.find('{')
    first_bracket = json_str.find('[')
    
    start_idx = -1
    if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        start_idx = first_brace
    elif first_bracket != -1:
        start_idx = first_bracket
        
    if start_idx == -1: return None
    
    cleaned = json_str[start_idx:]
    
    # Attempt to close the structure by stripping trailing junk
    for _ in range(10): 
        open_braces = cleaned.count('{')
        close_braces = cleaned.count('}')
        open_brackets = cleaned.count('[')
        close_brackets = cleaned.count(']')

        repaired = cleaned
        if open_brackets > close_brackets:
            repaired += ']' * (open_brackets - close_brackets)
        if open_braces > close_braces:
            repaired += '}' * (open_braces - close_braces)

        try:
            return json.loads(repaired)
        except:
            # Cut at the last likely boundary and try again
            last_break = max(cleaned.rfind(','), cleaned.rfind(':'), cleaned.rfind('"'), cleaned.rfind('}'), cleaned.rfind(']'))
            if last_break <= 0: break
            cleaned = cleaned[:last_break]
            
    return None
