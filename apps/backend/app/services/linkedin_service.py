from typing import Any


def publish_linkedin_post(*, config: dict[str, Any], share_pack: dict[str, Any]) -> dict[str, Any]:
    organization_id = str(config.get("organization_id") or "organization").strip()
    simulated = not bool(config.get("access_token") and config.get("organization_id"))
    return {
        "status": "success",
        "message": (
            f"Publication LinkedIn simulée pour l'organisation {organization_id}."
            if simulated
            else f"Publication LinkedIn préparée pour l'organisation {organization_id}."
        ),
        "details": {
            "simulated": simulated,
            "organization_id": organization_id,
            "preview_text": share_pack.get("linkedin_text"),
            "public_url": share_pack.get("public_url"),
            "api_ready": bool(config.get("access_token") and config.get("organization_id")),
        },
    }
