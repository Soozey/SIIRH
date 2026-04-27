from typing import Any


def publish_email_campaign(*, config: dict[str, Any], share_pack: dict[str, Any], recipient_emails: list[str]) -> dict[str, Any]:
    sender_email = str(config.get("sender_email") or "recrutement@localhost").strip()
    configured_audience = [str(item).strip() for item in config.get("audience_emails", []) if str(item).strip()]
    final_recipients = sorted({*recipient_emails, *configured_audience})
    return {
        "status": "success",
        "message": f"Campagne e-mail préparée pour {len(final_recipients)} destinataire(s).",
        "details": {
            "sender_email": sender_email,
            "recipient_count": len(final_recipients),
            "recipients_preview": final_recipients[:20],
            "subject": share_pack.get("email_subject"),
        },
    }
