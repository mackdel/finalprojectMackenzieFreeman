from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic import TemplateView, ListView, DetailView
from django.views.generic.edit import FormView
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from datetime import datetime
from .models import PolicySection, Policy
from .forms import PolicyRequestForm
from .utils import send_mailgun_email

# Home page view: Displays the homepage for authenticated users
class IndexView(LoginRequiredMixin, TemplateView):
    template_name = "handbook/index.html"


# Policy sections view: Displays all policy sections with their related policies listed underneath
class PolicySectionsView(LoginRequiredMixin, ListView):
    model = PolicySection
    template_name = "handbook/policy_sections.html"
    context_object_name = "sections"

    def get_queryset(self):
        # Prefetch related policies for efficiency
        return PolicySection.objects.prefetch_related('policies')


# Section detail view: Displays details of a single section and its related policies
class SectionDetailView(LoginRequiredMixin, DetailView):
    model = PolicySection
    template_name = "handbook/section.html"
    context_object_name = "section"
    slug_field = "number"  # Match section based on the 'number' field (e.g., 1.0)
    slug_url_kwarg = "section_number"  # URL parameter to look up the section

    def get_context_data(self, **kwargs):
        # Add policies in the section to the context
        context = super().get_context_data(**kwargs)
        context['policies'] = Policy.objects.filter(section=self.object).order_by('number')
        return context


# Policy request form view: Allows users to submit questions/clarifications for a specific policy
class PolicyRequestFormView(LoginRequiredMixin, FormView):
    form_class = PolicyRequestForm
    template_name = "handbook/request_form.html"

    def get_success_url(self):
        # Stay on the same page but pass success=True as a GET parameter
        return reverse("handbook:request_form", kwargs={'policy_number': self.kwargs['policy_number']})

    def get_context_data(self, **kwargs):
        # Add the related policy to the context
        context = super().get_context_data(**kwargs)
        context['policy'] = get_object_or_404(Policy, number=self.kwargs['policy_number'])
        context['success'] = self.request.GET.get('success', False)
        return context

    def form_valid(self, form):
        # Save the form and associate it with the specific policy
        policy = get_object_or_404(Policy, number=self.kwargs['policy_number'])
        policy_request = form.save(commit=False)
        policy_request.policy = policy
        policy_request.save()

        # Prepare dynamic variables for the email
        employee_email = form.cleaned_data['email']
        question = form.cleaned_data['question']
        policy_title = policy.title
        policy_number = policy.number
        submission_date = datetime.now().strftime('%m-%d-%Y %I:%M %p')

        # Variables to populate the template
        variables = {
            "policy_number": policy_number,
            "policy_title": policy_title,
            "question": question,
            "submission_date": submission_date,
            "employee_email": employee_email,
        }

        # Send confirmation email to the employee
        send_mailgun_email(
            to_email=employee_email,
            subject="Policy Request Received",
            variables=variables,
        )

        # Redirect to the same page with success=True
        success_url = f"{self.get_success_url()}?success=True"
        return HttpResponseRedirect(success_url)
