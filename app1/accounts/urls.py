from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.onboarding_view, name="onboarding"),
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("profile/", views.profile_update_view, name="profile"),
    path("logout/", views.logout_view, name="logout"),
]
