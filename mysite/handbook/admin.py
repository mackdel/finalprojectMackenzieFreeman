from django.db import models
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import admin
from .models import PolicySection, Policy, Definition, PolicyRequest, ProcedureStep, PolicyApprovalRequest
from accounts.models import CustomUser, Department
from accounts.admin import CustomUserAdmin, DepartmentAdmin
from .utils import send_mailgun_email
from django.core.exceptions import ValidationError

# Custom Admin site for Super Admins
class SuperAdminSite(admin.AdminSite):
    site_header = "Handbook Admin Portal"
    site_title = "Handbook Site Admin"
    index_title = "Welcome to the Handbook Admin Dashboard"
    site_url = "/handbook/"

super_admin_site = SuperAdminSite(name="super_admin")


# Custom Admin site for Executives
class ExecutiveAdminSite(admin.AdminSite):
    site_header = "Executive Portal"
    site_title = "Executive Site Admin"
    index_title = "Welcome to the Executive Dashboard"
    site_url = "/handbook/"

    # Only allow users with the executive role
    def has_permission(self, request):
        if not request.user.is_authenticated:
            return False
        # Allow access if the user is an executive
        return request.user.is_executive()

executive_admin_site = ExecutiveAdminSite(name="executive_admin")


# Custom Admin site for Department Heads
class DepartmentHeadAdminSite(admin.AdminSite):
    site_header = "Department Head Portal"
    site_title = "Department Head Site Admin"
    index_title = "Welcome to the Department Head Dashboard"
    site_url = "/handbook/"

    # Only allow users with the department head role
    def has_permission(self, request):
        if not request.user.is_authenticated:
            return False
        if request.user.is_department_head():
            # Ensure the user has view permissions for ProcedureStep and Definition
            return request.user.has_perm('handbook.view_procedurestep') and request.user.has_perm('handbook.view_definition')
        return False

department_head_admin = DepartmentHeadAdminSite(name="department_head_admin")


# Inline configuration for Procedure Steps in Policies
class ProcedureStepInline(admin.TabularInline):
    model = ProcedureStep
    fields = ['step_number', 'description']
    extra = 0
    ordering = ['step_number']  # Order steps by their number
    can_delete = True

    def has_add_permission(self, request, obj=None):
        return request.user.is_department_head() or request.user.is_superuser or request.user.is_executive()

    def has_change_permission(self, request, obj=None):
        return request.user.is_department_head() or request.user.is_superuser or request.user.is_executive()

    def has_delete_permission(self, request, obj=None):
        return request.user.is_department_head() or request.user.is_superuser or request.user.is_executive()

    # Ensure steps are always ordered correctly in the admin.
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('step_number')


# Inline configuration for Definitions in Policies
class DefinitionInline(admin.TabularInline):
    model = Policy.definitions.through
    extra = 1  # Start with one empty row for adding definitions
    verbose_name = "Definition"
    verbose_name_plural = "Definitions"

    # Restrict the available definitions to those related to the department head's policies.
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "definition":
            if request.user.is_department_head():
                kwargs["queryset"] = Definition.objects.filter(
                    policies__policy_owner=request.user.department
                ).distinct()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_add_permission(self, request, obj=None):
        return request.user.is_department_head() or request.user.is_superuser or request.user.is_executive()

    def has_change_permission(self, request, obj=None):
        return request.user.is_department_head() or request.user.is_superuser or request.user.is_executive()

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# Admin configuration for Policy model
class PolicyAdmin(admin.ModelAdmin):
    fieldsets = [
        ("Policy Information", {
            "fields": ["section", "title", "number", "version", "policy_owner", "pub_date", "review_period"]
        }),
        ("Policy Details", {
            "fields": [
                "purpose",
                "scope",
                "policy_statements",
                "responsibilities"
            ],
        }),
        ("Relationships", {
            "fields": ["related_policies"]
        }),
    ]
    readonly_fields = ["number", "pub_date", "version"]
    list_display = ["number", "title", "section", "policy_owner", "pub_date", "version"]
    list_filter = ["section", "policy_owner", "pub_date"]
    search_fields = ["title", "policy_statements", "section__title"]
    ordering = ["section", "number"]
    filter_horizontal = ["related_policies"]  # Horizontal widget for managing related policies
    inlines = [ProcedureStepInline, DefinitionInline]

    # Save the policy model
    def save_model(self, request, obj, form, change):
        if change:
            # Check if there are unsaved changes
            unsaved_changes = {}

            # Get changes to the policy fields
            for field, value in form.cleaned_data.items():
                if hasattr(obj, field):
                    field_obj = obj._meta.get_field(field)
                    if isinstance(field_obj, models.ForeignKey):
                        value = value.pk if value else None
                    elif isinstance(field_obj, models.ManyToManyField):
                        value = list(value.values_list("id", flat=True))
                    unsaved_changes[field] = value

            # Temporarily store the basic changes
            request.session["unsaved_policy_basic_changes"] = unsaved_changes
            request.session["policy_id"] = obj.id

            print("Save Model", unsaved_changes)

        # Skip saving for now
        return

    # Save inline-related changes into the session but avoid applying them
    def save_related(self, request, form, formsets, change):
        # Save related policies
        policy_id = request.session.get("policy_id")
        if policy_id:
            policy = Policy.objects.get(id=policy_id)
            unsaved_changes = request.session.get("unsaved_policy_basic_changes", {})

            related_policies = form.cleaned_data.get("related_policies", policy.related_policies.all())
            unsaved_changes["related_policies"] = list(related_policies.values_list("id", flat=True))

            # Save procedures and defintion chnages
            procedure_steps = []
            definitions = []
            for formset in formsets:
                if formset.model == ProcedureStep:
                    for form in formset.forms:
                        if form.cleaned_data.get("DELETE", False):
                            obj = form.instance
                            procedure_steps.append({
                                "id": obj.id,
                                "step_number": obj.step_number,
                                "description": obj.description,
                                "DELETE": True,
                            })
                        else:
                            instance = form.save(commit=False)
                            if instance.description:
                                if not instance.pk:
                                    instance.policy = form.instance.policy
                                    instance.save()
                                procedure_steps.append({
                                    "id": instance.id,
                                    "step_number": instance.step_number,
                                    "description": instance.description,
                                })

                elif formset.model == Policy.definitions.through:
                    for form in formset.forms:
                        definition_instance = form.cleaned_data.get("definition")
                        if definition_instance and not form.cleaned_data.get("DELETE", False):
                            definitions.append({
                                "id": definition_instance.id,
                                "term": definition_instance.term,
                                "definition": definition_instance.definition,
                            })

            # Update unsaved changes for procedure steps and definitions
            unsaved_changes["procedure_steps"] = procedure_steps
            unsaved_changes["definitions"] = definitions

            # Save unsaved changes to session
            request.session["unsaved_policy_changes"] = unsaved_changes

            print("Save Related", unsaved_changes)

        # Do not commit related changes to the database yet
        return

    # Redirects to the major change questionnaire when saving an edited policy
    def response_change(self, request, obj):
        if "_save" in request.POST:
            questionnaire_url = reverse("handbook:major_change_questionnaire", kwargs={"policy_id": obj.id})
            return HttpResponseRedirect(questionnaire_url)
        return super().response_change(request, obj)

    # Construct a change message that avoids accessing new_objects
    def construct_change_message(self, request, form, formsets, add=False):
        change_message = []
        if form.changed_data:
            change_message.append(f"Changed fields: {', '.join(form.changed_data)}")

        # Custom handling for formsets
        for formset in formsets:
            if hasattr(formset, 'deleted_forms') and formset.deleted_forms:
                change_message.append(f"Deleted {len(formset.deleted_forms)} inline(s).")
            if hasattr(formset, 'changed_objects') and formset.changed_objects:
                change_message.append(f"Changed {len(formset.changed_objects)} inline(s).")
            if hasattr(formset, 'added_forms') and formset.added_forms:
                change_message.append(f"Added {len(formset.added_forms)} inline(s).")

        if add:
            return "Added new object."
        return " ".join(change_message) if change_message else "No changes detected."

# Executive Configuration of Policy Model
class PolicyAdminForExecutive(PolicyAdmin):
    inlines = [ProcedureStepInline, DefinitionInline]

    # Allow access to this model in the admin for executives
    def has_module_permission(self, request):
        return request.user.is_executive()

    # Allow editing policies
    def has_change_permission(self, request, obj=None):
        return request.user.is_executive()

    # Allow adding policies
    def has_add_permission(self, request):
        return request.user.is_executive()

    # Executives can view all policies
    def get_queryset(self, request):
        return super().get_queryset(request)

    # Executives cannot delete policies
    def has_delete_permission(self, request, obj=None):
        return False


# Department Head Configuration of Policy Model
class PolicyAdminForDepartmentHead(PolicyAdmin):
    inlines = [ProcedureStepInline, DefinitionInline]

    # Allow access to this model in the admin for department heads
    def has_module_permission(self, request):
        return request.user.is_department_head()

    # Department heads can only view policies within their department
    def has_view_permission(self, request, obj=None):
        if request.user.is_department_head():
            return obj is None or obj.policy_owner == request.user.department
        return super().has_view_permission(request, obj)

    # Department heads can only change policies within their department
    def has_change_permission(self, request, obj=None):
        if request.user.is_department_head():
            return obj and obj.policy_owner == request.user.department
        return super().has_change_permission(request, obj)

    # Department heads can only add policies within their department
    def has_add_permission(self, request):
        return request.user.is_department_head()

    # Custom list_filter for department heads
    def get_list_filter(self, request):
        if request.user.is_department_head():
            return ('section', 'pub_date')
        return super().get_list_filter(request)

    # Restrict policies to those belonging to the department head's department
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_department_head() and request.user.department:
            qs = qs.filter(policy_owner=request.user.department)
        return qs


# Admin configuration for Policy Request model
class PolicyRequestAdmin(admin.ModelAdmin):
    fieldsets = [
        ("Request Information", {
            "fields": ('policy', 'first_name', 'last_name', 'email', 'question', 'submitted_at')
        }),
        ("Resolution", {
            "fields": ('is_resolved', 'admin_notes')
        }),
    ]
    readonly_fields = ('policy', 'first_name', 'last_name', 'email', 'question', 'submitted_at')  # Non-editable fields
    list_display = ('policy', 'first_name', 'last_name', 'email', 'submitted_at', 'is_resolved')
    list_filter = ('is_resolved', 'submitted_at', 'policy__section')
    search_fields = ('first_name', 'last_name', 'email', 'question', 'policy__title', 'policy__section__title')
    ordering = ('-submitted_at',)  # Order by the most recent submissions
    actions = ['mark_requests_resolved']

    # Mark selected requests as resolved.
    def mark_requests_resolved(self, request, queryset):
        count = queryset.update(is_resolved=True)
        self.message_user(request, f"{count} request(s) marked as resolved.")

    mark_requests_resolved.short_description = "Mark selected requests as resolved"

    # Prevent adding new Policy Requests manually
    def has_add_permission(self, request):
        return False


# Department Head Configuration of Policy Request model
class PolicyRequestAdminForDepartmentHead(PolicyRequestAdmin):
    def has_module_permission(self, request):
        return request.user.is_department_head()

    # Department heads can only view requests for policies within their department
    def has_view_permission(self, request, obj=None):
        if request.user.is_department_head():
            return obj is None or obj.policy.policy_owner == request.user.department
        return super().has_view_permission(request, obj)

    # Department heads can only change requests for policies within their department
    def has_change_permission(self, request, obj=None):
        if request.user.is_department_head():
            return obj and obj.policy.policy_owner == request.user.department
        return super().has_change_permission(request, obj)

    # Restrict requests to those related to policies within the department head's department
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_department_head():
            return qs.filter(policy__policy_owner=request.user.department)
        return qs


# Admin configuration for Definition model
class DefinitionAdmin(admin.ModelAdmin):
    fieldsets = [
        ("Definition Details", {
            "fields": ['term', 'definition']
        }),
    ]
    list_display = ('term_display', 'definition_display')
    search_fields = ('term', 'definition')
    ordering = ('term',)

    # Display the term
    def term_display(self, obj):
        return obj.term

    term_display.short_description = "Term"

    # Display the definition
    def definition_display(self, obj):
        return obj.definition[:75] + "..." if len(obj.definition) > 75 else obj.definition

    definition_display.short_description = "Definition"


# Executive configuration for Definition model
class DefinitionAdminForExecutive(DefinitionAdmin):
    # Allow access to this model in the admin for executives
    def has_module_permission(self, request):
        return request.user.is_executive()

    # Executives can view all definitions
    def get_queryset(self, request):
        return super().get_queryset(request)

    # Allow adding definitions
    def has_add_permission(self, request):
        return request.user.is_executive()

    # Allow editing of definitions
    def has_change_permission(self, request, obj=None):
        return request.user.is_executive()

    # Executives cannot delete definitions
    def has_delete_permission(self, request, obj=None):
        return False


# Department Head configuration for Definition model
class DefinitionAdminForDepartmentHead(DefinitionAdmin):
    # Restrict queryset to definitions related to policies owned by the department
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_department_head():
            return qs.filter(policies__policy_owner=request.user.department).distinct()
        return qs

    # Allow only view, create, and edit permissions for department heads
    def has_view_permission(self, request, obj=None):
        if request.user.is_department_head():
            return obj is None or obj.policies.filter(policy_owner=request.user.department).exists()
        return super().has_view_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if request.user.is_department_head():
            return obj is None or obj.policies.filter(policy_owner=request.user.department).exists()
        return super().has_change_permission(request, obj)

    def has_add_permission(self, request):
        return request.user.is_department_head()

    def has_delete_permission(self, request, obj=None):
        return False


# Admin configuration for Policy Section model
class PolicySectionAdmin(admin.ModelAdmin):
    fieldsets = [
        ("Policy Section Details", {
            "fields": ['number', 'title']
        }),
    ]
    list_display = ('number_display', 'title_display')
    search_fields = ('number', 'title')
    ordering = ('number',)

    # Display the policy section number
    def number_display(self, obj):
        return obj.number

    number_display.short_description = "Section Number"

    # Display the policy section title
    def title_display(self, obj):
        return obj.title

    title_display.short_description = "Section Title"


# Executive configuration for Policy Approval Request
class PolicyApprovalRequestAdmin(admin.ModelAdmin):
    fieldsets = [
        ("Current Policy", {
            "fields": [
                "current_title",
                "current_purpose",
                "current_scope",
                "current_policy_statements",
                "current_responsibilities",
                "current_related_policies",
                "current_procedure_steps",
                "current_definitions",
            ],
        }),
        ("Proposed Changes", {
            "fields": [
                "proposed_title",
                "proposed_purpose",
                "proposed_scope",
                "proposed_policy_statements",
                "proposed_responsibilities",
                "proposed_related_policies",
                "proposed_procedure_steps",
                "proposed_definitions",
            ],
        }),
        ("Approval Details", {
            "fields": ("status", "notes", "approver", "submitted_at", "updated_at"),
        }),
    ]
    list_display = ("policy", "status", "submitter", "approver", "submitted_at", "updated_at")
    list_filter = ("status", "submitted_at", "updated_at")
    ordering = ("-submitted_at",)
    readonly_fields = (
        "policy",
        "submitter",
        "approver",
        "submitted_at",
        "updated_at",
        "current_title",
        "current_purpose",
        "current_scope",
        "current_policy_statements",
        "current_responsibilities",
        "current_related_policies",
        "current_procedure_steps",
        "current_definitions",
        "proposed_title",
        "proposed_purpose",
        "proposed_scope",
        "proposed_policy_statements",
        "proposed_responsibilities",
        "proposed_related_policies",
        "proposed_procedure_steps",
        "proposed_definitions",
    )

    def has_change_permission(self, request, obj=None):
        return request.user.is_executive()

    # Computed fields for the current policy
    def current_title(self, obj):
        return obj.policy.title

    def current_purpose(self, obj):
        return obj.policy.purpose

    def current_scope(self, obj):
        return obj.policy.scope

    def current_policy_statements(self, obj):
        return obj.policy.policy_statements

    def current_responsibilities(self, obj):
        return obj.policy.responsibilities

    def current_related_policies(self, obj):
        return ", ".join([str(policy) for policy in obj.current_related_policies]) or "None"

    def current_procedure_steps(self, obj):
        return "\n".join(
            [f"Step {step.step_number}: {step.description}" for step in obj.current_procedure_steps]
        ) or "None"

    def current_definitions(self, obj):
        return "\n".join(
            [f"{definition.term}: {definition.definition}" for definition in obj.current_definitions]) or "None"

    # Short descriptions for the current policy fields
    current_title.short_description = "Current Title"
    current_purpose.short_description = "Current Purpose"
    current_scope.short_description = "Current Scope"
    current_policy_statements.short_description = "Current Policy Statements"
    current_responsibilities.short_description = "Current Responsibilities"
    current_related_policies.short_description = "Current Related Policies"
    current_procedure_steps.short_description = "Current Procedure Steps"
    current_definitions.short_description = "Current Definitions"

    # Dynamic fields for the changes
    def proposed_title(self, obj):
        return obj.proposed_title or "No Change"

    def proposed_purpose(self, obj):
        return obj.proposed_purpose or "No Change"

    def proposed_scope(self, obj):
        return obj.proposed_scope or "No Change"

    def proposed_policy_statements(self, obj):
        return obj.proposed_policy_statements or "No Change"

    def proposed_responsibilities(self, obj):
        return obj.proposed_responsibilities or "No Change"

    def proposed_related_policies(self, obj):
        policies = Policy.objects.filter(id__in=obj.proposed_related_policies)
        return ", ".join(str(policy) for policy in policies) if policies else "No Change"

    def proposed_procedure_steps(self, obj):
        return "\n".join(
            f"Step {step['step_number']}: {step['description']}"
            for step in obj.proposed_procedure_steps
        ) if obj.proposed_procedure_steps else "No Change"

    def proposed_definitions(self, obj):
        return "\n".join(
            f"{definition['term']}: {definition['definition']}"
            for definition in obj.proposed_definitions
        ) if obj.proposed_definitions else "No Change"

    # Short descriptions for the proposed changes
    proposed_title.short_description = "Proposed Title"
    proposed_purpose.short_description = "Proposed Purpose"
    proposed_scope.short_description = "Proposed Scope"
    proposed_policy_statements.short_description = "Proposed Policy Statements"
    proposed_responsibilities.short_description = "Proposed Responsibilities"
    proposed_related_policies.short_description = "Proposed Related Policies"
    proposed_procedure_steps.short_description = "Proposed Procedure Steps"
    proposed_definitions.short_description = "Proposed Definitions"

    # Handle status changes
    def save_model(self, request, obj, form, change):
        if change:
            # Automatically assign the current user as the approver
            if obj.status in ["approved", "revision_needed", "rejected"]:
                if request.user == obj.submitter:
                    raise ValidationError("An executive cannot approve their own request.")
                obj.approver = request.user

            # Apply changes if the request is approved
            if obj.status == "approved":
                obj.apply_changes()

            # Notify submitter if the request requires revision or is rejected
            elif obj.status in ["revision_needed", "rejected"]:
                self.notify_submitter(obj)
        super().save_model(request, obj, form, change)

    def notify_submitter(self, obj):
        submitter_email = obj.submitter.email
        status_message = "revision needed" if obj.status == "revision_needed" else "rejected"
        send_mailgun_email(
            to_email=submitter_email,
            subject=f"Policy Change Request {status_message.capitalize()}",
            variables={
                "policy_number": obj.policy.number,
                "policy_title": obj.policy.title,
                "status_message": status_message,
                "notes": obj.notes or "No additional notes provided.",
            },
        )


# Register handbook models to super admin
super_admin_site.register(PolicySection, PolicySectionAdmin)
super_admin_site.register(Policy, PolicyAdmin)
super_admin_site.register(Definition, DefinitionAdmin)
super_admin_site.register(PolicyRequest, PolicyRequestAdmin)

# Register accounts models to super admin
super_admin_site.register(CustomUser, CustomUserAdmin)
super_admin_site.register(Department, DepartmentAdmin)

# Register models with the executive admin site
executive_admin_site.register(Policy, PolicyAdminForExecutive)
executive_admin_site.register(Definition, DefinitionAdminForExecutive)
executive_admin_site.register(PolicyApprovalRequest, PolicyApprovalRequestAdmin)

# Register models with the department head admin site
department_head_admin.register(Policy, PolicyAdminForDepartmentHead)
department_head_admin.register(PolicyRequest, PolicyRequestAdminForDepartmentHead)
department_head_admin.register(Definition, DefinitionAdminForDepartmentHead)
