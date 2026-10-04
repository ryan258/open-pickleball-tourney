from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from tourney.models import Organization, Membership, Event, Court, Division
from tourney import services

class Command(BaseCommand):
    help = "Create an idempotent synthetic 32-player, four-division, 24-match local demo. Never resets existing data."
    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG or not settings.DEMO_MODE:
            raise CommandError("Run ./tour demo to use the isolated local demo database.")
        user, created = get_user_model().objects.get_or_create(username="local-demo-organizer", defaults={"email": "organizer@example.invalid"})
        if created:
            user.set_unusable_password(); user.save()
        if Event.objects.filter(slug="community-court-day").exists():
            self.stdout.write("Demo already exists; all current work was preserved.")
            return
        org = Organization.objects.create(name="The Neighborhood Pickleball Club", contact_email="organizer@example.invalid")
        Membership.objects.create(organization=org, user=user)
        now = timezone.now()
        event = Event.objects.create(organization=org, slug="community-court-day", title="The Saturday Social", summary="Four courts, familiar faces, and a little friendly competition. A synthetic community doubles tournament you can run from the desk.",
            start_at=now-timedelta(hours=1), end_at=now+timedelta(hours=8), registration_open=now-timedelta(days=7), registration_close=now+timedelta(hours=7), status="published",
            venue="Neighborhood Courts", address="Example Park · Demo venue", contact_email=org.contact_email, accessibility="Step-free court access and a shaded rest area in this synthetic example. Ask the desk for extra rest.", is_demo=True)
        for i in range(1,5):
            Court.objects.create(event=event, name=f"Court {i}", opens_at=event.start_at, closes_at=event.end_at)
        names = ["Morning Crew", "Kitchen Regulars", "Weekend Rally", "Sunset Social"]
        for di, name in enumerate(names):
            division = Division.objects.create(event=event, name=name, capacity=4)
            for team in range(4):
                people = [{"name": f"Demo Player {di*8+team*2+p+1:02}", "email": f"player{di*8+team*2+p+1:02}@example.invalid", "birth_date": "1990-01-01", "skill": "3.0", "accepted": True} for p in range(2)]
                services.register(event.id, user, {"division": str(division.id), "label": f"{name} {team+1}", "people": people, "assisted": True, "policy_version": 1, "send_notices": False})
            division.refresh_from_db()
            inputs = services.draw_inputs(division)
            services.lock_draw(event.id, user, {"division": str(division.id), "preview_digest": services.digest(inputs)})
        # An empty event supports practicing creation/registration without disturbing the pilot roster.
        practice = Event.objects.create(organization=org, slug="next-week-rally", title="Next Week's Rally", summary="An open practice event for trying registration and partner invitations with synthetic contacts.",
            start_at=now+timedelta(days=7), end_at=now+timedelta(days=7,hours=6), registration_open=now-timedelta(days=1), registration_close=now+timedelta(days=6), status="published",
            venue="Community Courts", address="Example Greenway · Demo venue", contact_email=org.contact_email, is_demo=True)
        Court.objects.create(event=practice, name="Court 1", opens_at=practice.start_at, closes_at=practice.end_at)
        Division.objects.create(event=practice, name="Friendly doubles", capacity=4)
        self.stdout.write("Created 32 synthetic adults, 16 teams, four divisions, four courts and 24 matches. Players await check-in; scores are empty.")
