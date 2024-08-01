from dotenv import load_dotenv
import base64
import streamlit as st
import os
import io
from PIL import Image
import pdf2image
import google.generativeai as genai
from PyPDF2 import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Load environment variables
load_dotenv()

# Configure the Google Generative AI model with API key
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def get_gemini_response(input_text, pdf_content, prompt):
    model = genai.GenerativeModel('gemini-pro-vision')
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
                images = pdf2image.convert_from_bytes(uploaded_file.read(), poppler_path=r'D:\new_flask\Release-24.02.0-0\poppler-24.02.0\Library\bin')
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
                st.error("Poppler is not installed or not in PATH. Please install Poppler and add it to your system PATH.")
                return None, None
    return pdf_parts, file_infos

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

# Streamlit App
st.set_page_config(page_title="ESM ATS Expert")
st.header("ESM ATS Tracker")
input_text = st.text_area("Job Description: ", key="input", height=200)
uploaded_files = st.file_uploader("Upload your resumes (PDF)...", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    st.write("PDFs Uploaded Successfully")

submit1 = st.button("Summary Resume")
submit2 = st.button("Suggestions")
submit3 = st.button("Percentage Match and Missing Keywords")
submit4 = st.button("PDF to JD")

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


Evaluate the candidate's resume against the job description and provide the following:


1)Percentage Match: Calculate the overall percentage match between the resume and the job description by evaluating the following:

    1)Skills and Qualifications: Compare each skill and qualification listed in the job description with those mentioned in the resume. Calculate the percentage of matching skills and qualifications.
    2)Experience: Assess the candidate's experience in terms of years, relevance, and specific industry experience. Calculate the percentage match based on the experience criteria.
    3)Industry Terminology: Identify industry-specific terminology in the job description and compare its presence in the resume. Calculate the percentage match based on the occurrence of these terms.

Provide a detailed breakdown of each category and the combined overall match percentage.

2)Missing Keywords: Identify and list any critical keywords or phrases that are present in the job description but missing from the resume. Ensure these keywords are specific to the marine industry.

3)Candidate Suitability: Provide a detailed analysis of the candidate's overall suitability for the role, highlighting key strengths, relevant experiences, and areas for improvement. Comment on how well the candidate meets the essential and desirable criteria listed in the job description.

Your feedback should be comprehensive, precise, stick the same format and focused on key aspects of the resume evaluation.



"""

input_prompt4 = """
You are an expert in matching resumes to job descriptions in the maritime industry. Evaluate the candidate's resume and create a detailed job description

1. **Job Title and Department:** Accurately derive the job title and department from resume.
2. **Job Description Preparation:** Use the resume to craft a job description that includes specific responsibilities, required qualifications, and desired experience with the duration
3. **Strengths and Additional Qualities:** Highlight the strengths and highlight the Additional Qualities as optional but good to have. Do not use the word weakness.
4. **Age Consideration:** Calculate the candidate's accurate current age as of 2024 and specify the desired range.
5. **Experience and Skills:** Specify experience with duration, do not mention ship names, specific skills, qualifications, and any relevant certifications required.

### Important:
- Generate a generic job description do not include specific data such as dates and document numbers.
- Ensure responsibilities, qualifications, are derived from the resume without any assumptions.

"""

def process_submission(prompt, save_as_pdf=False):
    if uploaded_files:
        pdf_contents, file_infos = input_pdf_setup(uploaded_files)
        if pdf_contents is not None:
            for i, pdf_content in enumerate(pdf_contents):
                try:
                    response = get_gemini_response(input_text, pdf_content, prompt)

                    file_info = file_infos[i]
                    st.subheader(f"Response for {file_info['name']} ({file_info['file_name']})")
                    st.write(response)
                    
                    if save_as_pdf:
                        pdf_buffer = save_response_as_pdf(response, f"Job_Description_{i+1}.pdf")
                        st.download_button(
                            label=f"Download Job Description for {file_info['name']} ({file_info['file_name']}) as PDF",
                            data=pdf_buffer,
                            file_name=f"Job_Description_{file_info['name']}.pdf",
                            mime="application/pdf"
                        )
                except Exception as e:
                    st.error(f"Error processing file {file_infos[i]['file_name']}: {str(e)}")
    else:
        st.write("Please upload the resumes")

if submit1:
    process_submission(input_prompt1)

if submit2:
    process_submission(input_prompt2)

if submit3:
    process_submission(input_prompt3)

if submit4:
    process_submission(input_prompt4, save_as_pdf=True)
