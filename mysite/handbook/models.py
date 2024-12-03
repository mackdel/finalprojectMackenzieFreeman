from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

# Validator for section numbers (e.g., '1.0', '2.0', etc.)
def validate_section_number(value):
    if not value.endswith('.0') or not value.replace('.', '').isdigit():
        raise ValidationError("Section number must be in the format X.0 (e.g., '1.0').")

# Represents a high-level section, such as '1.0 Employment Policies and Procedures'
class PolicySection(models.Model):
    title = models.CharField(max_length=200, unique=True)
    number = models.CharField(max_length=10, unique=True, validators=[validate_section_number])

    def __str__(self):
        return f"{self.number} {self.title}"

    def save(self, *args, **kwargs):
        # Track changes to the section number
        old_number = None
        if self.pk:
            # Retrieve the old section number from the database
            old_number = PolicySection.objects.get(pk=self.pk).number

        super().save(*args, **kwargs)

        # If the section number has changed, update associated policies
        if old_number and old_number != self.number:
            section_prefix = self.number.split(".")[0]
            # Retrieve all policies associated with this section
            policies = self.policies.all().order_by('pk')  # Ensures policies maintain their sequence
            for index, policy in enumerate(policies, start=1):
                policy.number = f"{section_prefix}.{index}"
                policy.save()

    class Meta:
        verbose_name = "Policy Section"  # Singular form
        verbose_name_plural = "Policy Sections"  # Plural form


# Represents individual policies within sections, with detailed fields
class Policy(models.Model):
    section = models.ForeignKey(PolicySection, on_delete=models.CASCADE, related_name="policies")
    title = models.CharField(max_length=200)
    number = models.CharField(max_length=10, unique=True, editable=False)  # Auto-generated number
    purpose = models.TextField(blank=True, null=True)
    scope = models.TextField(blank=True, null=True)
    policy_statements = models.TextField(blank=True, null=True)
    responsibilities = models.TextField(blank=True, null=True)

    # Related policies as a many-to-many field
    related_policies = models.ManyToManyField("self", blank=True, symmetrical=False, related_name="related_to")

    # Definitions associated with the policy
    definitions = models.ManyToManyField('Definition', blank=True, related_name="policies")

    # Choose Department
    policy_owner = models.ForeignKey(
        'accounts.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="policies"
    )
    version = models.CharField(max_length=10)  # For tracking policy version
    pub_date = models.DateField("Date Created", auto_now_add=True)
    published = models.BooleanField(default=False)

    REVIEW_PERIOD_CHOICES = [
        ('Monthly', 'Monthly'),
        ('Quarterly', 'Quarterly'),
        ('Annually', 'Annually'),
        ('Bi-Annually', 'Bi-Annually'),
        ('Biennially', 'Biennially'),
    ]
    review_period = models.CharField(
        max_length=50,
        choices=REVIEW_PERIOD_CHOICES,
        blank=True,
        null=True,
        help_text="Select the review period for this policy."
    )

    def __str__(self):
        return f"{self.number} {self.title}"

    # Validate that the policy number matches the section's number
    def clean(self):
        if self.number and not self.number.startswith(self.section.number.split(".")[0]):
            raise ValidationError(f"Policy number {self.number} must match the section {self.section.number} prefix.")

    def save(self, *args, **kwargs):
        # Auto-generate the policy number
        if not self.number:
            # Get the section's prefix
            section_prefix = self.section.number.split(".")[0]
            # Count existing policies in this section
            policy_count = Policy.objects.filter(section=self.section).count()
            # Generate the policy number
            self.number = f"{section_prefix}.{policy_count + 1}"
        print(f"Policy Save Triggered: {self}")
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Policy"  # Singular form
        verbose_name_plural = "Policies"  # Plural form


# Represents individual procedure steps linked to a policy
class ProcedureStep(models.Model):
    policy = models.ForeignKey('Policy', on_delete=models.CASCADE, related_name='procedure_steps')
    step_number = models.PositiveIntegerField()  # For ordering steps
    description = models.TextField()

    class Meta:
        ordering = ['step_number']  # Steps will be ordered by their step number

    def __str__(self):
        return f"Step {self.step_number}: {self.description[:50]}"

    def save(self, *args, **kwargs):
        # Automatically assign step numbers if not set.
        if not self.pk:  # New instance
            max_step = ProcedureStep.objects.filter(policy=self.policy).aggregate(models.Max('step_number'))[
                           'step_number__max'
                       ] or 0
            self.step_number = max_step + 1
        super().save(*args, **kwargs)


# Represents definitions linked to policies
class Definition(models.Model):
    term = models.CharField(max_length=100)
    definition = models.TextField()

    def __str__(self):
        return f"{self.term}: {self.definition[:50]}..."

    class Meta:
        verbose_name = "Definition"  # Singular form
        verbose_name_plural = "Definitions"  # Plural form


# Represents requests for policy approval on edits/creations/archives
class PolicyApprovalRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('revision_needed', 'Revision Needed'),
        ('rejected', 'Rejected'),
    ]

    # Main policy reference
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name='approval_requests',
    )
    # Metadata for the request
    submitter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submitted_requests',
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_requests',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)  # Notes for revision/rejection
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Proposed changes (duplicate policy fields)
    proposed_title = models.CharField(max_length=200, blank=True, null=True)
    proposed_purpose = models.TextField(blank=True, null=True)
    proposed_scope = models.TextField(blank=True, null=True)
    proposed_policy_statements = models.TextField(blank=True, null=True)
    proposed_responsibilities = models.TextField(blank=True, null=True)
    proposed_related_policies = models.JSONField(default=list, blank=True)
    proposed_procedure_steps = models.JSONField(default=list, blank=True)
    proposed_definitions = models.JSONField(default=list, blank=True)

    # Get current policy details for admin display
    @property
    def current_title(self):
        return self.policy.title

    @property
    def current_purpose(self):
        return self.policy.purpose

    @property
    def current_scope(self):
        return self.policy.scope

    @property
    def current_policy_statements(self):
        return self.policy.policy_statements

    @property
    def current_responsibilities(self):
        return self.policy.responsibilities

    @property
    def current_related_policies(self):
        return self.policy.related_policies.all()

    @property
    def current_procedure_steps(self):
        return ProcedureStep.objects.filter(policy=self.policy).order_by("step_number")

    @property
    def current_definitions(self):
        return self.policy.definitions.all()

    def save(self, *args, **kwargs):
        # On creation, populate the duplicate fields only if not already provided
        if not self.pk:
            self.proposed_title = self.proposed_title or self.policy.title
            self.proposed_purpose = self.proposed_purpose or self.policy.purpose
            self.proposed_scope = self.proposed_scope or self.policy.scope
            self.proposed_policy_statements = self.proposed_policy_statements or self.policy.policy_statements
            self.proposed_related_policies = self.proposed_related_policies
            self.proposed_definitions = self.proposed_definitions
            self.proposed_procedure_steps = self.proposed_procedure_steps or list(ProcedureStep.objects.filter(policy=self.policy).values("id", "step_number", "description"))
            self.proposed_definitions = self.proposed_definitions or self.policy.definitions
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Request for Policy: {self.policy.number} - Status: {self.get_status_display()}"

# Represents request forms on each policy
class PolicyRequest(models.Model):
    policy = models.ForeignKey('Policy', on_delete=models.CASCADE, related_name='requests')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    question = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)  # Tracks whether the request has been addressed
    admin_notes = models.TextField(blank=True, null=True)  # Admin can add follow-up notes

    def __str__(self):
        return f"Request for {self.policy.title} by {self.first_name} {self.last_name}"

    class Meta:
        verbose_name = "Policy Request"  # Singular form
        verbose_name_plural = "Policy Requests"  # Plural form