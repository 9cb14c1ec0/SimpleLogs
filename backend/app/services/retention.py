from datetime import datetime, timedelta, timezone
from app.models import Team, Log


class RetentionService:
    @staticmethod
    async def cleanup_expired_logs():
        """Delete logs older than their team's retention period."""
        teams = await Team.filter(retention_days__isnull=False)

        for team in teams:
            if team.retention_days is None:
                continue

            cutoff = datetime.now(timezone.utc) - timedelta(days=team.retention_days)
            deleted = await Log.filter(
                team=team,
                created_at__lt=cutoff
            ).delete()

            if deleted:
                print(f"Deleted {deleted} expired logs for team {team.name}")
