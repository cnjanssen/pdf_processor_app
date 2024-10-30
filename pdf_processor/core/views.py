from django.views.generic import FormView
from django.http import JsonResponse
from django.conf import settings
import google.generativeai as genai
import logging
import json
import pandas as pd
from django.core.paginator import Paginator
from .forms import ProcessingForm
from .models import PDFDocument, ProcessingJob, ProcessingResult
import base64

logger = logging.getLogger(__name__)

MEDICAL_REVIEW_PROMPT = """You are a medical reviewer tasked with extracting specific information from case studies or case series related to meningioma patients. Your goal is to extract the following information and provide a confidence rating (1-5, with 5 being most confident) for each item. If information is not available, return an empty string for that item and a confidence rating of 1.

For each case, extract:
0. Article Name
1. Document Object Identifier (DOI)
2. Study author (last name of first author)
3. Year of publication
4. Patient age
5. Patient gender (M/F)
6. Duration of symptoms (in months)
7. Tumor location (Cranial or Spinal)
8. Extent of resection (total or subtotal)
9. WHO Grade
10. Meningioma subtype
11. Adjuvant therapy (y/n)
12. Symptom assessment
13. Recurrence (y/n)
14. Patient status (A/D)
15. Tumor invasion (y/n)

Return the data in JSON format:
{
  "case_results": [
    {
      "0": {"value": "", "confidence": 1},
      "1": {"value": "", "confidence": 1},
      ...
    }
  ]
}"""

class ProcessorView(FormView):
    template_name = 'processor.html'
    form_class = ProcessingForm
    success_url = '/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            latest_job = ProcessingJob.objects.latest('created_at')
            latest_result = ProcessingResult.objects.get(document__job=latest_job)
            
            if latest_result.result_data and isinstance(latest_result.result_data, dict):
                df = pd.DataFrame(latest_result.result_data.get('case_results', []))
                paginator = Paginator(df.to_dict('records'), 10)
                page = self.request.GET.get('page', 1)
                table_data = paginator.get_page(page)
                
                context.update({
                    'latest_job': latest_job,
                    'table_data': table_data,
                    'columns': df.columns.tolist() if not df.empty else [],
                    'show_results': True
                })
        except (ProcessingJob.DoesNotExist, ProcessingResult.DoesNotExist):
            context['show_results'] = False
        return context

    def extract_json_from_text(self, text):
        text = text.replace('```json\n', '').replace('\n```', '')
        start_idx = text.find('{')
        end_idx = text.rfind('}') + 1
        
        if start_idx >= 0 and end_idx > start_idx:
            return text[start_idx:end_idx]
        raise ValueError("No valid JSON found in response")

    def validate_and_normalize_json(self, json_str):
        try:
            data = json.loads(json_str)
            if 'case_results' not in data:
                data = {'case_results': [data]}
                
            for case in data['case_results']:
                for i in range(16):
                    key = str(i)
                    if key not in case:
                        case[key] = {"value": "", "confidence": 1}
                    elif isinstance(case[key], (str, int, float)):
                        case[key] = {"value": str(case[key]), "confidence": 1}
            return data
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")

    def process_pdf_with_gemini(self, pdf_doc):
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-pro')
            
            with pdf_doc.file.open('rb') as file:
                pdf_content = file.read()
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            
            response = model.generate_content(
                [{"mime_type": "application/pdf", "data": pdf_base64}, MEDICAL_REVIEW_PROMPT],
                generation_config={"temperature": 0.1, "top_p": 0.8, "top_k": 40}
            )
            
            try:
                json_str = self.extract_json_from_text(response.text)
                parsed_json = self.validate_and_normalize_json(json_str)
                return {
                    'success': True,
                    'parsed_json': parsed_json,
                    'raw_text': response.text
                }
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"JSON parsing error: {e}")
                return {
                    'success': False,
                    'error': f"Failed to parse response as JSON: {str(e)}",
                    'raw_text': response.text
                }
        except Exception as e:
            logger.error(f"Error in process_pdf_with_gemini: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'raw_text': getattr(response, 'text', 'No response text available')
            }

    def form_valid(self, form):
        try:
            job = form.save()
            pdf_doc = PDFDocument.objects.create(
                job=job,
                file=self.request.FILES['pdf_file']
            )

            result = self.process_pdf_with_gemini(pdf_doc)
            print(result)
            if not result.get('success'):
                raise ValueError(result.get('error', 'Unknown processing error'))

            parsed_data = result['parsed_json']
            
            try:
                df = pd.json_normalize(parsed_data['case_results'])
                for col in [str(i) for i in range(16)]:
                    if col not in df.columns:
                        df[col] = pd.NA

                ProcessingResult.objects.create(
                    document=pdf_doc,
                    result_data=parsed_data
                )

                job.status = 'completed'
                job.save()

                return JsonResponse({
                    'success': True,
                    'table_html': df.to_html(classes='table table-striped', index=False),
                    'raw_text': result['raw_text'],
                    'job_id': job.id
                })

            except Exception as e:
                logger.error(f"DataFrame creation error: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': f"Error processing results: {str(e)}",
                    'raw_text': result.get('raw_text', '')
                })

        except Exception as e:
            logger.error(f"Error in form_valid: {str(e)}", exc_info=True)
            if 'job' in locals():
                job.status = 'failed'
                job.save()
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

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