from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("session/start/", views.start_session, name="start_session"),
    path("session/<int:session_id>/", views.session_detail, name="session_detail"),
    path("session/<int:session_id>/tick/", views.session_tick, name="session_tick"),
    path("session/<int:session_id>/state/", views.session_state, name="session_state"),
    path("session/<int:session_id>/action/", views.session_action, name="session_action"),
    path("session/<int:session_id>/phase/", views.session_phase, name="session_phase"),
]
