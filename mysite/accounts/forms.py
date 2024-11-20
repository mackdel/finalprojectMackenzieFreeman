from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(required=True, max_length=30, label="First Name")
    last_name = forms.CharField(required=True, max_length=30, label="Last Name")

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name' ,'username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = CustomUser.EMPLOYEE  # Default role
        if commit:
            user.save()
        return user
