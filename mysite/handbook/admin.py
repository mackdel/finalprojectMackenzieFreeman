from django.db import models
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import admin
from .models import PolicySection, Policy, Definition, PolicyFeedback, ProcedureStep, PolicyApprovalRequest, ArchivedPolicy
from accounts.models import CustomUser, Department
from accounts.admin import CustomUserAdmin, DepartmentAdmin

"""
Custom admin sites for different user roles (Super Admins, Executives, Department Heads).
Each site is tailored to match the permissions and views required by the respective roles.
"""

# Custom Admin site for Super Admins
class SuperAdminSite(admin.AdminSite):
    # Define the headers and titles for the admin portal
    site_header = "Handbook Admin Portal"
    site_title = "Handbook Site Admin"
    index_title = "Welcome to the Handbook Admin Dashboard"
    site_url = "/handbook/" # Default URL for the handbook site

# Instantiate the SuperAdminSite
super_admin_site = SuperAdminSite(name="super_admin")


# Custom Admin site for Executives
class ExecutiveAdminSite(admin.AdminSite):
    # Define the headers and titles for the executive portal
    site_header = "Executive Portal"
    site_title = "Executive Site Admin"
    index_title = "Welcome to the Executive Dashboard"
    site_url = "/handbook/"

    # Restrict access to only authenticated executive users
    def has_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_executive()

# Instantiate the ExecutiveAdminSite
executive_admin_site = ExecutiveAdminSite(name="executive_admin")


# Custom Admin site for Department Heads
class DepartmentHeadAdminSite(admin.AdminSite):
    # Define the headers and titles for the department head portal
    site_header = "Department Head Portal"
    site_title = "Department Head Site Admin"
    index_title = "Welcome to the Department Head Dashboard"
    site_url = "/handbook/"

    # Restrict access to authenticated users with the department head role
    def has_permission(self, request):
        if not request.user.is_authenticated:
            return False
        if request.user.is_department_head():
            # Ensure department heads have permissions to view procedure steps and definitions
            return request.user.has_perm('handbook.view_procedurestep') and request.user.has_perm('handbook.view_definition')
        return False

# Instantiate the DepartmentHeadAdminSite
department_head_admin = DepartmentHeadAdminSite(name="department_head_admin")


# Inline configuration for Procedure Steps in Policies
class ProcedureStepInline(admin.TabularInline):
    model = ProcedureStep
    fields = ['step_number', 'description']
    extra = 0  # Do not show extra rows for adding steps by default
    ordering = ['step_number']  # Ensure steps are ordered by their number
    can_delete = True # Allow deletion of steps

    # Permissions to add procedure steps
    def has_add_permission(self, request, obj=None):
        return request.user.is_department_head() or request.user.is_superuser or request.user.is_executive()

    # Permissions to edit procedure steps
    def has_change_permission(self, request, obj=None):
        return request.user.is_department_head() or request.user.is_superuser or request.user.is_executive()

    # Permissions to delete procedure steps
    def has_delete_permission(self, request, obj=None):
        return request.user.is_department_head() or request.user.is_superuser or request.user.is_executive()

    # Customize the queryset to ensure steps are always ordered by step number
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('step_number')


# Inline configuration for Definitions in Policies
class DefinitionInline(admin.TabularInline):
    model = Policy.definitions.through # Many-to-Many relationship through model
    extra = 1  # Show one empty row for adding definitions
    verbose_name = "Definition" # Label for a single definition
    verbose_name_plural = "Definitions" # Label for multiple definitions

    # Restrict available definitions to those related to department head's policies or created by the user
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "definition":
            if request.user.is_department_head():
                # Include definitions linked to policies owned by the department
                department_definitions = Definition.objects.filter(
                    policies__policy_owner=request.user.department
                )
                # Include definitions created by the user
                user_created_definitions = Definition.objects.filter(created_by=request.user)
                # Combine both querysets
                kwargs["queryset"] = (department_definitions | user_created_definitions).distinct()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # Permissions to add definitions
    def has_add_permission(self, request, obj=None):
        return request.user.is_department_head() or request.user.is_superuser or request.user.is_executive()

    # Permissions to edit definitions
    def has_change_permission(self, request, obj=None):
        return request.user.is_department_head() or request.user.is_superuser or request.user.is_executive()

    # Permissions to delete definitions
    def has_delete_permission(self, request, obj=None):
        return request.user.is_department_head()  or request.user.is_superuser or request.user.is_executive()


# Admin configuration for Policy model
class PolicyAdmin(admin.ModelAdmin):
    # Define sections for editing policies
    fieldsets = [
        ("Policy Information", {
            "fields": ["section", "title", "number", "version", "policy_owner", "pub_date", "updated_at", "review_period"]
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
    readonly_fields = ["number", "pub_date", "updated_at", "version", "policy_owner"]
    list_display = ["number", "title", "section", "policy_owner", "pub_date", "version"]
    list_filter = ["section", "policy_owner", "pub_date"]
    search_fields = ["title", "policy_statements", "section__title"]
    ordering = ["section", "number"]  # Default ordering of policies
    filter_horizontal = ["related_policies"]  # Horizontal widget for managing related policies

    # Inline models for editing procedure steps and definitions
    inlines = [ProcedureStepInline, DefinitionInline]

    def get_fieldsets(self, request, obj=None):
        # Adjust fieldsets when creating a new policy
        if obj is None:  # Adding a new policy
            return [
                ("Policy Information", {
                    "fields": ["section", "title", "policy_owner", "review_period"]
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
        return super().get_fieldsets(request, obj)

    # Dynamically adjust readonly fields based on user role and policy state:
    def get_readonly_fields(self, request, obj=None):
        # Start with the default readonly fields
        readonly_fields = self.readonly_fields.copy()

        # Remove `policy_owner` from readonly fields for superusers and admins
        if request.user.is_superuser or request.user.is_admin():
            readonly_fields = [field for field in readonly_fields if field != "policy_owner"]

        # Add `section` to readonly fields when editing an existing policy
        if obj:
            readonly_fields += ["section"]

        return readonly_fields

    # For archiving policies
    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        # Add the archive button URL to the context
        extra_context['archive_url'] = reverse('handbook:archive_policy', kwargs={'policy_id': object_id})
        return super().change_view(request, object_id, form_url, extra_context)

    # Save logic for creating and editing policies
    def save_model(self, request, obj, form, change):
        # Bypass approval workflow for superusers and admins
        if request.user.is_superuser or request.user.is_admin():
            super().save_model(request, obj, form, change)

        else:
            # Other roles trigger the approval workflow
            if not change:
                # Manually generate the policy number without saving the Policy object
                section_prefix = obj.section.number.split(".")[0]
                policy_count = Policy.objects.filter(section=obj.section).count()
                obj.number = f"{section_prefix}.{policy_count + 1}"
                obj.policy_owner = request.user.department

                # Save unsaved changes to the session for creating a PolicyApprovalRequest
                unsaved_changes = {
                    "section": obj.section.id,
                    "number": obj.number,
                    "title": form.cleaned_data["title"],
                    "policy_owner": obj.policy_owner.id if obj.policy_owner else None,
                    "review_period": form.cleaned_data["review_period"],
                    "purpose": form.cleaned_data["purpose"],
                    "scope": form.cleaned_data["scope"],
                    "policy_statements": form.cleaned_data["policy_statements"],
                    "responsibilities": form.cleaned_data["responsibilities"],
                }
                request.session["is_policy_creation"] = True
                # Store unsaved changes in the session
                request.session["unsaved_policy_changes"] = unsaved_changes
            else:
                # Capture unsaved changes to policy fields
                unsaved_changes = {}

                # Loop through all form fields and capture changes
                for field, value in form.cleaned_data.items():
                    # Check if the field exists on the policy model
                    if hasattr(obj, field):
                        field_obj = obj._meta.get_field(field)
                        # For ForeignKey fields, store the primary key
                        if isinstance(field_obj, models.ForeignKey):
                            value = value.pk if value else None
                        # For ManyToMany fields, store the list of related IDs
                        elif isinstance(field_obj, models.ManyToManyField):
                            value = list(value.values_list("id", flat=True))
                        # Store the updated field value in the unsaved_changes
                        unsaved_changes[field] = value

                request.session["policy_id"] = obj.id

                # Store unsaved changes in the session
                request.session["unsaved_policy_changes"] = unsaved_changes

            # Do not save changes to the database yet
            return

    # Save related objects (e.g., related policies, procedure steps, definitions)
    def save_related(self, request, form, formsets, change):
        # Allow direct saving for superusers and admins
        if request.user.is_superuser or request.user.is_admin():
            # Allow direct saving for superusers and admins
            super().save_related(request, form, formsets, change)

        else:
            # Follow the existing session-based logic for other roles
            if request.session.get("is_policy_creation", False):
                unsaved_changes = request.session.get("unsaved_policy_changes", {})

                # Capture related policies for a new policy
                related_policies = form.cleaned_data.get("related_policies", [])
                if related_policies:
                    # Store related policy IDs
                    unsaved_changes["related_policies"] = list(related_policies.values_list("id", flat=True))

                procedure_steps = []
                definitions = []

                for formset in formsets:
                    if formset.model == ProcedureStep:
                        for form in formset.forms:
                            if not form.cleaned_data.get("DELETE", False):
                                procedure_steps.append({
                                    "step_number": form.cleaned_data["step_number"],
                                    "description": form.cleaned_data["description"],
                                })
                    elif formset.model == Policy.definitions.through:
                        for form in formset.forms:
                            definition = form.cleaned_data.get("definition")
                            if definition and not form.cleaned_data.get("DELETE", False):
                                definitions.append({
                                    "id": definition.id,
                                    "term": definition.term,
                                    "definition": definition.definition,
                                })

            else:
                # Retrieve the policy ID from the session
                policy_id = request.session.get("policy_id")
                if policy_id:
                    # Fetch the policy object based on the policy ID
                    policy = Policy.objects.get(id=policy_id)

                    # Retrieve any basic changes saved in the session for the policy
                    unsaved_changes = request.session.get("unsaved_policy_changes", {})

                    # Capture the list of related policies from the form data or use the existing related policies
                    related_policies = form.cleaned_data.get("related_policies", policy.related_policies.all())
                    # Store the related policy IDs in the unsaved_changes
                    unsaved_changes["related_policies"] = list(related_policies.values_list("id", flat=True))

                    procedure_steps = [] # To store all procedure step changes
                    definitions = [] # To store all definition changes

                    # Iterate over all formsets to handle specific inline models
                    for formset in formsets:
                        # Handle procedure steps
                        if formset.model == ProcedureStep:
                            updated_steps = [] # Temporarily store updated steps

                            # Iterate over each form in the procedure steps formset
                            for form in formset.forms:
                                # If a step is marked for deletion, include it in the procedure_steps with DELETE flag
                                if form.cleaned_data.get("DELETE", False):
                                    obj = form.instance
                                    procedure_steps.append({
                                        "id": obj.id,
                                        "step_number": obj.step_number,
                                        "description": obj.description,
                                        "DELETE": True,
                                    })
                                # Else include step in the procedure_steps with normal data
                                else:
                                    instance = form.instance
                                    if instance.description: # Ensure meaningful data exists
                                        updated_steps.append(instance)

                            # Sort updated steps by step number and renumber them in memory
                            updated_steps.sort(key=lambda x: x.step_number)
                            for index, step in enumerate(updated_steps, start=1):
                                procedure_steps.append({
                                    "id": step.id,
                                    "step_number": index,  # Renumbered step number
                                    "description": step.description,
                                })

                        # Handle definitions
                        elif formset.model == Policy.definitions.through:
                            # Iterate over each form in the definitions formset
                            for form in formset.forms:
                                definition_instance = form.cleaned_data.get("definition") # Retrieve the definition object
                                if definition_instance:
                                    # If marked for deletion, include it with the DELETE flag
                                    if form.cleaned_data.get("DELETE", False):
                                        definitions.append({
                                            "id": definition_instance.id,
                                            "term": definition_instance.term,
                                            "definition": definition_instance.definition,
                                            "DELETE": True,
                                        })
                                    # Else add the definition data to the unsaved changes
                                    else:
                                        definitions.append({
                                            "id": definition_instance.id,
                                            "term": definition_instance.term,
                                            "definition": definition_instance.definition,
                                    })

            # Update session with changes
            unsaved_changes["procedure_steps"] = procedure_steps
            unsaved_changes["definitions"] = definitions
            request.session["unsaved_policy_changes"] = unsaved_changes

            print("Save Related", unsaved_changes)

            # Do not save changes to the database yet
            return

    def response_change(self, request, obj):
        # Check if the user is a superuser or admin
        if request.user.is_superuser or request.user.is_admin():
            # Admins bypass the questionnaire redirect
            return super().response_change(request, obj)

        # Redirect other users to the major change questionnaire
        if "_save" in request.POST:
            questionnaire_url = reverse("handbook:major_change_questionnaire", kwargs={"policy_id": obj.id})
            return HttpResponseRedirect(questionnaire_url)

        return super().response_change(request, obj)

    # Response handling for adding new policies
    def response_add(self, request, obj, post_url_continue=None):
        if request.user.is_superuser or request.user.is_admin():
            # Redirect directly for superusers and admins
            return HttpResponseRedirect(reverse("admin:handbook_policy_changelist"))
        else:
            # Follow the approval workflow
            unsaved_changes = request.session.get("unsaved_policy_changes", {})
            # Create a policy approval request for the new policy
            self._create_policy_approval_request(request, unsaved_changes, request_type="new")
            self.message_user(
                request,
                f"New policy '{unsaved_changes['title']} has been submitted for approval.",
                level="success"
            )

            # Redirect to the policy change list
            return HttpResponseRedirect(reverse("admin:handbook_policy_changelist"))

    # Creates a PolicyApprovalRequest using the stored unsaved changes
    def _create_policy_approval_request(self, request, unsaved_changes, request_type="edit"):
        PolicyApprovalRequest.objects.create(
            submitter=request.user,
            request_type='new',
            status="pending",
            policy_owner=Department.objects.get(id=unsaved_changes["policy_owner"]),
            section=PolicySection.objects.get(id=unsaved_changes["section"]),
            proposed_title=unsaved_changes["title"],
            proposed_review_period=unsaved_changes["review_period"],
            proposed_purpose=unsaved_changes["purpose"],
            proposed_scope=unsaved_changes["scope"],
            proposed_policy_statements=unsaved_changes["policy_statements"],
            proposed_responsibilities=unsaved_changes["responsibilities"],
            proposed_related_policies=unsaved_changes.get("related_policies", []),
            proposed_procedure_steps=unsaved_changes.get("procedure_steps", []),
            proposed_definitions=unsaved_changes.get("definitions", []),
        )

    # Construct a change message that avoids accessing new_objects
    def construct_change_message(self, request, form, formsets, add=False):
        change_message = []

        # Capture changed fields in the form
        if form.changed_data:
            change_message.append(f"Changed fields: {', '.join(form.changed_data)}")

        # Handle changes in formsets
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

    # Grant module access only to executives
    def has_module_permission(self, request):
        return request.user.is_executive()

    # Grant module access only to executives
    def has_change_permission(self, request, obj=None):
        return request.user.is_executive()

    # Allow executives to add new policies
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

    # Grant module access only to department heads
    def has_module_permission(self, request):
        return request.user.is_department_head()

    # Allow department heads to view policies within their department
    def has_view_permission(self, request, obj=None):
        if request.user.is_department_head():
            return obj is None or obj.policy_owner == request.user.department
        return super().has_view_permission(request, obj)

    # Allow department heads to edit policies within their department
    def has_change_permission(self, request, obj=None):
        if request.user.is_department_head():
            return obj and obj.policy_owner == request.user.department
        return super().has_change_permission(request, obj)

    # Allow department heads to add policies to their department
    def has_add_permission(self, request):
        return request.user.is_department_head()

    # Customize the list filter for department heads
    def get_list_filter(self, request):
        # Limit to only filter by section and publish date
        if request.user.is_department_head():
            return ('section', 'pub_date')
        return super().get_list_filter(request)

    # Restrict policies to those belonging to the department head's department
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_department_head() and request.user.department:
            qs = qs.filter(policy_owner=request.user.department)
        return qs


# Admin configuration for Policy Feedback model
class PolicyFeedbackAdmin(admin.ModelAdmin):
    fieldsets = [
        ("Request Information", {
            "fields": ('policy', 'first_name', 'last_name', 'email', 'question', 'submitted_at')
        }),
        ("Resolution", {
            "fields": ('is_resolved', 'admin_notes')
        }),
    ]
    readonly_fields = ('policy', 'first_name', 'last_name', 'email', 'question', 'submitted_at')
    list_display = ('policy', 'first_name', 'last_name', 'email', 'submitted_at', 'is_resolved')
    list_filter = ('is_resolved', 'submitted_at', 'policy__section')
    search_fields = ('first_name', 'last_name', 'email', 'question', 'policy__title', 'policy__section__title')
    ordering = ('-submitted_at',)  # Default ordering: newest submissions first

    actions = ['mark_feedbacks_resolved'] # Custom admin action
    # Custom admin action to mark selected feedback as resolved
    def mark_feedbacks_resolved(self, request, queryset):
        count = queryset.update(is_resolved=True) # Update the is_resolved field for selected feedbacks
        self.message_user(request, f"{count} feedback(s) marked as resolved.") # Display a success message
    # Description for the action
    mark_feedbacks_resolved.short_description = "Mark selected feedbacks as resolved"

    # Prevent adding new Policy Feedback manually
    def has_add_permission(self, request):
        return False


# Department Head Configuration of Policy Feedback model
class PolicyFeedbackAdminForDepartmentHead(PolicyFeedbackAdmin):
    # Grant module access only to department heads
    def has_module_permission(self, request):
        return request.user.is_department_head()

    # Allow department heads to view feedback for their department's policies
    def has_view_permission(self, request, obj=None):
        if request.user.is_department_head():
            return obj is None or obj.policy.policy_owner == request.user.department
        return super().has_view_permission(request, obj)

    # Allow department heads to resolve feedback for their department's policies
    def has_change_permission(self, request, obj=None):
        if request.user.is_department_head():
            return obj and obj.policy.policy_owner == request.user.department
        return super().has_change_permission(request, obj)

    # Restrict queryset to feedback related to policies within the department head's department
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
    list_display = ['term_display', 'definition_display']
    search_fields = ['term', 'definition']
    ordering = ['term',] # Default ordering: alphabetically by term

    # Display the term in the list view
    def term_display(self, obj):
        return obj.term
    # Label for the column
    term_display.short_description = "Term"

    # Display a shortened version of the definition in the list view
    def definition_display(self, obj):
        return obj.definition[:75] + "..." if len(obj.definition) > 75 else obj.definition
    # Label for the column
    definition_display.short_description = "Definition"

    # Automatically set the `created_by` field when saving
    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# Executive configuration for Definition model
class DefinitionAdminForExecutive(DefinitionAdmin):
    # Grant module access only to executives
    def has_module_permission(self, request):
        return request.user.is_executive()

    # Allow executives to view all definitions
    def get_queryset(self, request):
        return super().get_queryset(request)

    # Allow executives to add new definitions
    def has_add_permission(self, request):
        return request.user.is_executive()

    # Allow executives to edit definitions
    def has_change_permission(self, request, obj=None):
        return request.user.is_executive()

    # Executives cannot delete definitions
    def has_delete_permission(self, request, obj=None):
        return False


# Department Head configuration for Definition model
class DefinitionAdminForDepartmentHead(DefinitionAdmin):
    # Restrict queryset to definitions related to policies owned by the department or created by the department head
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_department_head():
            # Include definitions linked to policies owned by the department
            linked_definitions = qs.filter(policies__policy_owner=request.user.department)
            # Include definitions created by the current user (assuming a creator field)
            user_created_definitions = qs.filter(created_by=request.user)
            # Combine both querysets
            return (linked_definitions | user_created_definitions).distinct()
        return qs

    # Allow department heads to view definitions linked to their department's policies or their own
    def has_view_permission(self, request, obj=None):
        if request.user.is_department_head():
            # Allow if the definition is linked to a policy owned by their department or created by the user
            return obj is None or obj.policies.filter(policy_owner=request.user.department).exists() or obj.created_by == request.user
        return super().has_view_permission(request, obj)

    # Allow department heads to edit definitions linked to their department's policies or their own
    def has_change_permission(self, request, obj=None):
        if request.user.is_department_head():
            # Allow if the definition is linked to a policy owned by their department or created by the user
            return obj is None or obj.policies.filter(policy_owner=request.user.department).exists() or obj.created_by == request.user
        return super().has_change_permission(request, obj)

    # Allow department heads to add definitions
    def has_add_permission(self, request):
        return request.user.is_department_head()

    # Restrict department heads from deleting definitions
    def has_delete_permission(self, request, obj=None):
        return False



# Admin configuration for Policy Section model
class PolicySectionAdmin(admin.ModelAdmin):
    fieldsets = [
        ("Policy Section Details", {
            "fields": ['number', 'title']
        }),
    ]
    list_display = ['number_display', 'title_display']
    search_fields = ['number', 'title']
    ordering = ['number',] # Default ordering: numerically by section number

    # Display the section number in the list view
    def number_display(self, obj):
        return obj.number
    # Label for the column
    number_display.short_description = "Section Number"

    # Display the section title in the list view
    def title_display(self, obj):
        return obj.title
    # Label for the column
    title_display.short_description = "Section Title"


# Admin configuration for Policy Approval Request
class PolicyApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ["get_policy_or_proposed_title", "request_type",  "status", "submitter", "submitted_at"]

    # Determines the displayed field
    def get_policy_or_proposed_title(self, obj):
        if obj.request_type == 'new':
            return obj.proposed_title or "No Title Proposed"
        elif obj.request_type in ['edit', 'archive'] and obj.policy:
            return obj.policy.title
        elif obj.archived_policy:
            return obj.archived_policy.title
        return "No Policy Linked"

    get_policy_or_proposed_title.short_description = "Policy"

    list_filter = ["status", "request_type", "section", "submitted_at"]
    ordering = ["-submitted_at",]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = [
                "policy", "section", "number", "policy_owner", "submitter",
                "approver", "submitted_at", "updated_at", "current_review_period",
                "current_version", "current_title", "current_purpose", "current_scope",
                "current_policy_statements", "current_responsibilities",
                "current_related_policies", "current_procedure_steps",
                "current_definitions",
                    "get_proposed_title",
                    "get_proposed_review_period",
                    "get_proposed_purpose",
                    "get_proposed_scope",
                    "get_proposed_policy_statements",
                    "get_proposed_responsibilities",
                    "get_proposed_related_policies",
                    "get_proposed_procedure_steps",
                    "get_proposed_definitions",
            ]
        if obj:
            # For approved/rejected requests, all fields are readonly
            if obj.status in ["approved", "rejected", "revision_needed"]:
                return readonly_fields + [
                    "status", "notes"
                ]
            return readonly_fields
        return super().get_readonly_fields(request, obj)

    # Dynamically adjust fieldsets based on the `request_type` of the policy approval request
    def get_fieldsets(self, request, obj=None):
        base_fieldsets = [
            ("Approval Details", {
                "fields": ("status", "notes", "approver", "submitted_at", "updated_at"),
            }),
        ]

        if obj:
            if obj.request_type == "edit":
                base_fieldsets.insert(0, ("Current Policy Details", {
                    "fields": [
                        "section", "current_title", "current_version", "policy_owner", "current_review_period",
                        "current_purpose", "current_scope", "current_policy_statements", "current_responsibilities",
                        "current_related_policies", "current_procedure_steps", "current_definitions",
                    ],
                }))
                base_fieldsets.insert(1, ("Proposed Changes",  {
                    "fields": [
                        "get_proposed_title", "get_proposed_review_period", "get_proposed_purpose",
                        "get_proposed_scope", "get_proposed_policy_statements", "get_proposed_responsibilities",
                        "get_proposed_related_policies","get_proposed_procedure_steps", "get_proposed_definitions",
                    ],
                }))
            elif obj.request_type == "new":
                base_fieldsets.insert(0, ("New Policy Details", {
                    "fields": [
                        "section", "get_proposed_title", "policy_owner", "get_proposed_review_period",
                        "get_proposed_purpose", "get_proposed_scope", "get_proposed_policy_statements",
                        "get_proposed_responsibilities", "get_proposed_related_policies", "get_proposed_procedure_steps",
                        "get_proposed_definitions",
                    ],
                }))
            elif obj.request_type == "archive" and obj.status != "approved":
                base_fieldsets.insert(0, ("Policy Details", {
                    "fields": [
                        "section", "current_title", "current_version", "policy_owner", "current_review_period", "current_purpose",
                        "current_scope", "current_policy_statements", "current_responsibilities", "current_related_policies",
                        "current_procedure_steps", "current_definitions",
                    ],
                }))
        return base_fieldsets

    # Computed fields for the current policy
    # These methods retrieve and display data from the current policy associated with the approval request
    def current_title(self, obj):
        return obj.policy.title

    def current_version(self, obj):
        return obj.policy.version

    def current_review_period(self, obj):
        return obj.policy.review_period

    def current_purpose(self, obj):
        return obj.policy.purpose

    def current_scope(self, obj):
        return obj.policy.scope

    def current_policy_statements(self, obj):
        return obj.policy.policy_statements

    def current_responsibilities(self, obj):
        return obj.policy.responsibilities

    def current_related_policies(self, obj):
        # Format the related policies as a list
        return "\n".join([str(policy) for policy in obj.policy.related_policies.all()]) or "None"

    def current_procedure_steps(self, obj):
        # Format procedure steps as a numbered list
        return "\n".join(
            [f"Step {step.step_number}: {step.description}" for step in ProcedureStep.objects.filter(policy=obj.policy).order_by("step_number")]
        ) or "None"

    def current_definitions(self, obj):
        # Format definitions as a list of terms with their corresponding definitions
        return "\n".join(
            [f"{definition.term}: {definition.definition}" for definition in obj.policy.definitions.all()]
        ) or "None"

    # Short descriptions for the current policy fields
    current_title.short_description = "Current Title"
    current_version.short_description = "Version"
    current_review_period.short_description = "Current Review Period"
    current_purpose.short_description = "Current Purpose"
    current_scope.short_description = "Current Scope"
    current_policy_statements.short_description = "Current Policy Statements"
    current_responsibilities.short_description = "Current Responsibilities"
    current_related_policies.short_description = "Current Related Policies"
    current_procedure_steps.short_description = "Current Procedure Steps"
    current_definitions.short_description = "Current Definitions"

    # Computed fields for the proposed changes
    # These methods retrieve and display the proposed changes submitted with the approval request
    def get_proposed_title(self, obj):
        return obj.proposed_title or "None"

    def get_proposed_purpose(self, obj):
        return obj.proposed_purpose or "None"

    def get_proposed_scope(self, obj):
        return obj.proposed_scope or "None"

    def get_proposed_policy_statements(self, obj):
        return obj.proposed_policy_statements or "None"

    def get_proposed_responsibilities(self, obj):
        return obj.proposed_responsibilities or "None"

    def get_proposed_review_period(self, obj):
        return obj.proposed_review_period or "None"

    def get_proposed_related_policies(self, obj):
        # Format the proposed related policies as a list
        policies = Policy.objects.filter(id__in=obj.proposed_related_policies)
        return "\n".join(str(policy) for policy in policies) if policies else "None"

    def get_proposed_procedure_steps(self, obj):
        # Format proposed procedure steps as a numbered list
        return "\n".join(
            f"Step {step['step_number']}: {step['description']}"
            for step in obj.proposed_procedure_steps
        ) if obj.proposed_procedure_steps else "None"

    def get_proposed_definitions(self, obj):
        # Format proposed definitions as a list of terms with their corresponding definitions
        return "\n".join(
            f"{definition['term']}: {definition['definition']}"
            for definition in obj.proposed_definitions
        ) if obj.proposed_definitions else "None"

    # Short descriptions for the proposed changes
    get_proposed_title.short_description = "Proposed Title"
    get_proposed_review_period.short_description = "Proposed Review Period"
    get_proposed_purpose.short_description = "Proposed Purpose"
    get_proposed_scope.short_description = "Proposed Scope"
    get_proposed_policy_statements.short_description = "Proposed Policy Statements"
    get_proposed_responsibilities.short_description = "Proposed Responsibilities"
    get_proposed_related_policies.short_description = "Proposed Related Policies"
    get_proposed_procedure_steps.short_description = "Proposed Procedure Steps"
    get_proposed_definitions.short_description = "Proposed Definitions"

    # Prevent adding new Policy Approval Requests manually
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if obj:
            if request.user.is_executive() or request.user.is_admin() or request.user.is_superuser:
                if obj.submitter == request.user:
                    return False  # Cannot apporve of own policy
                # Executives can edit requests they didn't submit unless approved/rejected
                return obj.status not in ["approved", "rejected", "revision_needed"]
        return super().has_change_permission(request, obj)

    # Handle status changes
    def save_model(self, request, obj, form, change):
        if change:
            # Apply changes if the request is approved
            if obj.status == "approved":
                obj.approver = request.user # Automatically assign the current user as the approver
                obj.apply_changes()

            # Notify submitter if the request requires revision or is rejected
            # elif obj.status in ["revision_needed", "rejected"]:

        # Save the changes
        super().save_model(request, obj, form, change)


# Executive configuration for Policy Approval Request
class PolicyApprovalRequestAdminForExecutive(PolicyApprovalRequestAdmin):
    def has_view_permission(self, request, obj=None):
        return request.user.is_executive()


# Dept Head configuration for Policy Approval Request
class PolicyApprovalRequestAdminForDeptHead(PolicyApprovalRequestAdmin):
    # Filter queryset for department heads
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(policy_owner=request.user.department)

    # Allow viewing only if the request belongs to the user's department
    def has_view_permission(self, request, obj=None):
        return obj is None or obj.policy_owner == request.user.department

    def has_change_permission(self, request, obj=None):
        return False


# Admin configuration for Archived Policy
class ArchivedPolicyAdmin(admin.ModelAdmin):
    fieldsets = [
        ("Archived Policy Details", {
            "fields": (
                'section',
                'number',
                'title',
                'version',
                'policy_owner',
                'archived_at',
                'review_period',
                'purpose',
                'scope',
                'policy_statements',
                'responsibilities',
                'formatted_related_policies',
                'formatted_procedure_steps',
                'formatted_definitions',
            )
        }),
    ]
    list_display = ["number", "title", "section", "policy_owner", "archived_at"]
    search_fields = ["title", "number", "section__title"]
    list_filter = ["section", "archived_at"]
    readonly_fields = [
        'section',
        'number',
        'title',
        'version',
        'policy_owner',
        'archived_at',
        'review_period',
        'purpose',
        'scope',
        'policy_statements',
        'responsibilities',
        'formatted_related_policies',
        'formatted_procedure_steps',
        'formatted_definitions',
    ]

    # Format Some Fields
    def formatted_related_policies(self, obj):
        related_policies = obj.related_policies.all()
        if not related_policies:
            return "None"
        return "\n".join(str(policy) for policy in related_policies)

    def formatted_procedure_steps(self, obj):
        if not obj.procedure_steps_json:
            return "None"
        return "\n".join(
            f"Step {step['step_number']}: {step['description']}"
            for step in obj.procedure_steps_json
        )

    def formatted_definitions(self, obj):
        definitions = obj.definitions.all()
        if not definitions:
            return "None"
        return "\n".join(
            f"{definition.term}: {definition.definition}" for definition in definitions
        )

    formatted_related_policies.short_description = "Related Policies"
    formatted_procedure_steps.short_description = "Procedure Steps"
    formatted_definitions.short_description = "Definitions"

    # Restrict view and edit permissions
    def has_view_permission(self, request, obj=None):
        return request.user.is_executive()

    def has_change_permission(self, request, obj=None):
        return False


# Register handbook models to super admin
super_admin_site.register(PolicySection, PolicySectionAdmin)
super_admin_site.register(Policy, PolicyAdmin)
super_admin_site.register(Definition, DefinitionAdmin)
super_admin_site.register(PolicyFeedback, PolicyFeedbackAdmin)
super_admin_site.register(PolicyApprovalRequest, PolicyApprovalRequestAdmin)

# Register accounts models to super admin
super_admin_site.register(CustomUser, CustomUserAdmin)
super_admin_site.register(Department, DepartmentAdmin)

# Register models with the executive admin site
executive_admin_site.register(Policy, PolicyAdminForExecutive)
executive_admin_site.register(Definition, DefinitionAdminForExecutive)
executive_admin_site.register(PolicyApprovalRequest, PolicyApprovalRequestAdminForExecutive)
executive_admin_site.register(ArchivedPolicy, ArchivedPolicyAdmin)

# Register models with the department head admin site
department_head_admin.register(Policy, PolicyAdminForDepartmentHead)
department_head_admin.register(PolicyFeedback, PolicyFeedbackAdminForDepartmentHead)
department_head_admin.register(Definition, DefinitionAdminForDepartmentHead)
department_head_admin.register(PolicyApprovalRequest, PolicyApprovalRequestAdminForDeptHead)