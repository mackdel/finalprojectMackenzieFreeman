from django.contrib.auth.models import AbstractUser
from django.db import models

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
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
    departments = models.ManyToManyField(
        Department,
        blank=True,
        related_name="users"  # Adds a reverse relation from Department to its users
    )

    def is_employee(self):
        return self.role == self.EMPLOYEE

    def is_department_head(self):
        return self.role == self.DEPARTMENT_HEAD

    def is_admin(self):
        return self.role == self.ADMIN
