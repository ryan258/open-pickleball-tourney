import time
from django.core.management.base import BaseCommand
from tourney.delivery import deliver_one, maintenance

class Command(BaseCommand):
    help = "Deliver queued operational mail; interrupted/ambiguous deliveries require reconciliation."
    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--limit", type=int, default=50)
    def handle(self, *args, **options):
        try:
            while True:
                maintenance()
                count = 0
                for _ in range(max(1, min(options["limit"], 200))):
                    if not deliver_one():
                        break
                    count += 1
                if options["once"]:
                    self.stdout.write(f"Processed {count} messages. Review delivery state in the event desk.")
                    return
                time.sleep(5)
        except KeyboardInterrupt:
            return
