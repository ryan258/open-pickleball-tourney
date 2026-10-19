import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tarfile
import tempfile
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

class Command(BaseCommand):
    help = "Create a consistent SQLite snapshot and hashed manifest in a private archive."
    def add_arguments(self, parser):
        parser.add_argument("--output", required=True)
    def handle(self, *args, **options):
        db=settings.DATABASES["default"]
        if db["ENGINE"] != "django.db.backends.sqlite3":
            raise CommandError("Use PostgreSQL's native pg_dump and restore procedures for this installation.")
        output=Path(options["output"])
        if output.exists(): raise CommandError("Choose a new backup filename; existing backups are never overwritten.")
        output.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory() as temporary:
            snapshot=Path(temporary)/"tourney.sqlite3"
            source=sqlite3.connect(f"file:{Path(db['NAME']).resolve()}?mode=ro",uri=True)
            target=sqlite3.connect(snapshot)
            try: source.backup(target)
            finally: source.close(); target.close()
            payload=snapshot.read_bytes()
            manifest={"schema":"open-tourney-sqlite/1","created_at":timezone.now().isoformat(),"files":{"tourney.sqlite3":hashlib.sha256(payload).hexdigest()},"private_data":True,"restore_policy":"Disable external actions, revoke tokens/sessions, reconcile pending deliveries."}
            fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,"wb") as handle, tarfile.open(fileobj=handle,mode="w:gz") as archive:
                for name,data in [("tourney.sqlite3",payload),("manifest.json",json.dumps(manifest,indent=2).encode())]:
                    info=tarfile.TarInfo(name); info.size=len(data); info.mode=0o600
                    archive.addfile(info,io.BytesIO(data))
        self.stdout.write(f"Private SQLite backup saved: {output}. It contains the state at snapshot time; mail files and environment secrets are excluded.")
