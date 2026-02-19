from app.services.partitions import cleanup_expired_partitions


class RetentionService:
    @staticmethod
    async def cleanup_expired_logs():
        """Drop expired monthly partitions and delete partial-month rows."""
        await cleanup_expired_partitions()
