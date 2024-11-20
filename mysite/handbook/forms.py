from django import forms
from .models import PolicyRequest

class PolicyRequestForm(forms.ModelForm):
    class Meta:
        model = PolicyRequest
        fields = ['first_name', 'last_name', 'email', 'question']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control bg-light text-muted',
                'readonly': 'readonly',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control bg-light text-muted',
                'readonly': 'readonly',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control bg-light text-muted',
                'readonly': 'readonly',
            }),
            'question': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Your Question or Clarification',
                'required': 'required',
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Pass the user from the view
        super().__init__(*args, **kwargs)
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
