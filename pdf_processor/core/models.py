# core/models.py
from django.db import models

class ProcessingJob(models.Model):
    name = models.CharField(max_length=200)
    prompt = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed')
        ],
        default='pending'
    )

    def __str__(self):
        return self.name

class PDFDocument(models.Model):
    job = models.OneToOneField(ProcessingJob, on_delete=models.CASCADE, related_name='document')
    file = models.FileField(upload_to='pdfs/')
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.job.name} - {self.file.name}"

class ProcessingResult(models.Model):
    document = models.OneToOneField(PDFDocument, on_delete=models.CASCADE, related_name='result')
    result_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Result for {self.document}"