import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tarfile
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = "Validate a SQLite backup into a NEW directory, disable outbound actions, and revoke old sessions/tokens."
    def add_arguments(self, parser):
        parser.add_argument("backup")
        parser.add_argument("--output-dir",required=True)
    def handle(self,*args,**options):
        destination=Path(options["output_dir"])
        if destination.exists(): raise CommandError("Restore into a new directory. An existing installation is never overwritten.")
        try:
            with tarfile.open(options["backup"],"r:gz") as archive:
                members=archive.getmembers()
                if {m.name for m in members}!={"manifest.json","tourney.sqlite3"} or len(members)!=2 or any(not m.isfile() or m.size>256*1024*1024 for m in members):
                    raise ValueError()
                manifest=json.loads(archive.extractfile("manifest.json").read())
                data=archive.extractfile("tourney.sqlite3").read()
                if manifest["schema"]!="open-tourney-sqlite/1" or hashlib.sha256(data).hexdigest()!=manifest["files"]["tourney.sqlite3"]:
                    raise ValueError()
        except (OSError,tarfile.TarError,ValueError,KeyError,TypeError):
            raise CommandError("Invalid backup archive or manifest. No installation was changed.")
        destination.mkdir(parents=True,mode=0o700)
        path=destination/"tourney.sqlite3"
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,"wb") as handle: handle.write(data)
        db=sqlite3.connect(path)
        try:
            if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok": raise CommandError("SQLite integrity check failed. Preserve the isolated restore for inspection.")
            with db:
                db.execute("UPDATE tourney_event SET external_actions_enabled=0")
                db.execute("UPDATE tourney_outbox SET status='uncertain', error='Restored snapshot: reconcile delivery before retry.' WHERE status IN ('queued','sending')")
                db.execute("DELETE FROM tourney_token")
                db.execute("DELETE FROM django_session")
        except sqlite3.DatabaseError:
            raise CommandError("This backup is incompatible with the current schema. The original installation was not changed.")
        finally: db.close()
        (destination/"RESTORE-REVIEW.json").write_text(json.dumps(manifest,indent=2))
        self.stdout.write(f"Restored into {destination}. External actions are disabled; sessions and links were revoked. Review before serving. Snapshot time: {manifest['created_at']}")
