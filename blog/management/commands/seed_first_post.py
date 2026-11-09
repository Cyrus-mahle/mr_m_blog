from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from blog.models import Post

TITLE = "Coding the right way in the age of AI"

CONTENT = """AI can write a working login page in thirty seconds. In the same thirty seconds it can write one that leaks your users' passwords. Working code is not the same as safe code, and the difference is your responsibility.

## Security comes before everything

Security is priority one. It comes before speed, before new features, before a clever design and before the launch date. A fast website that gets hacked has failed its users. A slower website that protects them has done its job.

If you must choose between shipping today and being secure, choose secure. Every time.

## AI is a helper, you are the developer

AI tools are useful. They are also confident when they are wrong, and they happily forget security rules. So the rules for working with AI are simple:

- Read every line before you run it.
- If you cannot explain a line, do not ship it.
- Ask the AI to review its own code for security problems, then check the answer against the official documentation yourself.
- Never paste secret keys, passwords or customer data into an AI chat.

## Habits that protect your users

Security is not one big switch. It is a set of habits, repeated on every project:

- Never trust user input. Validate every form.
- Keep secrets out of your code. Use environment variables and keep .env out of GitHub.
- Turn DEBUG off on a live website.
- Use HTTPS everywhere, with secure cookies.
- Hash passwords and limit login attempts.
- Give people only the access they need. Only the author or the administrator may edit a post.
- Keep your packages up to date.
- Test your code, then run python manage.py check --deploy before every release.

## When speed and security disagree

They will disagree. A deadline is close, a client is waiting, and the secure way takes another hour. Take the hour. A breach costs far more than an hour, and it costs your users first.

## This blog follows its own advice

This blog is built the way this post asks you to build. Passwords are hashed. Every form is protected against forgery. Post text is escaped so a script cannot run in your browser. Login attempts are limited, pages are served over HTTPS, and only authors and the administrator can change a post.

Build it right. Build it secure. Then ship it.

Nyakama Mahle
Founder, MR M"""


class Command(BaseCommand):
    help = "Create the first blog post, written by the administrator."

    def add_arguments(self, parser):
        parser.add_argument("--username", help="Administrator username (default: first superuser)")
        parser.add_argument("--name", default="Nyakama Mahle", help="Full name shown as the author")

    def handle(self, *args, **options):
        User = get_user_model()
        if options["username"]:
            author = User.objects.filter(username=options["username"]).first()
        else:
            author = User.objects.filter(is_superuser=True).order_by("pk").first()
        if author is None:
            raise CommandError("No administrator found. Run: python manage.py createsuperuser")

        if not author.get_full_name():
            first, _, last = options["name"].partition(" ")
            author.first_name, author.last_name = first, last
            author.save(update_fields=["first_name", "last_name"])

        post, created = Post.objects.get_or_create(
            title=TITLE, defaults={"content": CONTENT, "author": author}
        )
        self.stdout.write(self.style.SUCCESS(
            "First post created." if created else "First post already exists."
        ))