import datetime
import logging

# In-memory storage (resets on restart)
USERS = {}

class Database:
    def __init__(self):
        logging.info("Using in-memory database (no MongoDB, no JSON). Data will reset after restart.")

    def new_user(self, id):
        return dict(
            _id=int(id),
            join_date=datetime.date.today().isoformat(),
            file_id=None,
            caption=None,
            metadata=True,
            metadata_code="Telegram : @World_Fastest_Bots",
            format_template=None,
            ban_status=dict(
                is_banned=False,
                ban_duration=0,
                banned_on=datetime.date.max.isoformat(),
                ban_reason=''
            )
        )

    async def add_user(self, b, m):
        u = m.from_user
        if not await self.is_user_exist(u.id):
            USERS[u.id] = self.new_user(u.id)

    async def is_user_exist(self, id):
        return int(id) in USERS

    async def total_users_count(self):
        return len(USERS)

    async def get_all_users(self):
        return USERS.values()

    async def delete_user(self, user_id):
        USERS.pop(int(user_id), None)

    async def set_thumbnail(self, id, file_id):
        USERS.setdefault(int(id), self.new_user(id))["file_id"] = file_id

    async def get_thumbnail(self, id):
        return USERS.get(int(id), {}).get("file_id")

    async def set_caption(self, id, caption):
        USERS.setdefault(int(id), self.new_user(id))["caption"] = caption

    async def get_caption(self, id):
        return USERS.get(int(id), {}).get("caption")

    async def set_format_template(self, id, format_template):
        USERS.setdefault(int(id), self.new_user(id))["format_template"] = format_template

    async def get_format_template(self, id):
        return USERS.get(int(id), {}).get("format_template")

    async def set_media_preference(self, id, media_type):
        USERS.setdefault(int(id), self.new_user(id))["media_type"] = media_type

    async def get_media_preference(self, id):
        return USERS.get(int(id), {}).get("media_type")

    async def get_metadata(self, user_id):
        return USERS.get(int(user_id), {}).get("metadata", "Off")

    async def set_metadata(self, user_id, metadata):
        USERS.setdefault(int(user_id), self.new_user(user_id))["metadata"] = metadata

    async def get_title(self, user_id):
        return USERS.get(int(user_id), {}).get("title", "Encoded by @World_Fastest_Bots")

    async def set_title(self, user_id, title):
        USERS.setdefault(int(user_id), self.new_user(user_id))["title"] = title

    async def get_author(self, user_id):
        return USERS.get(int(user_id), {}).get("author", "@World_Fastest_Bots")

    async def set_author(self, user_id, author):
        USERS.setdefault(int(user_id), self.new_user(user_id))["author"] = author

    async def get_artist(self, user_id):
        return USERS.get(int(user_id), {}).get("artist", "@World_Fastest_Bots")

    async def set_artist(self, user_id, artist):
        USERS.setdefault(int(user_id), self.new_user(user_id))["artist"] = artist

    async def get_audio(self, user_id):
        return USERS.get(int(user_id), {}).get("audio", "By @World_Fastest_Bots")

    async def set_audio(self, user_id, audio):
        USERS.setdefault(int(user_id), self.new_user(user_id))["audio"] = audio

    async def get_subtitle(self, user_id):
        return USERS.get(int(user_id), {}).get("subtitle", "By @World_Fastest_Bots")

    async def set_subtitle(self, user_id, subtitle):
        USERS.setdefault(int(user_id), self.new_user(user_id))["subtitle"] = subtitle

    async def get_video(self, user_id):
        return USERS.get(int(user_id), {}).get("video", "Encoded By @World_Fastest_Bots")

    async def set_video(self, user_id, video):
        USERS.setdefault(int(user_id), self.new_user(user_id))["video"] = video


# Global instance
codeflixbots = Database()
