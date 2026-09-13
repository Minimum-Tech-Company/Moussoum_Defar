from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Language(models.Model):
    """African languages supported by the platform."""
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    region = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class Country(models.Model):
    """African countries."""
    code = models.CharField(max_length=2, unique=True)
    name = models.CharField(max_length=100)
    currency = models.CharField(max_length=10, default='FCFA')
    mobile_money_services = models.JSONField(default=list)
    languages = models.ManyToManyField(Language, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'countries'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class Worker(models.Model):
    """African worker profile."""
    LEVEL_CHOICES = [
        (1, 'Data Worker'),
        (2, 'Verified Annotator'),
        (3, 'Language Specialist'),
        (4, 'AI Evaluator'),
        (5, 'Domain Expert'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='worker_profile')
    phone = models.CharField(max_length=20, blank=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    languages = models.ManyToManyField(Language, blank=True)
    level = models.IntegerField(choices=LEVEL_CHOICES, default=1)
    quality_score = models.FloatField(default=0.0)
    total_tasks = models.IntegerField(default=0)
    accuracy = models.FloatField(default=0.0)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_verified = models.BooleanField(default=False)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-quality_score']

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - Level {self.level}"

    def calculate_quality_score(self):
        """Calculate quality score based on accuracy and volume."""
        accuracy_score = self.accuracy * 40
        volume_score = min(self.total_tasks / 1000, 1.0) * 30
        consistency_score = self._calculate_consistency() * 30
        self.quality_score = accuracy_score + volume_score + consistency_score
        self.save(update_fields=['quality_score'])
        return self.quality_score

    def _calculate_consistency(self):
        """Measure quality consistency over time."""
        recent_logs = QualityLog.objects.filter(
            worker=self
        ).order_by('-created_at')[:50]

        if len(recent_logs) < 10:
            return 0.5

        scores = [log.score for log in recent_logs]
        mean = sum(scores) / len(scores)
        if mean == 0:
            return 0.5

        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        std_dev = variance ** 0.5

        return max(0, 1.0 - (std_dev / mean))


class WorkerLevel(models.Model):
    """Level and progression requirements."""
    LEVEL_CHOICES = [
        (1, 'Data Worker'),
        (2, 'Verified Annotator'),
        (3, 'Language Specialist'),
        (4, 'AI Evaluator'),
        (5, 'Domain Expert'),
    ]

    worker = models.OneToOneField(Worker, on_delete=models.CASCADE, related_name='level_info')
    level = models.IntegerField(choices=LEVEL_CHOICES)
    tasks_required = models.IntegerField(default=100)
    accuracy_required = models.FloatField(default=80.0)
    unlocked_at = models.DateTimeField(null=True, blank=True)
    tasks_at_unlock = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.worker} - Level {self.level}"

    def can_advance(self):
        """Check if the worker can advance to the next level."""
        return (
            self.worker.total_tasks >= self.tasks_required and
            self.worker.accuracy >= self.accuracy_required
        )


class DataCollection(models.Model):
    """Data collection project."""
    DATA_TYPE_CHOICES = [
        ('audio', 'Audio'),
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('document', 'Document'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    data_type = models.CharField(max_length=10, choices=DATA_TYPE_CHOICES)
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    target_count = models.IntegerField(default=1000)
    current_count = models.IntegerField(default=0)
    price_per_item = models.DecimalField(max_digits=8, decimal_places=4)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    instructions = models.TextField(blank=True)
    sample_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'data collections'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_data_type_display()})"

    @property
    def progress_percentage(self):
        if self.target_count == 0:
            return 0
        return (self.current_count / self.target_count) * 100

    @property
    def is_complete(self):
        return self.current_count >= self.target_count


class DataSubmission(models.Model):
    """Worker data submission."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('review', 'Under Review'),
    ]

    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name='submissions')
    collection = models.ForeignKey(DataCollection, on_delete=models.CASCADE, related_name='submissions')
    file = models.FileField(upload_to='submissions/%Y/%m/%d/', blank=True, null=True)
    transcription = models.TextField(blank=True)
    metadata = models.JSONField(default=dict)
    quality_score = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reviewer_notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.worker} - {self.collection.title} - {self.status}"

    def approve(self, score=1.0):
        """Approve the submission."""
        self.status = 'approved'
        self.quality_score = score
        self.save()
        self.collection.current_count += 1
        self.collection.save(update_fields=['current_count'])
        self.worker.total_tasks += 1
        self.worker.accuracy = (
            (self.worker.accuracy * (self.worker.total_tasks - 1) + score * 100)
            / self.worker.total_tasks
        )
        self.worker.save(update_fields=['total_tasks', 'accuracy'])
        QualityLog.objects.create(worker=self.worker, submission=self, score=score)

    def reject(self, reason=''):
        """Reject the submission."""
        self.status = 'rejected'
        self.reviewer_notes = reason
        self.save()


class QualityLog(models.Model):
    """Submission quality history."""
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name='quality_logs')
    submission = models.ForeignKey(DataSubmission, on_delete=models.CASCADE)
    score = models.FloatField()
    reviewer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.worker} - Score: {self.score}"


# === SCALE AI FEATURES ADAPTED FOR AFRICA ===

class AnnotationTask(models.Model):
    """Image/text/audio annotation task (like Scale AI labeling)."""
    TASK_TYPE_CHOICES = [
        ('image_bbox', 'Image Bounding Box'),
        ('image_segmentation', 'Image Segmentation'),
        ('image_classification', 'Image Classification'),
        ('text_classification', 'Text Classification'),
        ('text_ner', 'Named Entity Recognition'),
        ('text_sentiment', 'Sentiment Analysis'),
        ('text_translation', 'Translation'),
        ('audio_transcription', 'Audio Transcription'),
        ('audio_classification', 'Audio Classification'),
        ('conversation_rating', 'Conversation Rating'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('review', 'Under Review'),
    ]

    DIFFICULTY_CHOICES = [
        (1, 'Easy'),
        (2, 'Medium'),
        (3, 'Hard'),
        (4, 'Expert'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    task_type = models.CharField(max_length=25, choices=TASK_TYPE_CHOICES)
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    difficulty = models.IntegerField(choices=DIFFICULTY_CHOICES, default=2)
    reward = models.DecimalField(max_digits=8, decimal_places=4, default=0.10)
    input_data = models.JSONField(default=dict, help_text='Data to annotate')
    expected_output = models.JSONField(default=dict, help_text='Expected annotation format')
    instructions = models.TextField(blank=True)
    max_annotations = models.IntegerField(default=3, help_text='Max workers per task')
    current_annotations = models.IntegerField(default=0)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_annotation_tasks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_task_type_display()})"


class AnnotationResult(models.Model):
    """Worker annotation submission."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    task = models.ForeignKey(AnnotationTask, on_delete=models.CASCADE, related_name='results')
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name='annotations')
    annotation_data = models.JSONField(default=dict, help_text='The annotation output')
    time_spent_seconds = models.IntegerField(default=0)
    quality_score = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    reviewer_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.worker} - {self.task.title}"


class RLHFTask(models.Model):
    """Reinforcement Learning from Human Feedback task."""
    TASK_TYPE_CHOICES = [
        ('comparison', 'Response Comparison (A vs B)'),
        ('ranking', 'Rank Multiple Responses'),
        ('rating', 'Rate Response Quality'),
        ('preference', 'Preference Pair'),
        ('correction', 'Text Correction'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES)
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    prompt = models.TextField(help_text='The AI prompt/query')
    responses = models.JSONField(default=list, help_text='List of AI responses to evaluate')
    context = models.JSONField(default=dict, help_text='Additional context for evaluation')
    reward = models.DecimalField(max_digits=8, decimal_places=4, default=0.15)
    max_workers = models.IntegerField(default=5)
    current_workers = models.IntegerField(default=0)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_rlhftasks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'RLHF tasks'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_task_type_display()})"


class RLHFFeedback(models.Model):
    """Worker feedback on RLHF task."""
    task = models.ForeignKey(RLHFTask, on_delete=models.CASCADE, related_name='feedbacks')
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name='rlhf_feedbacks')
    selected_response = models.IntegerField(help_text='Index of preferred response')
    confidence = models.FloatField(default=0.8, help_text='Worker confidence 0-1')
    reasoning = models.TextField(blank=True, help_text='Why this response was chosen')
    time_spent_seconds = models.IntegerField(default=0)
    quality_score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['task', 'worker']

    def __str__(self):
        return f"{self.worker} - {self.task.title}"


class SyntheticDataJob(models.Model):
    """Synthetic data generation job."""
    GENERATION_TYPE_CHOICES = [
        ('conversation', 'Conversation Generation'),
        ('translation', 'Translation Pairs'),
        ('qa_pairs', 'Q&A Pairs'),
        ('text_variations', 'Text Variations'),
        ('entity_data', 'Named Entity Data'),
        ('sentiment_data', 'Sentiment Labeled Text'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    generation_type = models.CharField(max_length=25, choices=GENERATION_TYPE_CHOICES)
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    parameters = models.JSONField(default=dict, help_text='Generation parameters')
    target_count = models.IntegerField(default=100)
    current_count = models.IntegerField(default=0)
    output_data = models.JSONField(default=list, help_text='Generated data')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='synthetic_jobs')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_generation_type_display()})"


class Payment(models.Model):
    """Worker payment/earning record."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    METHOD_CHOICES = [
        ('mobile_money', 'Mobile Money'),
        ('bank_transfer', 'Bank Transfer'),
        ('crypto', 'Cryptocurrency'),
    ]

    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='mobile_money')
    phone_number = models.CharField(max_length=20, blank=True, help_text='For mobile money')
    reference = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    task_type = models.CharField(max_length=50, blank=True, help_text='Type of task earned from')
    task_id = models.IntegerField(null=True, blank=True, help_text='ID of completed task')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.worker} - {self.amount} {self.currency} ({self.status})"


class Notification(models.Model):
    """User notification."""
    TYPE_CHOICES = [
        ('task_assigned', 'Task Assigned'),
        ('task_completed', 'Task Completed'),
        ('payment_received', 'Payment Received'),
        ('payment_processing', 'Payment Processing'),
        ('level_up', 'Level Up'),
        ('evaluation_complete', 'Evaluation Complete'),
        ('collection_ready', 'Collection Ready'),
        ('system', 'System'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=25, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    data = models.JSONField(default=dict, help_text='Additional data')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.title}"

    def mark_read(self):
        self.is_read = True
        self.save(update_fields=['is_read'])
