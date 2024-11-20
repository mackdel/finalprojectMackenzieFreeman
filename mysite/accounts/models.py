from django.contrib.auth.models import AbstractUser
from django.db import models

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    # Additional Required fields
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=False)
    last_name = models.CharField(max_length=30, blank=False)

    # Define user roles
    EMPLOYEE = 'employee'
    DEPARTMENT_HEAD = 'department_head'
    ADMIN = 'admin'

    ROLE_CHOICES = [
        (EMPLOYEE, 'Employee'),
        (DEPARTMENT_HEAD, 'Department Head'),
        (ADMIN, 'Admin'),
    ]

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default=EMPLOYEE)
    department = models.ForeignKey(
        Department,
        null=True,  # Allow null for super admins or unaffiliated users
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users"
    )

    def is_employee(self):
        return self.role == self.EMPLOYEE

    def is_department_head(self):
        return self.role == self.DEPARTMENT_HEAD

    def is_admin(self):
        return self.role == self.ADMIN

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Assign permissions when role is department head
        if self.is_department_head():
            from django.contrib.auth.models import Permission
            from django.contrib.contenttypes.models import ContentType
            from handbook.models import Policy, PolicyRequest

            # Get content types for models
            policy_ct = ContentType.objects.get_for_model(Policy)
            policy_request_ct = ContentType.objects.get_for_model(PolicyRequest)

            # Get permissions
            view_policy = Permission.objects.get(codename='view_policy', content_type=policy_ct)
            change_policy = Permission.objects.get(codename='change_policy', content_type=policy_ct)
            view_request = Permission.objects.get(codename='view_policyrequest', content_type=policy_request_ct)
            change_request = Permission.objects.get(codename='change_policyrequest', content_type=policy_request_ct)

            # Add permissions
            self.user_permissions.add(view_policy, change_policy, view_request, change_request)
