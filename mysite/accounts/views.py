from django.urls import reverse_lazy, reverse
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import CreateView
from django.views.generic import TemplateView
from handbook.models import PolicyRequest
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
        elif user.is_executive():
            return reverse('executive_admin:index')  # Redirect executives to their portal
        elif user.is_employee():
            return '/handbook/'  # Redirect employees to the handbook
        else:
            return '/'  # Default fallback if no role is set


# Profile View: Allows users to view account info
class UserProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # Add user details to context
        context['user'] = user
        # Fetch the user's submitted forms
        context['submitted_forms'] = PolicyRequest.objects.filter(email=user.email)
        return context