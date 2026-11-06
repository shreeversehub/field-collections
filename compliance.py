from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
BLOCKED = ("arrest", "police", "jail", "threat", "expose", "पुलिस", "जेल", "धमकी")
TEMPLATES = {
    "en": "Dear {name}, Rs {amt} is overdue on loan {loan}. Please pay {when}. Thank you.",
    "hi": "प्रिय {name}, लोन {loan} पर Rs {amt} बकाया है। कृपया {when} भुगतान करें। धन्यवाद।",
}


def can_contact(now=None):
    """RBI window: borrower contact only 8 am to 7 pm IST."""
    return 8 <= (now or datetime.now(IST)).astimezone(IST).hour < 19


def safe(text):
    return not any(w in text.lower() for w in BLOCKED)
