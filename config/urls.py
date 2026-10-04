from django.urls import path
from tourney import auth, views as v, desk_views as d

urlpatterns = [
    path("", v.home, name="home"), path("login/", auth.login_view, name="login"),
    path("logout/", auth.logout_view, name="logout"), path("link/<str:raw>/", auth.link_view, name="link"),
    path("demo-login/", auth.demo_login, name="demo_login"), path("mailbox/", auth.mailbox, name="mailbox"),
    path("dashboard/", v.dashboard, name="dashboard"), path("events/new/", v.event_create, name="event_create"),
    path("events/<slug:slug>/", v.public_event, name="event"),
]
for route, view, name in [
    ("edit/", v.event_edit, "event_edit"), ("desk/", v.desk, "desk"), ("live/", v.live, "live"),
    ("register/", v.registration, "register"), ("my/", v.my_event, "my_event"),
    ("action/", v.event_command, "event_command"), ("entries/action/", v.entry_command, "entry_command"),
    ("divisions/new/", v.division_edit, "division_new"), ("divisions/<uuid:division_id>/edit/", v.division_edit, "division_edit"),
    ("divisions/<uuid:division_id>/draw/", v.draw_view, "draw"), ("divisions/<uuid:division_id>/action/", v.division_command, "division_command"),
    ("divisions/<uuid:division_id>/partial/", d.partial_results, "partial_results"),
    ("schedule/", v.schedule_view, "schedule"), ("matches/<uuid:match_id>/", v.match_view, "match"),
    ("matches/<uuid:match_id>/scorer/", d.assign_scorer, "assign_scorer"), ("matches/<uuid:match_id>/schedule/", d.manual_schedule, "manual_schedule"),
    ("courts/<uuid:court_id>/action/", v.court_command, "court_command"), ("finance/", v.finance_command, "finance_command"),
    ("delivery/", d.reconcile_delivery, "reconcile_delivery"),
    ("evidence/", v.sanction_command, "sanction_command"), ("staff/", v.staff_command, "staff_command"),
    ("flyer/", v.flyer, "flyer"), ("qr/", v.qr, "qr"), ("print/", v.print_pack, "print_pack"),
    ("clone/", d.clone, "clone"), ("roster/import/", d.roster_import, "roster_import"),
    ("participants/<uuid:participant_id>/", d.participant_edit, "participant_edit"), ("entries/<uuid:entry_id>/edit/", d.entry_edit, "entry_edit"),
    ("results.csv", d.results_csv, "results_csv"), ("roster.csv", d.roster_csv, "roster_csv"),
    ("archive/", d.archive_export, "archive_export"), ("archive/import/", d.archive_import, "archive_import"),
    ("packages/create/", d.package_create, "package_create"), ("packages/<uuid:package_id>/", d.package_download, "package_download"),
]:
    urlpatterns.append(path(f"events/<slug:slug>/{route}", view, name=name))
