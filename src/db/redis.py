import redis
from src.config import Config
from datetime import timedelta

class RedisService:
    def __init__(self):
        self.client = redis.Redis(
            host=Config.REDIS_HOST,
            port=Config.REDIS_PORT,
            db=Config.REDIS_DB,
            password=Config.REDIS_PASSWORD,
            decode_responses=True
        )

    async def add_token(self, user_id: str, token: str, expires: int):
        """Store token in Redis with expiration"""
        self.client.setex(f"user:{user_id}:{token}", expires, "valid")

    async def revoke_token(self, user_id: str, token: str):
        """Remove specific token from Redis"""
        self.client.delete(f"user:{user_id}:{token}")

    async def revoke_all_tokens(self, user_id: str):
        """Remove all tokens for a user"""
        keys = self.client.keys(f"user:{user_id}:*")
        if keys:
            self.client.delete(*keys)

    async def is_token_valid(self, user_id: str, token: str) -> bool:
        """Check if token exists in Redis"""
        return bool(self.client.exists(f"user:{user_id}:{token}"))

redis_service = RedisService()