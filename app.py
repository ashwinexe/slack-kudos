"""
Devfolio Kudos Bot - Main application.
A lightweight Slack bot for giving kudos.
"""

import os
import random
from typing import Optional, List
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from summarizer import summarize_thread

# Load environment variables
load_dotenv()

# Initialize the app
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
)

KUDOS_CHANNEL_ID = os.environ.get("KUDOS_CHANNEL_ID")

CELEBRATION_EMOJIS = ["🎉", "🙌", "⭐", "🚀", "💪", "🔥", "✨", "👏", "💯", "🏆"]


def fetch_thread_messages(client, channel_id: str, thread_ts: str) -> List[str]:
    """Fetch all messages from a thread."""
    try:
        # First try to join the channel (in case bot was just added)
        try:
            client.conversations_join(channel=channel_id)
        except Exception:
            pass  # Already in channel or can't join (private)
        
        result = client.conversations_replies(
            channel=channel_id,
            ts=thread_ts,
            limit=50,
        )
        messages_list = []
        for msg in result.get("messages", []):
            if msg.get("text") and not msg.get("bot_id"):
                messages_list.append(msg["text"])
        print(f"Fetched {len(messages_list)} messages from thread")
        return messages_list
    except Exception as e:
        print(f"Error fetching thread (channel={channel_id}, ts={thread_ts}): {e}")
        return []


def get_channel_name(client, channel_id: str) -> str:
    """Get channel name from channel ID."""
    try:
        result = client.conversations_info(channel=channel_id)
        return f"#{result['channel']['name']}"
    except Exception:
        return "a channel"


def get_thread_link(client, channel_id: str, thread_ts: str) -> str:
    """Generate a permalink to the thread."""
    try:
        result = client.chat_getPermalink(channel=channel_id, message_ts=thread_ts)
        return result.get("permalink", "")
    except Exception as e:
        print(f"Error getting permalink: {e}")
        return ""


def post_kudos_to_channel(client, sender_id: str, receiver_id: str, summary: str, thread_link: str):
    """Post the kudos message to the #kudos channel."""
    if not KUDOS_CHANNEL_ID:
        print("KUDOS_CHANNEL_ID not set")
        return False

    try:
        emoji = random.choice(CELEBRATION_EMOJIS)
        # Use Slack's link format: <URL|text> for hyperlinked summary
        if thread_link:
            summary_with_link = f"<{thread_link}|{summary}>"
        else:
            summary_with_link = summary
        message = f"<@{sender_id}> gave <@{receiver_id}> a kudos for {summary_with_link} {emoji}"
        client.chat_postMessage(
            channel=KUDOS_CHANNEL_ID,
            text=message,
            unfurl_links=False,
            unfurl_media=False,
        )
        return True
    except Exception as e:
        print(f"Error posting to kudos channel: {e}")
        return False


# ============================================================
# MESSAGE SHORTCUT: Three-dot menu -> "Give Kudos"
# ============================================================

@app.shortcut("give_kudos")
def handle_give_kudos_shortcut(ack, shortcut, client):
    """
    Handle the 'Give Kudos' message shortcut.
    Opens a modal to select who gets the kudos.
    """
    ack()

    message = shortcut.get("message", {})
    channel_id = shortcut.get("channel", {}).get("id")
    message_ts = message.get("ts")
    thread_ts = message.get("thread_ts") or message_ts
    message_user = message.get("user")  # Author of the clicked message

    # Store context in private_metadata
    metadata = f"{channel_id}|{thread_ts}"

    client.views_open(
        trigger_id=shortcut["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "kudos_modal",
            "private_metadata": metadata,
            "title": {"type": "plain_text", "text": "Give Kudos"},
            "submit": {"type": "plain_text", "text": "Send Kudos"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "recipient_block",
                    "element": {
                        "type": "users_select",
                        "action_id": "recipient",
                        "initial_user": message_user,
                        "placeholder": {"type": "plain_text", "text": "Select a person"},
                    },
                    "label": {"type": "plain_text", "text": "Who deserves kudos?"},
                },
            ],
        },
    )


@app.view("kudos_modal")
def handle_kudos_modal_submission(ack, body, client, view):
    """Handle the kudos modal submission."""
    ack()
    print("=== KUDOS MODAL SUBMITTED ===", flush=True)

    sender_id = body["user"]["id"]
    receiver_id = view["state"]["values"]["recipient_block"]["recipient"]["selected_user"]

    # Parse metadata
    metadata = view.get("private_metadata", "")
    parts = metadata.split("|")
    channel_id = parts[0] if len(parts) > 0 else None
    thread_ts = parts[1] if len(parts) > 1 else None
    print(f"Channel: {channel_id}, Thread: {thread_ts}", flush=True)

    # Prevent self-kudos
    if receiver_id == sender_id:
        print("Self-kudos blocked", flush=True)
        return

    # Get thread context and summarize
    if thread_ts and channel_id:
        print("Fetching thread messages...", flush=True)
        thread_messages = fetch_thread_messages(client, channel_id, thread_ts)
        print(f"Got {len(thread_messages)} messages: {thread_messages[:2]}...", flush=True)
        summary = summarize_thread(thread_messages)
        print(f"Summary: {summary}", flush=True)
        thread_link = get_thread_link(client, channel_id, thread_ts)
    else:
        summary = "their contributions"
        thread_link = ""

    # Post to #kudos channel
    print(f"Posting kudos: {summary}", flush=True)
    post_kudos_to_channel(client, sender_id, receiver_id, summary, thread_link)


def main():
    """Start the bot."""
    app_token = os.environ.get("SLACK_APP_TOKEN")

    if app_token:
        print("Starting bot in Socket Mode...")
        handler = SocketModeHandler(app, app_token)
        handler.start()
    else:
        port = int(os.environ.get("PORT", 3000))
        print(f"Starting bot in HTTP mode on port {port}...")
        app.start(port=port)


if __name__ == "__main__":
    main()
