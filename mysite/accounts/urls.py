from django.urls import path
from django.contrib.auth import views as auth_views
from .views import SignUpView, RoleBasedLoginView

app_name = "accounts"

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("login/", RoleBasedLoginView.as_view(), name="login"),
    path("password_change/", auth_views.PasswordChangeView.as_view(), name="password_change"),
    path("password_change/done/", auth_views.PasswordChangeDoneView.as_view(), name="password_change_done"),
]
