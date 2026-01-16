"""
Devfolio Kudos Bot - Main application.
A lightweight Slack bot for giving and tracking kudos.
"""

import os
import re
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


def extract_user_id(text: str) -> str | None:
    """Extract the first user ID from a text containing @mentions."""
    match = USER_MENTION_PATTERN.search(text)
    return match.group(1) if match else None


def fetch_thread_messages(client, channel_id: str, thread_ts: str) -> list[str]:
    """Fetch all messages from a thread."""
    try:
        result = client.conversations_replies(
            channel=channel_id,
            ts=thread_ts,
            limit=50,  # Reasonable limit for context
        )
        # Extract just the text from each message, skip bot messages
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
        # Open a DM channel with the user
        result = client.conversations_open(users=[user_id])
        dm_channel = result["channel"]["id"]
        
        # Send the message
        client.chat_postMessage(channel=dm_channel, text=text)
    except Exception as e:
        print(f"Error sending DM to {user_id}: {e}")


@app.command("/kudos")
def handle_kudos_command(ack, command, client, respond):
    """
    Handle the /kudos slash command.
    
    Usage:
    - /kudos @user (in a thread) - Give kudos to someone for the thread's work
    - /kudos me - View your personal kudos stats
    """
    ack()  # Acknowledge the command immediately
    
    sender_id = command["user_id"]
    text = command.get("text", "").strip()
    channel_id = command["channel_id"]
    
    # Check if this is a "kudos me" request
    if text.lower() == "me":
        handle_kudos_me(client, sender_id)
        return
    
    # Extract the receiver from the mention
    receiver_id = extract_user_id(text)
    
    if not receiver_id:
        respond(messages.format_error_no_user())
        return
    
    # Prevent self-kudos
    if receiver_id == sender_id:
        respond(messages.format_error_self_kudos())
        return
    
    # Check if command was used in a thread
    thread_ts = command.get("thread_ts")
    
    if not thread_ts:
        # Not in a thread - still allow it but with generic message
        summary = "their great work"
    else:
        # Fetch thread messages and summarize
        thread_messages = fetch_thread_messages(client, channel_id, thread_ts)
        summary = summarize_thread(thread_messages)
    
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
            client.chat_postMessage(
                channel=KUDOS_CHANNEL_ID,
                text=public_message,
            )
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
    
    # Ephemeral confirmation to sender
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
    # Initialize the database
    db.init_db()
    
    # Check if we should use Socket Mode (development) or HTTP (production)
    app_token = os.environ.get("SLACK_APP_TOKEN")
    
    if app_token:
        # Socket Mode for development
        print("Starting bot in Socket Mode...")
        handler = SocketModeHandler(app, app_token)
        handler.start()
    else:
        # HTTP mode for production
        port = int(os.environ.get("PORT", 3000))
        print(f"Starting bot in HTTP mode on port {port}...")
        app.start(port=port)


if __name__ == "__main__":
    main()
