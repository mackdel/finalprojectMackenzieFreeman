from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.urls import reverse
from django.utils.html import format_html
from .models import CustomUser, Department

# Admin configuration for CustomUser model
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    fieldsets = UserAdmin.fieldsets + (
        ("Department", {
            "fields": ("role", "department"),
        }),
    )
    list_display = ("last_name", "first_name", "email", "role", "department")
    list_filter = ("role", "department")
    search_fields = ("username", "email", "role")
    ordering = ("last_name",)


# Admin configuration for Department model
class DepartmentAdmin(admin.ModelAdmin):
    model = Department
    fieldsets = (
        (None, {
            "fields": ("name",),
        }),
        ("Department Details", {
            "fields": ("view_department_heads", "view_department_employees"),
        })
    )
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)
    readonly_fields = ("view_department_heads", "view_department_employees")

    def view_department_heads(self, obj):
        heads = obj.users.filter(role=CustomUser.DEPARTMENT_HEAD)
        if heads.exists():
            # Create a clickable link for each department head
            return format_html("<br>".join([
                f'<a href="{reverse("super_admin:accounts_customuser_change", args=[user.id])}">{user.first_name} {user.last_name}</a>'
                for user in heads
            ]))
        return "None"

    def view_department_employees(self, obj):
        employees = obj.users.filter(role=CustomUser.EMPLOYEE)
        if employees.exists():
            # Create a clickable link for each employee
            return format_html("<br>".join([
                f'<a href="{reverse("super_admin:accounts_customuser_change", args=[user.id])}">{user.first_name} {user.last_name}</a>'
                for user in employees
            ]))
        return "None"

    view_department_heads.short_description = "Department Heads"
    view_department_employees.short_description = "Employees"
