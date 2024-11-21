from django.urls import path
from .views import (
    IndexView,
    PolicySectionsView,
    SectionDetailView,
    PolicyRequestFormView,
)
from accounts.views import UserProfileView

app_name = "handbook"

urlpatterns = [
    path("", IndexView.as_view(), name="index"),
    path("policy_sections/", PolicySectionsView.as_view(), name="policy_sections"),
    path("section/<str:section_number>/", SectionDetailView.as_view(), name="section"),
    path("policy/<str:policy_number>/request", PolicyRequestFormView.as_view(), name="request_form"),
    path("profile/", UserProfileView.as_view(), name='user_profile'),
]
