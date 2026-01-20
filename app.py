"""
Devfolio Kudos Bot - Main application.
A lightweight Slack bot for giving and tracking kudos.
"""

import os
import re
from typing import Optional, List
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

import db
import messages
from summarizer import summarize_thread

# Load environment variables
load_dotenv()

# Initialize the app with bot token and signing secret
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
)

KUDOS_CHANNEL_ID = os.environ.get("KUDOS_CHANNEL_ID")

# Regex to extract user ID from Slack mention format <@U123ABC>
USER_MENTION_PATTERN = re.compile(r"<@([A-Z0-9]+)(?:\|[^>]*)?>")


def extract_user_id(text: str) -> Optional[str]:
    """Extract the first user ID from a text containing @mentions."""
    match = USER_MENTION_PATTERN.search(text)
    return match.group(1) if match else None


def fetch_thread_messages(client, channel_id: str, thread_ts: str) -> List[str]:
    """Fetch all messages from a thread."""
    try:
        result = client.conversations_replies(
            channel=channel_id,
            ts=thread_ts,
            limit=50,
        )
        messages_list = []
        for msg in result.get("messages", []):
            if msg.get("text") and not msg.get("bot_id"):
                messages_list.append(msg["text"])
        return messages_list
    except Exception as e:
        print(f"Error fetching thread: {e}")
        return []


def send_dm(client, user_id: str, text: str):
    """Send a direct message to a user."""
    try:
        result = client.conversations_open(users=[user_id])
        dm_channel = result["channel"]["id"]
        client.chat_postMessage(channel=dm_channel, text=text)
    except Exception as e:
        print(f"Error sending DM to {user_id}: {e}")


def process_kudos(client, sender_id: str, receiver_id: str, channel_id: str, thread_ts: Optional[str]):
    """Core kudos logic - used by both slash command and message shortcut."""
    # Get thread context if available
    if thread_ts:
        thread_messages = fetch_thread_messages(client, channel_id, thread_ts)
        summary = summarize_thread(thread_messages)
    else:
        summary = "their great work"

    # Store the kudos
    db.add_kudos(
        sender_id=sender_id,
        receiver_id=receiver_id,
        summary=summary,
        thread_ts=thread_ts,
        channel_id=channel_id,
    )

    # Get receiver's updated stats
    stats = db.get_user_stats(receiver_id)

    # Post to #kudos channel
    if KUDOS_CHANNEL_ID:
        try:
            public_message = messages.format_public_message(sender_id, receiver_id, summary)
            client.chat_postMessage(channel=KUDOS_CHANNEL_ID, text=public_message)
        except Exception as e:
            print(f"Error posting to kudos channel: {e}")

    # Send private DM to receiver
    dm_text = messages.format_private_dm(
        sender_id=sender_id,
        summary=summary,
        month_count=stats["month_count"],
        all_time_count=stats["all_time_count"],
    )
    send_dm(client, receiver_id, dm_text)

    return summary


# ============================================================
# MESSAGE SHORTCUT: Right-click any message -> "Give Kudos"
# ============================================================

@app.shortcut("give_kudos")
def handle_give_kudos_shortcut(ack, shortcut, client):
    """
    Handle the 'Give Kudos' message shortcut.
    User right-clicks a message and selects 'Give Kudos'.
    Opens a modal to confirm who gets the kudos.
    """
    ack()

    # Get context from the message that was right-clicked
    message = shortcut.get("message", {})
    channel_id = shortcut.get("channel", {}).get("id")
    message_ts = message.get("ts")
    thread_ts = message.get("thread_ts") or message_ts  # Use thread root if in thread
    message_user = message.get("user")  # Author of the clicked message

    # Open modal to confirm kudos recipient
    client.views_open(
        trigger_id=shortcut["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "kudos_modal",
            "private_metadata": f"{channel_id}|{thread_ts}",
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

    sender_id = body["user"]["id"]
    receiver_id = view["state"]["values"]["recipient_block"]["recipient"]["selected_user"]

    # Parse metadata
    metadata = view.get("private_metadata", "")
    parts = metadata.split("|")
    channel_id = parts[0] if len(parts) > 0 else None
    thread_ts = parts[1] if len(parts) > 1 else None

    # Prevent self-kudos
    if receiver_id == sender_id:
        send_dm(client, sender_id, messages.format_error_self_kudos())
        return

    # Process the kudos
    process_kudos(client, sender_id, receiver_id, channel_id, thread_ts)

    # Confirm to sender via DM
    send_dm(client, sender_id, messages.format_success_ephemeral(receiver_id))


# ============================================================
# SLASH COMMAND: /kudos @user or /kudos me
# ============================================================

@app.command("/kudos")
def handle_kudos_command(ack, command, client, respond):
    """
    Handle the /kudos slash command.
    
    Usage:
    - /kudos @user - Give kudos to someone
    - /kudos me - View your personal kudos stats
    """
    ack()

    sender_id = command["user_id"]
    text = command.get("text", "").strip()
    channel_id = command["channel_id"]

    # Handle "kudos me"
    if text.lower() == "me":
        handle_kudos_me(client, sender_id)
        respond("Check your DMs for your kudos stats!")
        return

    # Extract receiver from mention
    receiver_id = extract_user_id(text)

    if not receiver_id:
        respond(messages.format_error_no_user())
        return

    if receiver_id == sender_id:
        respond(messages.format_error_self_kudos())
        return

    # Process kudos (no thread context from slash command)
    process_kudos(client, sender_id, receiver_id, channel_id, None)
    respond(messages.format_success_ephemeral(receiver_id))


def handle_kudos_me(client, user_id: str):
    """Handle /kudos me - show personal kudos stats via DM."""
    stats = db.get_user_stats(user_id)

    dm_text = messages.format_kudos_me_dm(
        month_count=stats["month_count"],
        all_time_count=stats["all_time_count"],
        recent_kudos=stats["recent_kudos"],
    )

    send_dm(client, user_id, dm_text)


def main():
    """Initialize database and start the bot."""
    db.init_db()

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
