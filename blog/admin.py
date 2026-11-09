from django.contrib import admin

from .models import ContactMessage, Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "created", "updated")
    list_filter = ("author", "created")
    search_fields = ("title", "content")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "name", "email", "created", "is_read")
    list_filter = ("is_read",)
    readonly_fields = ("name", "email", "subject", "message", "created")

    def has_add_permission(self, request):
        return False  # messages come only from the Contact page