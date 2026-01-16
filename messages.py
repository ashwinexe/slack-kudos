"""
Message templates for kudos bot.
Tone: calm, human, affirming. 1 emoji max. No gamification language.
"""


def format_public_message(sender_id: str, receiver_id: str, summary: str) -> str:
    """
    Format the public kudos message for #kudos channel.
    Compact acknowledgement crediting sender and receiver.
    """
    return f"<@{sender_id}> gave kudos to <@{receiver_id}> for {summary}"


def format_private_dm(
    sender_id: str,
    summary: str,
    month_count: int,
    all_time_count: int,
) -> str:
    """
    Format the private DM sent to the kudos receiver.
    Affirming, personal, with stats.
    """
    return (
        f"Hey! <@{sender_id}> just recognized you for {summary} ✨\n\n"
        f"This month: {month_count} kudos · All-time: {all_time_count} kudos"
    )


def format_kudos_me_dm(
    month_count: int,
    all_time_count: int,
    recent_kudos: list[dict],
) -> str:
    """
    Format the /kudos me response showing personal stats.
    """
    lines = [
        f"*Your kudos*\n",
        f"This month: {month_count} · All-time: {all_time_count}\n",
    ]
    
    if recent_kudos:
        lines.append("\n*Recent*")
        for kudos in recent_kudos:
            sender_id = kudos["sender_id"]
            summary = kudos["summary"]
            lines.append(f"• <@{sender_id}>: {summary}")
    else:
        lines.append("\nNo kudos yet. They'll come!")
    
    return "\n".join(lines)


def format_error_not_in_thread() -> str:
    """Error message when /kudos is used outside a thread."""
    return "Use `/kudos @user` inside a thread to give kudos for that conversation."


def format_error_no_user() -> str:
    """Error message when no user is mentioned."""
    return "Please mention someone to give kudos to: `/kudos @user`"


def format_error_self_kudos() -> str:
    """Error message when someone tries to kudos themselves."""
    return "You can't give kudos to yourself! Recognize someone else's work."


def format_success_ephemeral(receiver_id: str) -> str:
    """Ephemeral success message shown to the sender."""
    return f"Kudos sent to <@{receiver_id}>!"
