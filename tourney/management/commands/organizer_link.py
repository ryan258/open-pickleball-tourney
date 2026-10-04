import hashlib
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.conf import settings
from tourney.services import issue_token

class Command(BaseCommand):
    help = "Create a local operator sign-in link. Run only from the trusted server terminal; the printed URL is a credential."
    def add_arguments(self, parser):
        parser.add_argument("email")
    def handle(self, *args, **options):
        email=options["email"].strip().lower()
        try: validate_email(email)
        except ValidationError: raise CommandError("Enter a valid email address.")
        user, created=get_user_model().objects.get_or_create(username=hashlib.sha256(email.encode()).hexdigest(),defaults={"email":email})
        if created: user.set_unusable_password(); user.save()
        if not user.is_active: raise CommandError("This account is disabled.")
        raw,_=issue_token("login",email,hours=.25)
        self.stdout.write(f"Private single-use sign-in link (15 minutes): {settings.SITE_URL}/link/{raw}/")
