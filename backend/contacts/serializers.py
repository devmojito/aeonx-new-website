from rest_framework import serializers

from .models import ContactSubmission, NewsletterSubscriber


class ContactSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactSubmission
        fields = [
            "kind", "company_name", "full_name", "email", "country_code",
            "phone_number", "role", "additional_information", "region",
            "type_of_engagement", "timeline", "brief_description", "source_page",
        ]

    def validate(self, attrs):
        kind = attrs.get("kind")
        # Mirrors the two panel shapes in _forminputs.html: each kind requires
        # only ITS OWN extra fields, not the other kind's -- a "Talk to AeonX"
        # submission has no Region/Timeline to be missing.
        if kind == ContactSubmission.KIND_TALK and not attrs.get("role"):
            raise serializers.ValidationError({"role": "This field is required."})
        if kind == ContactSubmission.KIND_ENQUIRY:
            for f in ("region", "type_of_engagement", "timeline"):
                if not attrs.get(f):
                    raise serializers.ValidationError({f: "This field is required."})
        return attrs


class NewsletterSubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscriber
        fields = ["email", "source_page"]
        # `email` is unique, and a repeat sign-up is a normal thing a reader does,
        # not an error to show them. The view upserts, so the uniqueness check is
        # dropped here rather than turned into a 400 they cannot act on.
        extra_kwargs = {"email": {"validators": []}}
