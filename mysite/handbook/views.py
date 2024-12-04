from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.db.models import ForeignKey, ManyToManyField
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView
from django.views.generic.edit import FormView
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.contrib import messages
from datetime import datetime
from .models import PolicySection, Policy, PolicyApprovalRequest, ProcedureStep, Definition
from .forms import PolicyRequestForm, MajorChangeQuestionnaireForm
from .utils import send_mailgun_email

"""
Handles views for the handbook application, including homepage, policy sections, 
policy requests, and major policy change processing.
"""

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

    def get_form_kwargs(self):
        # Pass the current user to the form to prepopulate fields
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        # Add the related policy to the context
        context = super().get_context_data(**kwargs)
        context['policy'] = get_object_or_404(Policy, number=self.kwargs['policy_number'])
        context['success'] = self.request.GET.get('success', False)
        return context

    # Save the form and associate it with the specific policy
    def form_valid(self, form):
        # Get the policy related to the form
        policy = get_object_or_404(Policy, number=self.kwargs['policy_number'])
        policy_request = form.save(commit=False)

        # Attach additional details to the request
        policy_request.policy = policy
        policy_request.name = f"{self.request.user.first_name} {self.request.user.last_name}"
        policy_request.email = self.request.user.email
        policy_request.save()

        # Prepare dynamic variables for the email
        employee_email = self.request.user.email
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

        # Redirect back to the same page with a success message
        success_url = f"{self.get_success_url()}?success=True"
        return HttpResponseRedirect(success_url)


# Major change questionnaire view: Handles the form submission for major policy changes
class MajorChangeQuestionnaireView(LoginRequiredMixin, FormView):
    template_name = "handbook/major_change_questionnaire.html"
    form_class = MajorChangeQuestionnaireForm

    # Redirect back to the admin panel after processing the questionnaire
    def get_success_url(self):
        return reverse("admin:handbook_policy_changelist")

    #  Process the form and determine if a major change request is needed
    def form_valid(self, form):
        # Get the policy related to the form
        policy = get_object_or_404(Policy, id=self.kwargs["policy_id"])

        unsaved_changes = self.request.session.get("unsaved_policy_changes", {})
        print("Views", unsaved_changes)

        # Check if any major impacts are identified
        is_major_change = any([
            form.cleaned_data.get("operational_impact", False),
            form.cleaned_data.get("compliance_impact", False),
            form.cleaned_data.get("financial_impact", False),
            form.cleaned_data.get("technology_impact", False),
        ])

        if is_major_change:
            # Create a policy approval request if major changes are detected
            self.create_policy_approval_request(policy, unsaved_changes)
        else:
            # Apply changes directly for minor updates
            self.apply_changes(policy, unsaved_changes)

        # Clear session after handling changes
        self.request.session.pop("unsaved_policy_changes", None)
        self.request.session.pop("policy_id", None)
        return redirect(self.get_success_url())


    # Create a PolicyApprovalRequest to handle major policy changes
    def create_policy_approval_request(self, policy, unsaved_changes):
        procedure_steps = [
            step for step in unsaved_changes.get("procedure_steps", []) if not step.get("DELETE")
        ]
        definitions = [
            definition for definition in unsaved_changes.get("definitions", []) if not definition.get("DELETE")
        ]

        # Save the approval request to the database
        PolicyApprovalRequest.objects.create(
            policy=policy,
            submitter=self.request.user,
            status="pending",
            proposed_title=unsaved_changes.get("title", policy.title),
            proposed_purpose=unsaved_changes.get("purpose", policy.purpose),
            proposed_scope=unsaved_changes.get("scope", policy.scope),
            proposed_policy_statements=unsaved_changes.get("policy_statements", policy.policy_statements),
            proposed_responsibilities=unsaved_changes.get("responsibilities", policy.responsibilities),
            proposed_related_policies=unsaved_changes.get("related_policies", []),
            proposed_procedure_steps=procedure_steps,
            proposed_definitions=definitions,
        )
        # Inform the user about the submission
        messages.warning(
            self.request,
            f"Major change detected for policy {policy.number} {policy.title}. Approval request submitted.",
        )

    # Directly apply minor changes to the policy
    def apply_changes(self, policy, unsaved_changes):
        major, minor = map(int, policy.version.split('.'))
        minor += 1
        policy.version = f"{major}.{minor}"

        for field, value in unsaved_changes.items():
            if field == "related_policies":
                # Update related policies
                policy.related_policies.set(value)
            elif field == "procedure_steps":
                # Clear existing procedure steps and add new ones
                policy.procedure_steps.all().delete()
                for step in value:
                    if not step.get("DELETE"):  # Skip deleted steps
                        ProcedureStep.objects.create(
                            policy=policy,
                            step_number=step["step_number"],
                            description=step["description"],
                        )
            elif field == "definitions":
                # Clear existing definitions and associate new ones
                policy.definitions.clear()
                for definition in value:
                    if not definition.get("DELETE"): # Skip deleted steps
                        definition_instance = Definition.objects.get(id=definition["id"])
                        policy.definitions.add(definition_instance)
            else:
                # Handle other fields, including ForeignKey and ManyToMany
                field_obj = policy._meta.get_field(field)
                if isinstance(field_obj, ForeignKey):
                    value = field_obj.remote_field.model.objects.filter(pk=value).first() if value else None
                    setattr(policy, field, value)
                elif isinstance(field_obj, ManyToManyField):
                    related_manager = getattr(policy, field)
                    related_manager.set(value)
                else:
                    setattr(policy, field, value)

        policy.save()
        messages.success(
            self.request,
            f"Changes to {policy.number} {policy.title} have been saved as a minor change.",
        )

    # Handle invalid form submissions by displaying an error message
    def form_invalid(self, form):
        messages.error(self.request, "Please complete the questionnaire.")
        return self.render_to_response(self.get_context_data(form=form))


class ArchivePolicyView(View):
    def get(self, request, policy_id, *args, **kwargs):
        # Get the policy object
        policy = get_object_or_404(Policy, id=policy_id)

        # Create a PolicyApprovalRequest for archiving
        PolicyApprovalRequest.objects.create(
            policy=policy,
            submitter=request.user,
            request_type="archive",
            status="pending",
            section=policy.section,
            policy_owner=policy.policy_owner,
            version=policy.version,
        )

        # Add a success message
        messages.success(request, f"Archive request for {policy.number} {policy.title} submitted successfully.")

        # Redirect back to the policy change view
        return redirect("admin:handbook_policy_change", object_id=policy_id)