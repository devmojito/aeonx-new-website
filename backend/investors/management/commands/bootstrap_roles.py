"""Create the IR team's permission groups.

Two roles, because a listed company's filings need a second pair of eyes but a
full draft/review workflow is more process than a three-person IR team will follow:

  IR Contributor — add and edit documents, but cannot publish or delete. Work is
                   staged with "published" off and is invisible to the public.
  IR Publisher   — everything a contributor can do, plus publish and delete.

Idempotent: safe to re-run after every deploy.
"""
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from investors.models import Category, Document, Section

CONTRIBUTOR = "IR Contributor"
PUBLISHER = "IR Publisher"


class Command(BaseCommand):
    help = "Create/refresh the IR Contributor and IR Publisher groups."

    def handle(self, *args, **options):
        def perms(model, actions):
            ct = ContentType.objects.get_for_model(model)
            return list(
                Permission.objects.filter(
                    content_type=ct,
                    codename__in=[f"{a}_{model._meta.model_name}" for a in actions],
                )
            )

        contributor = perms(Document, ["add", "change", "view"]) + \
            perms(Category, ["view"]) + perms(Section, ["view"])

        publisher = perms(Document, ["add", "change", "view", "delete"]) + \
            perms(Category, ["add", "change", "view"]) + perms(Section, ["view"])

        for name, permissions in ((CONTRIBUTOR, contributor), (PUBLISHER, publisher)):
            group, created = Group.objects.get_or_create(name=name)
            group.permissions.set(permissions)
            self.stdout.write(
                self.style.SUCCESS(
                    f"{'created' if created else 'updated'} {name} "
                    f"({len(permissions)} permissions)"
                )
            )

        self.stdout.write(
            "\nGive a team member access with: Admin > Users > Add user, tick "
            '"Staff status", then assign one of these groups.\n'
            "Staff status only opens the admin — the group decides what they can do there."
        )
