from django.shortcuts import redirect
from django.urls import reverse

# Redirect users to the appropriate page based on their role
class RoleRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip middleware logic for logout URL
        if request.path == '/accounts/logout/':
            return self.get_response(request)

        # Skip redirect if the user is accessing the handbook site
        if request.user.is_authenticated:
            if request.path.startswith('/handbook/'):
                return self.get_response(request)

            # Redirect based on role
            if request.user.is_superuser and not request.path.startswith(reverse('super_admin:index')):
                return redirect('super_admin:index')
            elif request.user.is_department_head() and not request.path.startswith(reverse('department_head_admin:index')):
                return redirect('department_head_admin:index')
            elif request.user.is_employee() and not request.path.startswith('/handbook/'):
                return redirect('/handbook/')
        return self.get_response(request)


