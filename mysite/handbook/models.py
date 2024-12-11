from django.db import models, transaction
from django.db.models import JSONField
from django.conf import settings
from django.core.exceptions import ValidationError

"""
Model definitions for the handbook application.
Includes sections, policies, procedure steps, definitions, approval requests, and policy requests.
"""

# Validator for section numbers (e.g., '1.0', '2.0', etc.)
def validate_section_number(value):
    # Ensure the section number follows the 'X.0' format
    if not value.endswith('.0') or not value.replace('.', '').isdigit():
        # Raises a ValidationError if the format is incorrect
        raise ValidationError("Section number must be in the format X.0 (e.g., '1.0').")

# Represents a high-level section, such as '1.0 Employment Policies and Procedures'
class PolicySection(models.Model):
    title = models.CharField(max_length=200, unique=True)
    number = models.CharField(max_length=10, unique=True, validators=[validate_section_number])

    # Display the section using its number and title
    def __str__(self):
        return f"{self.number} {self.title}"

    #  Custom save method to ensure policy numbers stay in sync with section numbers
    def save(self, *args, **kwargs):
        # Track changes to the section number
        old_number = None
        if self.pk:
            # Retrieve the previous section number before saving
            old_number = PolicySection.objects.get(pk=self.pk).number

        super().save(*args, **kwargs)

        # If the section number has changed, update associated policies
        if old_number and old_number != self.number:
            section_prefix = self.number.split(".")[0]
            # Retrieve all policies associated with this section
            policies = self.policies.all().order_by('pk')  # Maintain policy sequence
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

    # Department responsible for the policy
    policy_owner = models.ForeignKey(
        'accounts.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="policies"
    )
    version = models.CharField(max_length=10)  # For tracking policy version
    pub_date = models.DateField("Date Created", auto_now_add=True)
    updated_at = models.DateTimeField("Last Updated", auto_now=True)

    # Review period options
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

    # Display the policy using its number and title
    def __str__(self):
        return f"{self.number} {self.title}"

    # Validate that the policy number matches the section's number
    def clean(self):
        if self.number and not self.number.startswith(self.section.number.split(".")[0]):
            # Raises a ValidationError if the number doesn't match the section's format
            raise ValidationError(f"Policy number {self.number} must match the section {self.section.number} prefix.")

    # Custom save method to auto-generate the policy number if it doesn't already exist
    def save(self, *args, **kwargs):
        # Auto-generate the policy number
        if not self.number:
            # Get the section's prefix
            section_prefix = self.section.number.split(".")[0]
            # Count existing policies in this section
            policy_count = Policy.objects.filter(section=self.section).count()
            # Generate the policy number
            self.number = f"{section_prefix}.{policy_count + 1}"
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

    # Display the procedure step using its number and truncated description
    def __str__(self):
        return f"Step {self.step_number}: {self.description[:50]}"

    # Custom save method to auto-assign step numbers for new procedure steps if not explicitly set
    def save(self, *args, **kwargs):
        if not self.pk:  # If new policy
            max_step = ProcedureStep.objects.filter(policy=self.policy).aggregate(models.Max('step_number'))[
                           'step_number__max'
                       ] or 0
            self.step_number = max_step + 1
        super().save(*args, **kwargs)


# Represents definitions linked to policies
class Definition(models.Model):
    term = models.CharField(max_length=100)
    definition = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_definitions"
    )

    # Display the definition term and a truncated version of its description
    def __str__(self):
        return f"{self.term}: {self.definition[:50]}..."

    class Meta:
        verbose_name = "Definition"  # Singular form
        verbose_name_plural = "Definitions"  # Plural form


# Represents requests for policy approval on edits/creations/archives
class PolicyApprovalRequest(models.Model):
    # Options for status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('revision_needed', 'Revision Needed'),
        ('rejected', 'Rejected'),
    ]

    # Options for request type
    REQUEST_TYPE_CHOICES = [
        ('new', 'New Policy'),
        ('edit', 'Edit Policy'),
        ('archive', 'Archive Policy'),
    ]

    # Main policy reference
    policy = models.ForeignKey(
        'Policy',
        on_delete=models.CASCADE,
        related_name='approval_requests',
        null=True,
        blank=True,
    )
    # Archived policy reference
    archived_policy = models.ForeignKey(
        'ArchivedPolicy',
        on_delete=models.SET_NULL,
        related_name='approval_requests',
        null=True,
        blank=True,
    )
    # User who submitted policy approval request
    submitter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submitted_requests',
    )
    # User who approves or handles the request
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_requests',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending') # Default pending status if new request
    request_type = models.CharField(max_length=10,choices=REQUEST_TYPE_CHOICES,default='edit')
    notes = models.TextField(blank=True, null=True)  # Notes for revision/rejection
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Fields for policy (read-only or editable based on request type)
    section = models.ForeignKey(PolicySection, on_delete=models.CASCADE, related_name="approval_requests")
    number = models.CharField(max_length=10, blank=True, null=True)
    policy_owner = models.ForeignKey(
        'accounts.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    version = models.CharField(max_length=10, blank=True, null=True)

    # Proposed changes for policy fields
    proposed_title = models.CharField(max_length=200, blank=True, null=True)
    proposed_review_period = models.CharField(max_length=50, choices=Policy.REVIEW_PERIOD_CHOICES, blank=True,
                                              null=True)
    proposed_purpose = models.TextField(blank=True, null=True)
    proposed_scope = models.TextField(blank=True, null=True)
    proposed_policy_statements = models.TextField(blank=True, null=True)
    proposed_responsibilities = models.TextField(blank=True, null=True)
    proposed_related_policies = models.JSONField(default=list, blank=True)
    proposed_procedure_steps = models.JSONField(default=list, blank=True)
    proposed_definitions = models.JSONField(default=list, blank=True)

    # Automatically populate fields for edits
    def save(self, *args, **kwargs):
        if self.request_type == 'edit' and self.policy:
            self.section = self.policy.section
            self.number = self.policy.number
            self.policy_owner = self.policy.policy_owner
            self.proposed_title = self.proposed_title or self.policy.title
            self.proposed_review_period = self.proposed_review_period or self.policy.review_period
            self.proposed_purpose = self.proposed_purpose or self.policy.purpose
            self.proposed_scope = self.proposed_scope or self.policy.scope
            self.proposed_policy_statements = self.proposed_policy_statements or self.policy.policy_statements
            self.proposed_related_policies = self.proposed_related_policies
            self.proposed_procedure_steps = self.proposed_procedure_steps or list(ProcedureStep.objects.filter(policy=self.policy).values("id", "step_number", "description"))
            self.proposed_definitions = self.proposed_definitions or self.policy.definitions
        super().save(*args, **kwargs)

    # Apply the proposed changes to the main policy and update associated steps/definitions
    def apply_changes(self):
        if self.request_type == 'new':
            # Create a new Policy object
            new_policy = Policy.objects.create(
                section=self.section,
                title=self.proposed_title,
                version="1.0",
                policy_owner=self.policy_owner,
                review_period=self.proposed_review_period,
                purpose=self.proposed_purpose,
                scope=self.proposed_scope,
                policy_statements=self.proposed_policy_statements,
                responsibilities=self.proposed_responsibilities,
            )
            new_policy.related_policies.set(Policy.objects.filter(id__in=self.proposed_related_policies))

            for step in self.proposed_procedure_steps:
                ProcedureStep.objects.create(
                    policy=new_policy,
                    step_number=step["step_number"],
                    description=step["description"],
                )
            for definition in self.proposed_definitions:
                new_policy.definitions.add(Definition.objects.get(id=definition["id"]))
            new_policy.save()
            self.policy = new_policy
            self.save()
        elif self.request_type == 'edit' and self.policy:
            # Update existing policy
            self.policy.version = self.policy.version
            self.policy.title = self.proposed_title
            self.policy.review_period = self.proposed_review_period
            self.policy.purpose = self.proposed_purpose
            self.policy.scope = self.proposed_scope
            self.policy.policy_statements = self.proposed_policy_statements
            self.policy.responsibilities = self.proposed_responsibilities
            self.policy.related_policies.set(self.proposed_related_policies)

            # Update version for major change
            major, minor = map(int, self.policy.version.split('.'))
            major += 1
            minor = 0
            self.policy.version = f"{major}.{minor}"

            # Delete existing Procedure Steps and replace with new ones
            self.policy.procedure_steps.all().delete()
            for step in self.proposed_procedure_steps:
                ProcedureStep.objects.create(
                    policy=self.policy,
                    step_number=step["step_number"],
                    description=step["description"],
                )

            # Remove all current definitions and add new ones
            self.policy.definitions.clear()
            for definition in self.proposed_definitions:
                definition_instance = Definition.objects.get(id=definition["id"])
                self.policy.definitions.add(definition_instance)

            # Save the updated policy
            self.policy.save()

        elif self.request_type == "archive" and self.policy:
            with transaction.atomic():  # Ensure the operation is atomic
                # Save the policy instance before making changes
                section = self.policy.section  # Save the section for renumbering later
                policy = self.policy

                # Serialize procedure steps into a JSON field
                procedure_steps_data = list(policy.procedure_steps.values('step_number', 'description'))

                # Create an ArchivedPolicy instance from the Policy instance
                archived_policy = ArchivedPolicy.objects.create(
                    section=self.policy.section,
                    number=self.policy.number,
                    title=self.policy.title,
                    version=self.policy.version,
                    policy_owner=self.policy.policy_owner,
                    review_period=self.policy.review_period,
                    purpose=self.policy.purpose,
                    scope=self.policy.scope,
                    policy_statements=self.policy.policy_statements,
                    responsibilities=self.policy.responsibilities,
                )
                # Move related data to the archived policy
                archived_policy.related_policies.set(self.policy.related_policies.all())
                archived_policy.definitions.set(self.policy.definitions.all())

                # Attach the serialized procedure steps
                archived_policy.procedure_steps_json = procedure_steps_data
                archived_policy.save()

                # Update the PolicyApprovalRequest to reference the archived policy
                self.archived_policy = archived_policy
                self.policy = None  # Clear the original policy reference
                self.save()

                # Delete the original policy
                policy.delete()

                # Renumber remaining policies in the same section
                policies = Policy.objects.filter(section=section).order_by("number")
                section_prefix = section.number.split(".")[0]
                for i, remaining_policy in enumerate(policies, start=1):
                    remaining_policy.number = f"{section_prefix}.{i}"
                    remaining_policy.save()


    # Display the approval request with the policy number and status
    def __str__(self):
        if self.policy:
            return f"Request to {self.request_type} policy: {self.policy.title}"
        elif self.archived_policy:
            return f"Archived {self.request_type} policy: {self.archived_policy.title}"
        else:
            return f"Request to create new policy: {self.proposed_title}"

    class Meta:
        verbose_name = "Policy Approval Request"  # Singular form
        verbose_name_plural = "Policy Approval Requests"  # Plural form


# Represents archived policies
class ArchivedPolicy(models.Model):
    section = models.ForeignKey(PolicySection, on_delete=models.CASCADE, related_name="archived_policies")
    number = models.CharField(max_length=10)
    title = models.CharField(max_length=200)
    version = models.CharField(max_length=10)
    policy_owner = models.ForeignKey('accounts.Department', on_delete=models.SET_NULL, null=True, blank=True)
    review_period = models.CharField(max_length=50)
    purpose = models.TextField()
    scope = models.TextField()
    policy_statements = models.TextField()
    responsibilities = models.TextField()
    archived_at = models.DateTimeField(auto_now_add=True)
    related_policies = models.ManyToManyField("Policy", related_name="archived_related_policies", blank=True)
    procedure_steps_json = JSONField(default=list, blank=True)
    definitions = models.ManyToManyField("Definition", related_name="archived_policies", blank=True)

    def __str__(self):
        return f"{self.number} {self.title}"

    class Meta:
        verbose_name = "Archived Policy"  # Singular form
        verbose_name_plural = "Archived Policies"  # Plural form


# Represents feedback forms on each policy
class PolicyFeedback(models.Model):
    policy = models.ForeignKey('Policy', on_delete=models.CASCADE, related_name='requests')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    question = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)  # Tracks whether the feedback has been addressed
    admin_notes = models.TextField(blank=True, null=True)  # Admin can add follow-up notes

    # Display the feedback details, including the policy title and submitter's name
    def __str__(self):
        return f"Request for {self.policy.title} by {self.first_name} {self.last_name}"

    class Meta:
        verbose_name = "Policy Feedback"  # Singular form
        verbose_name_plural = "Policy Feedback"  # Plural form