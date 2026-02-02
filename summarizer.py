"""
OpenAI-powered thread summarization for kudos context.
"""

import os
from typing import List
from dotenv import load_dotenv
from openai import OpenAI

# Load env vars early
load_dotenv()

_client = None


def get_client():
    """Lazily initialize OpenAI client."""
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        _client = OpenAI(api_key=api_key)
    return _client


SYSTEM_PROMPT = """You summarize Slack thread conversations into a brief phrase describing the task or achievement.
Rules:
- Maximum 10 words
- Focus on WHAT was done (e.g., "fixing the dashboard bug", "deploying the new API", "reviewing the PR")
- Start with a verb in -ing form (fixing, implementing, reviewing, merging, etc.)
- Do NOT include names, @mentions, or pronouns
- Do NOT use generic phrases like "their work" or "contributions"
- Be specific about the actual task discussed
- Return ONLY the summary phrase, nothing else"""


def summarize_thread(messages: List[str]) -> str:
    """
    Summarize a list of thread messages into a brief description.

    Args:
        messages: List of message texts from the thread

    Returns:
        A brief summary string (~10 words max)
    """
    if not messages:
        return "their contributions"

    # Join messages with newlines for context
    thread_text = "\n".join(messages)

    # Truncate if too long
    if len(thread_text) > 2000:
        thread_text = thread_text[:2000] + "..."

    try:
        print(f"Calling OpenAI with {len(messages)} messages...")
        print(f"Thread text: {thread_text[:200]}...")

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
        print(f"OpenAI returned: {summary}")

        # Remove quotes if the model wrapped the response
        if summary.startswith('"') and summary.endswith('"'):
            summary = summary[1:-1]

        return summary

    except Exception as e:
        print(f"OpenAI summarization failed: {e}")
        # Fallback: use first message snippet as context
        if messages:
            first_msg = messages[0][:50].strip()
            return f"helping with: {first_msg}..."
        return "their awesome contribution"
