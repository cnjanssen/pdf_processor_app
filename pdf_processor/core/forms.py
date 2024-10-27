# core/forms.py
from django import forms
from .models import ProcessingJob

class ProcessingForm(forms.ModelForm):
    pdf_file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'accept': '.pdf'}),
        help_text='Select a PDF file'
    )
    
    class Meta:
        model = ProcessingJob
        fields = ['name', 'prompt']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a name for this processing job'
            }),
            'prompt': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Enter your prompt here'
            })
        }

    def clean_pdf_file(self):
        file = self.cleaned_data['pdf_file']
        if not file.name.endswith('.pdf'):
            raise forms.ValidationError('Only PDF files are allowed.')
        return file