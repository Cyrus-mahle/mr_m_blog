from django.conf import settings
from django.db import models
from django.urls import reverse


class Post(models.Model):
    """One blog post written by a registered user."""

    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts"
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("blog_detail", args=[self.pk])

    @property
    def author_name(self):
        return self.author.get_full_name() or self.author.get_username()

    @property
    def was_edited(self):
        return (self.updated - self.created).total_seconds() > 60

    def can_be_managed_by(self, user):
        """Authorization: only the author or an administrator may edit or delete."""
        return bool(
            user.is_authenticated and (user.pk == self.author_id or user.is_staff)
        )


class ContactMessage(models.Model):
    """A message sent from the Contact page (read it in the admin)."""

    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=150)
    message = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.subject} ({self.email})"