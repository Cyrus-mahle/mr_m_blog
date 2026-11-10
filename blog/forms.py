from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import ContactMessage, Post


def honeypot_field():
    """A hidden trap field. People never see it; spam bots fill it in."""
    return forms.CharField(
        required=False,
        label="Leave this field empty",
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, max_length=254)
    accept_terms = forms.BooleanField(
        required=True, label="I accept the Terms of Use and Privacy Policy"
    )
    website = honeypot_field()
    field_order = ["username", "email", "password1", "password2", "accept_terms", "website"]

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class PostForm(forms.ModelForm):
    title = forms.CharField(max_length=200)
    content = forms.CharField(
        max_length=20000,
        widget=forms.Textarea(attrs={"rows": 16}),
        help_text="Blank line = new paragraph. Start a line with ## for a heading, or with - for a list.",
    )

    class Meta:
        model = Post
        fields = ("title", "content")  # the author is set in the view, never by the user

    def clean_title(self):
        return self.cleaned_data["title"].strip()

    def clean_content(self):
        return self.cleaned_data["content"].strip()


class ContactForm(forms.ModelForm):
    message = forms.CharField(max_length=5000, widget=forms.Textarea(attrs={"rows": 7}))
    website = honeypot_field()

    class Meta:
        model = ContactMessage
        fields = ("name", "email", "subject", "message")