from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from handbook.models import Policy, ProcedureStep, Definition, PolicyApprovalRequest
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
    EXECUTIVE = 'executive'
    ADMIN = 'admin'

    ROLE_CHOICES = [
        (EMPLOYEE, 'Employee'),
        (DEPARTMENT_HEAD, 'Department Head'),
        (EXECUTIVE, 'Executive'),
        (ADMIN, 'Admin'),
    ]

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

    def is_executive(self):
        return self.role == self.EXECUTIVE

    def is_admin(self):
        return self.role == self.ADMIN

    # Validates the role and department assignments before saving.
    def clean(self):
        # Get or create the Executive department
        executive_department, _ = Department.objects.get_or_create(name="Executive")

        # Validation for executives
        if self.is_executive():
            # Ensure the executive is only in the Executive department
            if self.department and self.department != executive_department:
                raise ValidationError({"department": "Executives must belong to the Executive department."})
            self.department = executive_department

        # Validation for department heads
        if self.is_department_head():
            # Department heads cannot belong to the Executive department
            if self.department == executive_department:
                raise ValidationError({"department": "Department heads cannot belong to the Executive department."})
            # Department must belong to a department
            if not self.department:
                raise ValidationError({"department": "Department heads must have a department assigned."})

        super().clean()

    def save(self, *args, **kwargs):
        # Call `clean()` to validate the data before saving
        self.full_clean()
        super().save(*args, **kwargs)
        self.assign_role_permissions()

    # Assign permissions based on the user's role.
    def assign_role_permissions(self):
        if self.is_department_head():
            # Assign department head permissions
            content_types = [
                ContentType.objects.get_for_model(Policy),
                ContentType.objects.get_for_model(Definition),
                ContentType.objects.get_for_model(ProcedureStep),
            ]
            permissions = Permission.objects.filter(content_type__in=content_types, codename__in=[
                'view_procedurestep','view_policy','view_definition', 'view_policyapprovalrequest'
            ])
            self.user_permissions.set(permissions)
        elif self.is_executive():
            # Assign executive permissions
            content_types = [
                ContentType.objects.get_for_model(Policy),
                ContentType.objects.get_for_model(Definition),
                ContentType.objects.get_for_model(ProcedureStep),
            ]
            permissions = Permission.objects.filter(content_type__in=content_types, codename__in=[
                'view_procedurestep','view_policy','view_definition', 'view_policyapprovalrequest'
            ])
            self.user_permissions.set(permissions)
        else:
            # Clear permissions for other roles
            self.user_permissions.clear()

