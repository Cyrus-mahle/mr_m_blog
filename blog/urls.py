from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("blogs/", views.blog_list, name="blog_list"),
    path("blogs/new/", views.post_create, name="post_create"),
    path("blogs/<int:pk>/", views.blog_detail, name="blog_detail"),
    path("blogs/<int:pk>/edit/", views.post_edit, name="post_edit"),
    path("blogs/<int:pk>/delete/", views.post_delete, name="post_delete"),
    path("my-posts/", views.my_posts, name="my_posts"),
    path("contact/", views.contact, name="contact"),
    path("register/", views.register, name="register"),
    path("terms/", views.terms, name="terms"),
]