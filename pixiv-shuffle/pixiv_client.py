import time
import logging
from pixivpy3 import AppPixivAPI

logger = logging.getLogger(__name__)

_api: AppPixivAPI | None = None


def get_api() -> AppPixivAPI:
    global _api
    if _api is None:
        raise RuntimeError("Pixiv API not initialized. Call init_api() first.")
    return _api


def init_api(refresh_token: str) -> AppPixivAPI:
    global _api
    _api = AppPixivAPI()
    _api.auth(refresh_token=refresh_token)
    logger.info("Pixiv API authenticated.")
    return _api


# ---------- Following ----------

def fetch_all_following(user_id: str | None = None) -> list[dict]:
    """Fetch all users the authenticated user follows."""
    api = get_api()
    if user_id is None:
        user_id = str(api.user_id)
    results = []
    next_url = None

    # user_id="0" means self
    resp = api.user_following(user_id, restrict="public")
    while True:
        if "error" in resp:
            logger.error("Error fetching following: %s", resp["error"])
            break
        for user_preview in resp.get("user_previews", []):
            u = user_preview["user"]
            results.append({"id": str(u["id"]), "name": u["name"]})
        next_url = resp.get("next_url")
        if not next_url:
            break
        time.sleep(1)
        resp = api.no_auth_requests_handler(next_url)

    logger.info("Fetched %d followed users.", len(results))
    return results


# ---------- User illusts ----------

def fetch_user_illusts(user_id: str, max_works: int = 100) -> list[dict]:
    """Fetch up to max_works illusts for a given user."""
    api = get_api()
    results = []
    offset = 0

    while len(results) < max_works:
        resp = api.user_illusts(user_id, type="illust", offset=offset)
        if "error" in resp:
            logger.error("Error fetching illusts for user %s: %s", user_id, resp["error"])
            break

        illusts = resp.get("illusts", [])
        if not illusts:
            break

        for illust in illusts:
            results.append(_parse_illust(illust))

        if not resp.get("next_url"):
            break

        offset += len(illusts)
        time.sleep(1)

    return results[:max_works]


def _parse_illust(illust: dict) -> dict:
    image_url = ""
    meta = illust.get("meta_single_page", {})
    if illust.get("meta_pages"):
        image_url = illust["meta_pages"][0]["image_urls"].get("medium", "")
    else:
        image_url = illust.get("image_urls", {}).get("medium", "")

    work_id = str(illust["id"])
    return {
        "id": work_id,
        "author_id": str(illust["user"]["id"]),
        "title": illust.get("title", ""),
        "image_url": image_url,
        "page_url": f"https://www.pixiv.net/artworks/{work_id}",
        "created_at": illust.get("create_date", ""),
    }
