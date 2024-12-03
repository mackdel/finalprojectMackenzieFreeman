from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.db.models import ForeignKey, ManyToManyField
from django.views.generic import TemplateView, ListView, DetailView
from django.views.generic.edit import FormView
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.contrib import messages
from datetime import datetime
from .models import PolicySection, Policy, PolicyApprovalRequest, ProcedureStep, Definition
from .forms import PolicyRequestForm, MajorChangeQuestionnaireForm
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

    def form_valid(self, form):
        # Save the form and associate it with the specific policy
        policy = get_object_or_404(Policy, number=self.kwargs['policy_number'])
        policy_request = form.save(commit=False)
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

        # Redirect to the same page with success=True
        success_url = f"{self.get_success_url()}?success=True"
        return HttpResponseRedirect(success_url)


# Major change questionnaire view: Handles the form submission for major policy changes
class MajorChangeQuestionnaireView(LoginRequiredMixin, FormView):
    template_name = "handbook/major_change_questionnaire.html"
    form_class = MajorChangeQuestionnaireForm

    # Redirect back to the admin panel after processing the questionnaire
    def get_success_url(self):
        return reverse("admin:handbook_policy_changelist")

    # Process form submission
    def form_valid(self, form):
        policy = get_object_or_404(Policy, id=self.kwargs["policy_id"])
        unsaved_changes = self.request.session.get("unsaved_policy_changes", {})
        print("Views", unsaved_changes)

        # Check for major chnage
        is_major_change = any([
            form.cleaned_data.get("operational_impact", False),
            form.cleaned_data.get("compliance_impact", False),
            form.cleaned_data.get("financial_impact", False),
            form.cleaned_data.get("technology_impact", False),
        ])

        if is_major_change:
            self.create_policy_approval_request(policy, unsaved_changes)
        else:
            self.apply_changes(policy, unsaved_changes)

        # Clear session after handling changes
        self.request.session.pop("unsaved_policy_changes", None)
        self.request.session.pop("policy_id", None)
        return redirect(self.get_success_url())

    def create_policy_approval_request(self, policy, unsaved_changes):
        procedure_steps = []
        for step in unsaved_changes.get("procedure_steps", []):
            # Exclude steps marked for deletion from proposed changes
            if not step.get("DELETE"):
                procedure_steps.append({
                    "id": step.get("id"),
                    "step_number": step.get("step_number"),
                    "description": step.get("description"),
                })

        # Handles major changes by creating a PolicyApprovalRequest
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
            proposed_definitions=unsaved_changes.get("definitions", []),
        )
        messages.warning(
            self.request,
            f"Major change detected for policy {policy.number} {policy.title}. Approval request submitted.",
        )

    def apply_changes(self, policy, unsaved_changes):
        for field, value in unsaved_changes.items():
            if field == "related_policies":
                policy.related_policies.set(value)
            elif field == "procedure_steps":
                policy.procedure_steps.all().delete()  # Clear existing steps
                for step in value:
                    if not step.get("DELETE"):  # Skip deleted steps
                        ProcedureStep.objects.create(
                            policy=policy,
                            step_number=step["step_number"],
                            description=step["description"],
                        )
            elif field == "definitions":
                policy.definitions.clear()
                definitions_to_add = Definition.objects.filter(id__in=[d["id"] for d in value])
                policy.definitions.set(definitions_to_add)
            else:
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

    # Handle invalid questionnaire submission
    def form_invalid(self, form):
        messages.error(self.request, "Please complete the questionnaire.")
        return self.render_to_response(self.get_context_data(form=form))