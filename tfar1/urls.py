
from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("upload/", views.upload_tfar, name="upload_tfar"),
    path("download/", views.download_tfar_csv, name="download_tfar_csv"),
    path("debug/", views.debug_view),
]
