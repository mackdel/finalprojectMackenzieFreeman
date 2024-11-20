from django.urls import reverse_lazy, reverse
from django.contrib.auth.views import LoginView
from django.views.generic.edit import CreateView
from .forms import CustomUserCreationForm

# Signup view: Allows users to make a new account
class SignUpView(CreateView):
    form_class = CustomUserCreationForm  # Use the custom form
    success_url = reverse_lazy('login')  # Redirect to login page after successful signup
    template_name = 'registration/signup.html'


# Login View: Redirect users based on their role
class RoleBasedLoginView(LoginView):
    def get_success_url(self):
        user = self.request.user

        if user.is_superuser:
            return reverse('super_admin:index')  # Redirect super admin to their dashboard
        elif user.is_department_head():
            return reverse('department_head_admin:index')  # Redirect department head to their portal
        elif user.is_employee():
            return '/handbook/'  # Redirect employees to the handbook
        else:
            return '/'  # Default fallback if no role is set
