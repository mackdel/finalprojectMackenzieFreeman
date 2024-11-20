from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.urls import reverse
from django.utils.html import format_html
from .models import CustomUser, Department


# Admin configuration for CustomUser model
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    fieldsets = UserAdmin.fieldsets + (
        ("Custom Fields", {
            "fields": ("role", "departments"),
        }),
    )
    list_display = ("username", "email", "role")
    list_filter = ("role", "departments")
    search_fields = ("username", "email", "role")
    ordering = ("username",)
    filter_horizontal = ("departments",)


# Admin configuration for Department model
class DepartmentAdmin(admin.ModelAdmin):
    model = Department
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)
    readonly_fields = ("view_department_heads", "view_department_employees")

    def view_department_heads(self, obj):
        """Display department heads in a clean, multi-line format"""
        heads = obj.users.filter(role=CustomUser.DEPARTMENT_HEAD)
        if heads.exists():
            # Create a clickable link for each department head
            return format_html("<br>".join([
                f'<a href="{reverse("admin:accounts_customuser_change", args=[user.id])}">{user.username} ({user.email})</a>'
                for user in heads
            ]))
        return "None"

    def view_department_employees(self, obj):
        """Display employees in a clean, multi-line format"""
        employees = obj.users.filter(role=CustomUser.EMPLOYEE)
        if employees.exists():
            # Create a clickable link for each employee
            return format_html("<br>".join([
                f'<a href="{reverse("admin:accounts_customuser_change", args=[user.id])}">{user.username} ({user.email})</a>'
                for user in employees
            ]))
        return "None"

    view_department_heads.short_description = "Department Heads"
    view_department_employees.short_description = "Employees"

    # Organize fieldsets for better layout
    fieldsets = (
        (None, {
            "fields": ("name",),
        }),
        ("Department Details", {
            "fields": ("view_department_heads","view_department_employees"),
        })
    )

# Register models with the admin site
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Department, DepartmentAdmin)
