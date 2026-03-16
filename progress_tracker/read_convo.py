# Django shell script: print full message history between two users
# Usage:
#   python manage.py shell
#   >>> exec(open("read_chat_history.py").read())   # if you save as a file
# OR just paste directly into shell.

from django.contrib.auth.models import User
from tracker.models import Conversation  # change "tracker" to your app name if different

USERNAME_A = "alice"
USERNAME_B = "bob"

# --- Load users ---
uA = User.objects.get(username=USERNAME_A)
uB = User.objects.get(username=USERNAME_B)

# --- Retrieve conversation (read-only; no creation) ---
u1, u2 = Conversation.normalize_pair(uA, uB)

conversation = Conversation.objects.get(user1=u1, user2=u2)

# --- Fetch and print all messages in chronological order ---
qs = (
    conversation.messages
    .select_related("sender")
    .order_by("created_at")
)

print(f"\nConversation #{conversation.id}: {uA.username} ↔ {uB.username}")
print("-" * 80)

for m in qs:
    ts = m.created_at.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {m.sender.username}: {m.body}")

print("-" * 80)
print(f"Total messages: {qs.count()}\n")
