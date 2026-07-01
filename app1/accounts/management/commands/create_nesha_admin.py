from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import AppUserProfile


class Command(BaseCommand):
    help = "Create a NESHA system administrator account (DB/manual flow)."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Admin email address")
        parser.add_argument("--password", required=True, help="Admin password")
        parser.add_argument("--full-name", required=True, help="Admin full name")
        parser.add_argument("--phone", required=True, help="Unique phone number")
        parser.add_argument("--username", required=False, help="Optional username override")

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        email = options["email"].strip().lower()
        password = options["password"]
        full_name = options["full_name"].strip()
        phone = options["phone"].strip()
        username = (options.get("username") or email.split("@", 1)[0]).strip()

        if not email:
            raise CommandError("Email is required.")
        if not full_name:
            raise CommandError("Full name is required.")
        if len(password) < 8:
            raise CommandError("Password must be at least 8 characters.")

        if User.objects.filter(email__iexact=email).exists():
            raise CommandError(f"A user with email {email} already exists.")

        if User.objects.filter(username__iexact=username).exists():
            base = username
            index = 1
            while User.objects.filter(username__iexact=f"{base}_{index}").exists():
                index += 1
            username = f"{base}_{index}"

        if AppUserProfile.objects.filter(phone_number=phone).exists():
            raise CommandError("Phone number already exists on another account.")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=True,
            is_superuser=False,
        )

        name_parts = full_name.split(maxsplit=1)
        user.first_name = name_parts[0]
        user.last_name = name_parts[1] if len(name_parts) > 1 else ""
        user.save(update_fields=["first_name", "last_name"])

        AppUserProfile.objects.create(
            user=user,
            full_name=full_name,
            phone_number=phone,
            role=AppUserProfile.Role.SYSTEM_ADMIN,
        )

        self.stdout.write(self.style.SUCCESS(f"NESHA admin created successfully: {email}"))
        self.stdout.write(f"Username: {username}")
