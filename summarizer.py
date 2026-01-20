"""
OpenAI-powered thread summarization for kudos context.
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

# Load env vars early
load_dotenv()

_client = None


def get_client():
    """Lazily initialize OpenAI client."""
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    return _client

SYSTEM_PROMPT = """You summarize Slack thread conversations into a single, brief sentence describing what was accomplished or discussed. 
Keep it under 20 words. Focus on the task or achievement. Be direct and factual.
Do not include names or @mentions in your summary."""


from typing import List


def summarize_thread(messages: List[str]) -> str:
    """
    Summarize a list of thread messages into a brief description.
    
    Args:
        messages: List of message texts from the thread
    
    Returns:
        A brief summary string (1 sentence, ~20 words max)
    """
    if not messages:
        return "their contributions"
    
    # Join messages with newlines for context
    thread_text = "\n".join(messages)
    
    # Truncate if too long (keep it minimal for privacy)
    if len(thread_text) > 2000:
        thread_text = thread_text[:2000] + "..."
    
    try:
        response = get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Summarize this thread:\n\n{thread_text}"},
            ],
            max_tokens=50,
            temperature=0.3,
        )
        summary = response.choices[0].message.content.strip()
        
        # Remove quotes if the model wrapped the response
        if summary.startswith('"') and summary.endswith('"'):
            summary = summary[1:-1]
        
        return summary
    
    except Exception as e:
        print(f"OpenAI summarization failed: {e}")
        return "their work in the thread"
