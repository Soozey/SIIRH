from typing import Any


def publish_internal_job(*, job_id: int, share_pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "message": "Offre rendue visible sur le portail interne.",
        "details": {
            "job_id": job_id,
            "public_url": share_pack.get("public_url"),
            "title": share_pack.get("title"),
        },
    }
