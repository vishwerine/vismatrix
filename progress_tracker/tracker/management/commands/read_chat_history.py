from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from tracker.models import Conversation

class Command(BaseCommand):
    help = "Print full message history between two users"

    def add_arguments(self, parser):
        parser.add_argument("user_a", type=str, help="Username of first user")
        parser.add_argument("user_b", type=str, help="Username of second user")

    def handle(self, *args, **options):
        user_a = options["user_a"]
        user_b = options["user_b"]

        try:
            uA = User.objects.get(username=user_a)
            uB = User.objects.get(username=user_b)
        except User.DoesNotExist:
            raise CommandError("One or both users do not exist")

        u1, u2 = Conversation.normalize_pair(uA, uB)

        try:
            conversation = Conversation.objects.get(user1=u1, user2=u2)
        except Conversation.DoesNotExist:
            raise CommandError("No conversation exists between these users")

        messages = (
            conversation.messages
            .select_related("sender")
            .order_by("created_at")
        )

        self.stdout.write(
            f"\nConversation #{conversation.id}: {uA.username} ↔ {uB.username}"
        )
        self.stdout.write("-" * 80)

        for m in messages:
            ts = m.created_at.strftime("%Y-%m-%d %H:%M:%S")
            self.stdout.write(f"[{ts}] {m.sender.username}: {m.body}")

        self.stdout.write("-" * 80)
        self.stdout.write(f"Total messages: {messages.count()}")
