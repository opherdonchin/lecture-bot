def build_opening_message(lecture_package: dict) -> str:
    title = lecture_package["config"].get("title", lecture_package["lecture_id"])
    return (
        f"Welcome to the review bot for {title}. "
        "I’ll work with you through a short conceptual review of this lecture. "
        "You can ask for your current grade or a final report at any time. "
        "Let’s begin: what do you think was one central idea of this lecture?"
    )


def generate_reply(user_message: str, state: dict) -> tuple[str, dict]:
    reply = f"You said: {user_message}. Tell me more."
    state["turn_count"] += 1
    return reply, state