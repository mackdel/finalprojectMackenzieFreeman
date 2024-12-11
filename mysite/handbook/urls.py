from django.urls import path
from .views import (
    IndexView,
    PolicySectionsDetailsView,
    PolicyFeedbackFormView,
    MajorChangeQuestionnaireView,
    ArchivePolicyView,
    FetchPolicyDetailsView,
    FetchIntroductionDetailsView,
)
from accounts.views import UserProfileView

app_name = "handbook"

urlpatterns = [
    path("", IndexView.as_view(), name="index"),

    path("sections/", PolicySectionsDetailsView.as_view(), name="sections"),
    path("policy/<int:policy_id>/content/", FetchPolicyDetailsView.as_view(), name="fetch_policy_content"),
    path('introduction/content/', FetchIntroductionDetailsView.as_view(), name='fetch_introduction_content'),

    path("policy/<str:policy_number>/feedback", PolicyFeedbackFormView.as_view(), name="feedback_form"),
    path("profile/", UserProfileView.as_view(), name='user_profile'),
    path("major-change-questionnaire/<int:policy_id>/", MajorChangeQuestionnaireView.as_view(), name='major_change_questionnaire'),
    path("policy/<int:policy_id>/archive/", ArchivePolicyView.as_view(), name="archive_policy"),
]
