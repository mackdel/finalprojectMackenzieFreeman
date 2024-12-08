from .models import PolicySection

# Add all policy sections to the context for the nav bar
def policy_sections_context(request):
    if request.user.is_authenticated:
        return {'sections': PolicySection.objects.all()}
    return {}
