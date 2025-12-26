from django.core.management.base import BaseCommand
from tracker.models import Message

class Command(BaseCommand):
    help = "List all messages between all users"

    def handle(self, *args, **options):
        qs = (
            Message.objects
            .select_related("sender", "conversation__user1", "conversation__user2")
            .order_by("created_at")
        )

        self.stdout.write("-" * 100)
        for m in qs:
            conv = m.conversation
            self.stdout.write(
                f"[{m.created_at:%Y-%m-%d %H:%M:%S}] "
                f"{m.sender.username} "
                f"({conv.user1.username} ↔ {conv.user2.username}): "
                f"{m.body}"
            )
        self.stdout.write("-" * 100)
        self.stdout.write(f"Total messages: {qs.count()}")
