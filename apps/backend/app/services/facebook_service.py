from typing import Any


def publish_facebook_post(*, config: dict[str, Any], share_pack: dict[str, Any]) -> dict[str, Any]:
    page_name = str(config.get("page_name") or config.get("page_id") or "page Facebook").strip()
    simulated = not bool(config.get("graph_api_url") and config.get("access_token"))
    return {
        "status": "success",
        "message": (
            f"Publication Facebook simulée sur {page_name}."
            if simulated
            else f"Publication Facebook préparée pour {page_name} via Graph API."
        ),
        "details": {
            "simulated": simulated,
            "page_name": page_name,
            "preview_text": share_pack.get("facebook_text"),
            "public_url": share_pack.get("public_url"),
            "graph_api_ready": bool(config.get("graph_api_url")),
        },
    }
