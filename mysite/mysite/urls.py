from django.contrib import admin
from django.urls import include, path
from debug_toolbar.toolbar import debug_toolbar_urls
from handbook.admin import super_admin_site, department_head_admin

urlpatterns = [
    path("handbook/", include("handbook.urls")),
    path("super-admin/", super_admin_site.urls),
    path("department-head-admin/", department_head_admin.urls),
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
] + debug_toolbar_urls()
