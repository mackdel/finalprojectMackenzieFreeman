from django.shortcuts import redirect
from django.urls import reverse

# Redirect users to the appropriate page based on their role
class RoleRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip middleware logic for logout and account-related URLs
        exempt_paths = [
            '/accounts/logout/',
            reverse('password_change'),
            reverse('password_change_done'),
            reverse('password_reset'),
            reverse('password_reset_done'),
            reverse('password_reset_confirm', kwargs={'uidb64': 'uidb64', 'token': 'token'}),
            reverse('password_reset_complete'),
        ]

        if request.path in exempt_paths or request.path.startswith('/handbook/'):
            return self.get_response(request)

        if request.user.is_authenticated:
            # Redirect based on role
            if request.user.is_superuser and not request.path.startswith(reverse('super_admin:index')):
                return redirect('super_admin:index')
            elif request.user.is_department_head() and not request.path.startswith(reverse('department_head_admin:index')):
                return redirect('department_head_admin:index')
            elif request.user.is_employee() and not request.path.startswith('/handbook/'):
                return redirect('/handbook/')

        return self.get_response(request)
