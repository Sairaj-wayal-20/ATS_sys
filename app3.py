from dotenv import load_dotenv
import base64
import os
import io
from PIL import Image
import pdf2image
import google.generativeai as genai
from PyPDF2 import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask import Flask, request, render_template, send_file, jsonify

# Load environment variables
load_dotenv()

# Configure the Google Generative AI model with API key
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

app = Flask(__name__)

def get_gemini_response(input_text, pdf_content, prompt):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([input_text, pdf_content, prompt])
    return response.text

def extract_name_from_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)
    first_page = reader.pages[0]
    text = first_page.extract_text()
    name = None

    # Implement a simple heuristic to extract the name (e.g., the first line of text)
    lines = text.split("\n")
    if lines:
        name = lines[0].strip()
    return name

def input_pdf_setup(uploaded_files):
    pdf_parts = []
    file_infos = []
    for uploaded_file in uploaded_files:
        if uploaded_file is not None:
            try:
                # Convert the PDF to image
                images = pdf2image.convert_from_bytes(uploaded_file.read(), poppler_path=r'D:\ATS_sys\Release-24.02.0-0\poppler-24.02.0\Library\bin')
                first_page = images[0]

                # Convert to bytes
                img_byte_arr = io.BytesIO()
                first_page.save(img_byte_arr, format='JPEG')
                img_byte_arr = img_byte_arr.getvalue()

                pdf_parts.append({
                    "mime_type": "image/jpeg",
                    "data": base64.b64encode(img_byte_arr).decode()  # encode to base64
                })

                # Extract name from the PDF
                uploaded_file.seek(0)
                name = extract_name_from_pdf(uploaded_file)
                file_infos.append({
                    "name": name if name else "Unknown",
                    "file_name": uploaded_file.name
                })
            except pdf2image.exceptions.PDFInfoNotInstalledError:
                return None, None, "Poppler is not installed or not in PATH. Please install Poppler and add it to your system PATH."
    return pdf_parts, file_infos, None

def save_response_as_pdf(response_text, file_name):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    c.drawString(100, height - 40, "Generated Job Description")
    text = c.beginText(40, height - 80)
    text.setFont("Helvetica", 12)
    for line in response_text.split("\n"):
        text.textLine(line)
    c.drawText(text)
    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer

input_prompt1 = """
You are an experienced Marine Human Resource Manager tasked with evaluating a candidate's resume against the provided job description. Your professional assessment should include the following points:

1. **Strengths and Weaknesses:** Clearly outline the candidate's strengths and weaknesses in relation to the job requirements.
2. **Age Calculation:** Calculate the candidate's accurate current age as of 2024. Consider if the candidate has had their birthday this year and include reasoning based on significant age milestones (e.g., turning 18, 21, 30).
3. **Experience and Skills:** Provide a detailed evaluation of the candidate's experience, skills, qualifications, and any relevant certifications.
4. **Role Suitability:** Assess the candidate's suitability for the role based on the alignment of their profile with the key responsibilities and qualifications in the job description.

Deliver your evaluation in a concise and professional manner.
"""

input_prompt2 = """
You are a Marine Human Resource Manager with expertise in the marine field. Evaluate the candidate's resume against the job description and offer professional insights:

1. **Detailed Analysis:** Provide a thorough analysis of the candidate's strengths and weaknesses in relation to the job requirements.
2. **Experience and Skills:** Assess the candidate's experience, skills, qualifications, and relevant certifications.
3. **Improvement Suggestions:** Suggest specific improvements and skill enhancements that would make the candidate more suitable for the role.
4. **Constructive Feedback:** Offer constructive feedback on areas where the candidate needs improvement.

Your response should be detailed, constructive, and aimed at enhancing the candidate's suitability for the role.
"""

input_prompt3 = """

You are a specialized ATS (Applicant Tracking System) scanner with extensive knowledge of the marine industry. Evaluate the candidate's resume against the job description and provide the following:

Candidate Evaluation Report: [PDF Name] (give exact resume name)

1)Percentage Match:

    1)Skills and Qualifications:
        1)Evaluate each skill and qualification listed in the job description against those in the resume.
        2)Calculate the percentage of matching skills and qualifications.
    2)Experience:
        1)Assess the candidate's experience in terms of years, relevance, and specific industry experience.
        2)Calculate the percentage match based on the experience criteria.
    3)Industry Terminology:
        1)Identify industry-specific terminology in the job description and compare its presence in the resume.
        2)Calculate the percentage match based on the occurrence of these terms.
    Overall Match Percentage: [Insert calculated percentage here]
2)Missing Keywords:

    1)Identify critical keywords or phrases from the job description that are absent in the resume.
    2)Ensure these keywords are specific to the marine industry.
3)Candidate Suitability:

    1)Provide a detailed analysis of the candidate's suitability for the role.
    2)Highlight key strengths, relevant experiences, and areas for improvement.
    3)Comment on how well the candidate meets the essential and desirable criteria listed in the job description.
Note:
Strictly remove the following lines from the resumes: "SAFETY AND QUALITY MANAGEMENT," "FLEET PERSONNEL OFFICE MANUAL," "EXECUTIVE SHIP MANAGEMENT PTE LTD."
Ensure these lines are not included in the response part.
Do not include the "Resume: uploaded_files" and "Name: SAFETY AND QUALITY MANAGEMENT" sections in the response.


"""
input_prompt4 = """
You are an expert in matching resumes to job descriptions in the maritime industry. Evaluate the candidate's resume and create a detailed job description

1. **Job Title and Department:** Accurately derive the job title and department from the resume.
2. **Job Description Preparation:** Use the resume to craft a job description that includes specific responsibilities, required qualifications, and desired experience with the duration.
3. **Strengths and Additional Qualities:** Highlight the strengths and highlight the additional qualities as optional but good to have. Do not use the word weakness.
4. **Age Consideration:** Calculate the candidate's accurate current age as of 2024 and specify the desired range.
5. **Experience and Skills:** Specify experience with duration, do not mention ship names, specific skills, qualifications, and any relevant certifications required.

### Important:
- Generate a generic job description do not include specific data such as dates and document numbers.
- Ensure responsibilities, qualifications, are derived from the resume without any assumptions.
"""
#flask 
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        input_text = request.form.get("input_text")
        prompt_type = request.form.get("prompt_type")
        prompt = globals()[f"input_prompt{prompt_type}"]
        uploaded_files = request.files.getlist("uploaded_files")

        pdf_contents, file_infos, error = input_pdf_setup(uploaded_files)
        if error:
            return render_template('index.html', error=error)
        
        responses = []
        for i, pdf_content in enumerate(pdf_contents):
            try:
                response = get_gemini_response(input_text, pdf_content, prompt)
                file_info = file_infos[i]
                responses.append({
                    "name": file_info['name'],
                    "file_name": file_info['file_name'],
                    "response": response
                })
            except Exception as e:
                return render_template('index.html', error=f"Error processing file {file_infos[i]['file_name']}: {str(e)}")
        
        return render_template('index.html', responses=responses)
    return render_template('index.html')

@app.route('/download_pdf/<int:index>', methods=['GET'])
def download_pdf(index):
    response_text = request.args.get("response_text")
    file_name = f"Job_Description_{index+1}.pdf"
    pdf_buffer = save_response_as_pdf(response_text, file_name)
    return send_file(pdf_buffer, download_name=file_name, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
