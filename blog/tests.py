from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import ContactMessage, Post

TEST_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


@override_settings(
    CACHES=TEST_CACHE,
    ALLOWED_HOSTS=["testserver"],
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
)
class BaseTest(TestCase):
    def setUp(self):
        cache.clear()
        self.alice = User.objects.create_user("alice", "alice@example.com", "S3cure-pass-123")
        self.bob = User.objects.create_user("bob", "bob@example.com", "S3cure-pass-123")
        self.admin = User.objects.create_user(
            "boss", "boss@example.com", "S3cure-pass-123", is_staff=True, is_superuser=True
        )
        self.post = Post.objects.create(title="Alice post", content="Hello", author=self.alice)


class PublicPageTests(BaseTest):
    def test_public_pages_open(self):
        for name in ["home", "about", "blog_list", "contact", "register", "login", "terms"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertEqual(self.client.get(self.post.get_absolute_url()).status_code, 200)

    def test_search(self):
        Post.objects.create(title="Django security", content="x", author=self.bob)
        response = self.client.get(reverse("blog_list"), {"q": "security"})
        self.assertContains(response, "Django security")
        self.assertNotContains(response, "Alice post")

    def test_security_headers(self):
        response = self.client.get(reverse("home"))
        self.assertIn("frame-ancestors 'none'", response["Content-Security-Policy"])
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")


class AccountTests(BaseTest):
    def test_register_creates_user_and_logs_in(self):
        response = self.client.post(reverse("register"), {
            "username": "newuser", "email": "new@example.com",
            "password1": "Another-Str0ng-pass", "password2": "Another-Str0ng-pass",
            "accept_terms": "on",
        })
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(User.objects.filter(username="newuser").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_duplicate_email_rejected(self):
        response = self.client.post(reverse("register"), {
            "username": "other", "email": "ALICE@example.com",
            "password1": "Another-Str0ng-pass", "password2": "Another-Str0ng-pass",
            "accept_terms": "on",
        })
        self.assertContains(response, "already exists")
        self.assertFalse(User.objects.filter(username="other").exists())

    def test_register_honeypot(self):
        self.client.post(reverse("register"), {
            "username": "bot", "email": "bot@example.com",
            "password1": "Another-Str0ng-pass", "password2": "Another-Str0ng-pass",
            "accept_terms": "on", "website": "http://spam.example",
        })
        self.assertFalse(User.objects.filter(username="bot").exists())

    def test_login_is_throttled(self):
        for _ in range(5):
            self.client.post(reverse("login"), {"username": "alice", "password": "wrong"})
        response = self.client.post(reverse("login"), {"username": "alice", "password": "S3cure-pass-123"})
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, "Too many failed attempts", status_code=429)

    def test_login_works(self):
        response = self.client.post(reverse("login"), {"username": "alice", "password": "S3cure-pass-123"})
        self.assertEqual(response.status_code, 302)


class PostTests(BaseTest):
    def test_new_post_needs_login(self):
        response = self.client.get(reverse("post_create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_create_sets_author_from_session(self):
        self.client.force_login(self.bob)
        self.client.post(reverse("post_create"), {"title": "Bob post", "content": "Text", "author": self.alice.pk})
        self.assertEqual(Post.objects.get(title="Bob post").author, self.bob)

    def test_author_can_edit_and_delete(self):
        self.client.force_login(self.alice)
        self.client.post(reverse("post_edit", args=[self.post.pk]), {"title": "Changed", "content": "New"})
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, "Changed")
        self.client.post(reverse("post_delete", args=[self.post.pk]))
        self.assertFalse(Post.objects.filter(pk=self.post.pk).exists())

    def test_other_user_cannot_edit_or_delete(self):
        self.client.force_login(self.bob)
        self.assertEqual(self.client.get(reverse("post_edit", args=[self.post.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("post_delete", args=[self.post.pk])).status_code, 403)
        self.assertTrue(Post.objects.filter(pk=self.post.pk).exists())

    def test_admin_can_edit_and_delete_any_post(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("post_edit", args=[self.post.pk])).status_code, 200)
        self.client.post(reverse("post_delete", args=[self.post.pk]))
        self.assertFalse(Post.objects.filter(pk=self.post.pk).exists())

    def test_delete_needs_post_method(self):
        self.client.force_login(self.alice)
        self.assertEqual(self.client.get(reverse("post_delete", args=[self.post.pk])).status_code, 405)

    def test_buttons_only_for_allowed_users(self):
        url = self.post.get_absolute_url()
        self.assertNotContains(self.client.get(url), "Delete post")
        self.client.force_login(self.bob)
        self.assertNotContains(self.client.get(url), "Delete post")
        self.client.force_login(self.alice)
        self.assertContains(self.client.get(url), "Delete post")

    def test_my_posts_shows_only_own(self):
        Post.objects.create(title="Bob private-ish", content="x", author=self.bob)
        self.client.force_login(self.alice)
        response = self.client.get(reverse("my_posts"))
        self.assertContains(response, "Alice post")
        self.assertNotContains(response, "Bob private-ish")

    def test_script_in_post_is_escaped(self):
        evil = Post.objects.create(
            title="<script>alert(1)</script>",
            content="## <b>big</b>\n\n<script>alert('Hacked')</script>\n\n- <img src=x onerror=alert(1)>",
            author=self.alice,
        )
        for url in (reverse("blog_list"), reverse("home"), evil.get_absolute_url()):
            response = self.client.get(url)
            self.assertNotContains(response, "<script>alert")
            self.assertNotContains(response, "<img src=x")
        self.assertContains(self.client.get(evil.get_absolute_url()), "&lt;script&gt;")


class ContactTests(BaseTest):
    data = {"name": "Sam", "email": "sam@example.com", "subject": "Hi", "message": "Hello there"}

    def test_contact_saves_message(self):
        self.client.post(reverse("contact"), self.data)
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_contact_honeypot_is_not_saved(self):
        self.client.post(reverse("contact"), {**self.data, "website": "http://spam.example"})
        self.assertEqual(ContactMessage.objects.count(), 0)


class SeedCommandTests(BaseTest):
    def test_first_post_by_admin(self):
        call_command("seed_first_post", username="boss", stdout=open("/dev/null", "w"))
        post = Post.objects.get(title="Coding the right way in the age of AI")
        self.assertEqual(post.author, self.admin)
        self.assertIn("Security is priority one", post.content)
        self.assertEqual(post.author_name, "Nyakama Mahle")