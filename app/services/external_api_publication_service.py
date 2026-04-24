from typing import Any

import httpx


def publish_external_api(*, config: dict[str, Any], share_pack: dict[str, Any]) -> dict[str, Any]:
    webhook_url = str(config.get("webhook_url") or "").strip()
    if not webhook_url:
        return {
            "status": "failed",
            "message": "Webhook externe non configuré.",
            "details": {"reason": "missing_webhook_url"},
        }

    payload = {
        "title": share_pack.get("title"),
        "public_url": share_pack.get("public_url"),
        "body": share_pack.get("web_body"),
    }
    try:
        response = httpx.post(webhook_url, json=payload, timeout=10.0)
        response.raise_for_status()
    except Exception as exc:
        return {
            "status": "failed",
            "message": f"Publication API externe échouée: {exc}",
            "details": {"webhook_url": webhook_url},
        }

    return {
        "status": "success",
        "message": "Publication transmise à l'API externe.",
        "details": {"webhook_url": webhook_url, "http_status": response.status_code},
    }
