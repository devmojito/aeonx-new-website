from django.urls import path

from .views import ContactSubmissionView, NewsletterSubscribeView

urlpatterns = [
    path("contact/", ContactSubmissionView.as_view(), name="contact-submit"),
    path("newsletter/", NewsletterSubscribeView.as_view(), name="newsletter-subscribe"),
]
