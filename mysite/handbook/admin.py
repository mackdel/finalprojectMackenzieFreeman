from django.contrib import admin
from .models import PolicySection, Policy, Definition, PolicyRequest, ProcedureStep
from accounts.models import CustomUser, Department
from accounts.admin import CustomUserAdmin, DepartmentAdmin

# Custom Admin site for Super Admins
class SuperAdminSite(admin.AdminSite):
    site_header = "Handbook Admin Portal"
    site_title = "Handbook Site Admin"
    index_title = "Welcome to the Handbook Admin Dashboard"
    site_url = "/handbook/"

super_admin_site = SuperAdminSite(name="super_admin")

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
    extra = 1  # Start with one empty row for adding steps
    ordering = ['step_number']  # Order steps by their number
    can_delete = True

    def has_add_permission(self, request, obj=None):
        return request.user.is_department_head() or request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_department_head() or request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_department_head() or request.user.is_superuser

    # Ensure steps are always ordered correctly in the admin.
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('step_number')


# Inline configuration for Definitions in Policies
class DefinitionInline(admin.TabularInline):
    model = Policy.definitions.through
    extra = 1  # Start with one empty row for adding definitions
    verbose_name = "Definition"
    verbose_name_plural = "Definitions"

    def has_add_permission(self, request, obj=None):
        return request.user.is_department_head() or request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_department_head() or request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_department_head() or request.user.is_superuser


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
    readonly_fields = ["section", "number", "policy_owner", "pub_date", "version"]  # Fields that should not be editable
    list_display = ["number", "title", "section", "policy_owner", "pub_date", "version"]
    list_filter = ["section", "policy_owner", "pub_date"]
    search_fields = ["title", "policy_statements", "section__title"]
    ordering = ["section", "number"]
    filter_horizontal = ["related_policies"]  # Horizontal widget for managing related policies
    inlines = [ProcedureStepInline, DefinitionInline]

    # Handle saving, renumbering, and deletions for ProcedureStep in a policy.
    def save_formset(self, request, form, formset, change):
        if formset.model == ProcedureStep:
            # Iterate through formset forms
            for form in formset.forms:
                if form.cleaned_data.get('DELETE', False):
                    # Delete the object if marked for deletion
                    obj = form.instance
                    obj.delete()

            # Save the remaining objects
            instances = formset.save(commit=False)
            for instance in instances:
                instance.save()

            # Renumber remaining steps
            steps = ProcedureStep.objects.filter(policy=form.instance.policy).order_by('step_number')
            for index, step in enumerate(steps, start=1):
                step.step_number = index
                step.save(update_fields=['step_number'])

            formset.save_m2m()  # Save many-to-many relationships
        else:
            formset.save()


# Department Head Configuration of Policy Model
class PolicyAdminForDepartmentHead(PolicyAdmin):
    inlines = [ProcedureStepInline, DefinitionInline]

    # Allow access to this model in the admin for department heads
    def has_module_permission(self, request):
        return request.user.is_department_head()

    # Department heads can only view policies within their department
    def has_view_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        if request.user.is_department_head():
            return obj is None or obj.policy_owner == request.user.department
        return super().has_view_permission(request, obj)

    # Department heads can only change policies within their department
    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        if request.user.is_department_head():
            return obj and obj.policy_owner == request.user.department
        return super().has_change_permission(request, obj)

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
        if not request.user.is_authenticated:
            return False
        if request.user.is_department_head():
            return obj is None or obj.policy.policy_owner == request.user.department
        return super().has_view_permission(request, obj)

    # Department heads can only change requests for policies within their department
    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
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


# Register handbook models to super admin
super_admin_site.register(PolicySection, PolicySectionAdmin)
super_admin_site.register(Policy, PolicyAdmin)
super_admin_site.register(Definition, DefinitionAdmin)
super_admin_site.register(PolicyRequest, PolicyRequestAdmin)

# Register accounts models to super admin
super_admin_site.register(CustomUser, CustomUserAdmin)
super_admin_site.register(Department, DepartmentAdmin)

# Register models with the department head admin site
department_head_admin.register(Policy, PolicyAdminForDepartmentHead)
department_head_admin.register(PolicyRequest, PolicyRequestAdminForDepartmentHead)
