from django.urls import path
from .views import SignUpView, RoleBasedLoginView

app_name = "accounts"

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("login/", RoleBasedLoginView.as_view(), name="login"),
]
