# core/views.py
from django.views.generic import FormView, TemplateView
from django.http import JsonResponse
from django.conf import settings
import google.generativeai as genai
from google.generativeai import GenerativeModel
import logging
from .forms import ProcessingForm
from .models import PDFDocument, ProcessingJob, ProcessingResult
import base64
import mimetypes
import logging

logger = logging.getLogger(__name__)

def process_pdf(request):
    try:
        job = ProcessingJob.objects.latest('created_at')
        pdf_document = PDFDocument.objects.get(job=job)
        
        job.status = 'processing'
        job.save()

        # Configure Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Read and encode PDF content
        with pdf_document.file.open('rb') as file:
            pdf_content = file.read()
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        # Create proper content parts for Gemini
        content_parts = [
            {
                "mime_type": "application/pdf",
                "data": pdf_base64
            },
            job.prompt
        ]
        
        # Generate response
        response = model.generate_content(
            content_parts,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40
            }
        )
        
        # Store result
        ProcessingResult.objects.update_or_create(
            document=pdf_document,
            defaults={'result_data': {'text': response.text}}
        )
        
        job.status = 'completed'
        job.save()
        pdf_document.processed = True
        pdf_document.save()
        
        return JsonResponse({
            'success': True,
            'result': response.text
        })
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
        if 'job' in locals():
            job.status = 'failed'
            job.save()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

class ProcessorView(FormView):
    template_name = 'processor.html'
    form_class = ProcessingForm
    success_url = '/'

    def form_valid(self, form):
        try:
            logger.info("Starting form processing")
            job = form.save()
            
            # Save the PDF file
            pdf_doc = PDFDocument.objects.create(
                job=job,
                file=self.request.FILES['pdf_file']
            )

            # Configure Gemini
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-pro')
            
            # Read and encode PDF content
            with pdf_doc.file.open('rb') as file:
                pdf_content = file.read()
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            
            # Create proper content parts for Gemini
            content_parts = [
                {
                    "mime_type": "application/pdf",
                    "data": pdf_base64
                },
                job.prompt
            ]
            
            # Generate response
            response = model.generate_content(
                content_parts,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.8,
                    "top_k": 40
                }
            )
            
            # Save the results
            result = ProcessingResult.objects.create(
                document=pdf_doc,
                result_data={'text': response.text}
            )
            
            # Update statuses
            job.status = 'completed'
            job.save()
            pdf_doc.processed = True
            pdf_doc.save()
            
            return JsonResponse({
                'success': True,
                'result': response.text,
                'job_id': job.id
            })
            
        except Exception as e:
            logger.error(f"Error processing form: {str(e)}", exc_info=True)
            if 'job' in locals():
                job.status = 'failed'
                job.save()
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

class ResultsView(TemplateView):
    template_name = 'results.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job_id = self.kwargs.get('job_id')
        
        try:
            job = ProcessingJob.objects.get(id=job_id)
            result = ProcessingResult.objects.get(document__job=job)
            context.update({
                'job': job,
                'result': result
            })
        except (ProcessingJob.DoesNotExist, ProcessingResult.DoesNotExist) as e:
            logger.warning(f"Results not found for job ID: {job_id}")
            context['error'] = 'Results not found'
        except Exception as e:
            logger.error(f"Error retrieving results: {str(e)}", exc_info=True)
            context['error'] = 'An error occurred while retrieving results'
        
        return context

def test_gemini(request):
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-pro')
        test_response = model.generate_content("Test connection")
        return JsonResponse({
            'success': True,
            'response': test_response.text
        })
    except Exception as e:
        logger.error(f"Gemini API test failed: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)