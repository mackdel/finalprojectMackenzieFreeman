from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from .forms import CustomUserCreationForm

# Signup view: Allows users to make a new account
class SignUpView(CreateView):
    form_class = CustomUserCreationForm  # Use the custom form
    success_url = reverse_lazy('login')  # Redirect to login page after successful signup
    template_name = 'registration/signup.html'