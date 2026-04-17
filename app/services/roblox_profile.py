from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw

from app.services.image_cache import ImageCache


USERS_BY_USERNAME_URL = "https://users.roblox.com/v1/usernames/users"
HEADSHOT_URL_TEMPLATE = (
    "https://thumbnails.roblox.com/v1/users/avatar-headshot"
    "?userIds={user_id}&size=150x150&format=Png&isCircular=false"
)


@dataclass
class RobloxProfile:
    username: str
    display_name: str
    user_id: str
    avatar_url: str
    avatar_path: str


class RobloxProfileService:
    def __init__(self, image_cache: ImageCache):
        self.image_cache = image_cache

    def fetch_profile(self, username: str) -> RobloxProfile:
        username = username.strip()
        if not username:
            raise ValueError("Roblox username is empty.")
        user_payload = self._post_json(
            USERS_BY_USERNAME_URL,
            {"usernames": [username], "excludeBannedUsers": False},
        )
        users = user_payload.get("data", [])
        if not users:
            raise ValueError(f'Roblox user "{username}" was not found.')
        user = users[0]
        user_id = str(user["id"])
        display_name = str(user.get("displayName") or user.get("name") or username)
        canonical_username = str(user.get("name") or username)

        headshot_payload = self._get_json(HEADSHOT_URL_TEMPLATE.format(user_id=user_id))
        data = headshot_payload.get("data", [])
        if not data or not data[0].get("imageUrl"):
            raise ValueError("Roblox avatar headshot was unavailable.")
        avatar_url = str(data[0]["imageUrl"])
        raw_path = self.image_cache.cache_remote_file(avatar_url, f"roblox_{user_id}.png")
        circular_path = self._create_circular_avatar(Path(raw_path), user_id=user_id)
        return RobloxProfile(
            username=canonical_username,
            display_name=display_name,
            user_id=user_id,
            avatar_url=avatar_url,
            avatar_path=str(circular_path),
        )

    def _post_json(self, url: str, payload: dict) -> dict:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))

    def _get_json(self, url: str) -> dict:
        with urlopen(url, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))

    def _create_circular_avatar(self, source_path: Path, *, user_id: str) -> Path:
        image = Image.open(source_path).convert("RGBA").resize((88, 88), Image.Resampling.LANCZOS)
        mask = Image.new("L", (88, 88), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 88, 88), fill=255)
        output = Image.new("RGBA", (88, 88), (0, 0, 0, 0))
        output.paste(image, (0, 0), mask)
        target = self.image_cache.cache_dir / f"roblox_{user_id}_circle.png"
        output.save(target)
        return target
