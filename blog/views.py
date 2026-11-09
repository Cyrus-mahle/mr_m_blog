from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ContactForm, PostForm, RegisterForm
from .models import Post
from .security import client_ip, hit, over_limit, reset, throttle_key


# ---------------------------------------------------------------- public pages
def home(request):
    latest_posts = Post.objects.select_related("author")[:3]
    return render(request, "blog/home.html", {"latest_posts": latest_posts})


def about(request):
    return render(request, "blog/about.html")


def terms(request):
    return render(request, "blog/terms.html")


def blog_list(request):
    q = request.GET.get("q", "").strip()[:100]
    posts = Post.objects.select_related("author")
    if q:
        posts = posts.filter(Q(title__icontains=q) | Q(content__icontains=q))  # ORM = safe
    page_obj = Paginator(posts, 5).get_page(request.GET.get("page"))
    return render(request, "blog/blogs.html", {"page_obj": page_obj, "q": q})


def blog_detail(request, pk):
    post = get_object_or_404(Post.objects.select_related("author"), pk=pk)
    return render(
        request,
        "blog/blog_detail.html",
        {"post": post, "can_manage": post.can_be_managed_by(request.user)},
    )


def contact(request):
    key = throttle_key("contact", client_ip(request))
    if request.method == "POST":
        if over_limit(key, 10):
            messages.error(request, "Too many messages from this address. Try again later.")
            return render(request, "blog/contact.html", {"form": ContactForm()}, status=429)
        form = ContactForm(request.POST)
        if form.is_valid():
            if not form.cleaned_data.get("website"):  # empty trap field = a real person
                form.save()
                hit(key, 3600)
            messages.success(request, "Thank you! Your message was sent.")
            return redirect("contact")
    else:
        form = ContactForm()
    return render(request, "blog/contact.html", {"form": form})


# ---------------------------------------------------------------- accounts
class ThrottledLoginView(LoginView):
    """Django does not slow down password guessing. This view does."""

    user_attempts = 5
    ip_attempts = 50
    window = 15 * 60  # seconds

    def _keys(self):
        ip = client_ip(self.request)
        username = self.request.POST.get("username", "").strip().lower()[:150]
        return throttle_key("login-user", ip, username), throttle_key("login-ip", ip)

    def post(self, request, *args, **kwargs):
        user_key, ip_key = self._keys()
        if over_limit(user_key, self.user_attempts) or over_limit(ip_key, self.ip_attempts):
            context = self.get_context_data(form=self.get_form_class()(request=request))
            context["throttled"] = True
            return self.render_to_response(context, status=429)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        user_key, ip_key = self._keys()
        hit(user_key, self.window)
        hit(ip_key, self.window)
        return super().form_invalid(form)

    def form_valid(self, form):
        reset(self._keys()[0])
        return super().form_valid(form)


def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    key = throttle_key("register", client_ip(request))
    if request.method == "POST":
        if over_limit(key, 30):
            messages.error(request, "Too many sign-up attempts. Try again later.")
            return render(request, "registration/registration.html", {"form": RegisterForm()}, status=429)
        hit(key, 3600)
        form = RegisterForm(request.POST)
        if form.is_valid():
            if form.cleaned_data.get("website"):  # bot trap
                return redirect("home")
            user = form.save()  # the password is stored hashed
            login(request, user)
            messages.success(request, "Welcome! Your account was created.")
            return redirect("home")
    else:
        form = RegisterForm()
    return render(request, "registration/registration.html", {"form": form})


# ---------------------------------------------------------------- posts
@login_required
def my_posts(request):
    posts = request.user.posts.all()
    page_obj = Paginator(posts, 10).get_page(request.GET.get("page"))
    return render(request, "blog/my_posts.html", {"page_obj": page_obj})


@login_required
def post_create(request):
    key = throttle_key("post-create", request.user.pk)
    if request.method == "POST":
        if over_limit(key, 20):
            messages.error(request, "You have reached today's limit of new posts.")
            return render(request, "blog/post_form.html", {"form": PostForm(), "heading": "New post"}, status=429)
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user  # set by the server, not by the user
            post.save()
            hit(key, 24 * 3600)
            messages.success(request, "Your post was published.")
            return redirect(post)
    else:
        form = PostForm()
    return render(request, "blog/post_form.html", {"form": form, "heading": "New post"})


@login_required
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if not post.can_be_managed_by(request.user):
        raise PermissionDenied  # only the author or an administrator
    if request.method == "POST":
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "Your post was updated.")
            return redirect(post)
    else:
        form = PostForm(instance=post)
    return render(request, "blog/post_form.html", {"form": form, "heading": "Edit post"})


@login_required
@require_POST  # deleting is allowed with POST only
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if not post.can_be_managed_by(request.user):
        raise PermissionDenied
    post.delete()
    messages.success(request, "The post was deleted.")
    return redirect("blog_list")