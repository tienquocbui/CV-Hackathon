from flask import Flask, render_template, request, jsonify, send_file, url_for
import openai, whisper, os, re
from dotenv import load_dotenv
from docx import Document  # Import python-docx
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
whisper_model = whisper.load_model("small")
os.makedirs('uploads', exist_ok=True)

def parse_cv_text(text):
    sections = {k: (v.group(1).strip() if v else "") for k, v in {
        "Name": re.search(r"Name[:\-]\s*(.*)", text, re.IGNORECASE),
        "Title": re.search(r"Title[:\-]\s*(.*)", text, re.IGNORECASE),
        # "Summary": re.search(r"Summary[:\-]\s*(.*)", text, re.IGNORECASE),
        # "Skills": re.search(r"Skills[:\-]\s*(.*)", text, re.IGNORECASE),
        # "Experience": re.search(r"Experience[:\-]\s*(.*)", text, re.IGNORECASE),
        # "Education": re.search(r"Education[:\-]\s*(.*)", text, re.IGNORECASE),
    }.items()}
    return sections

def generate_cv_pdf(data):
    output_path = os.path.join('uploads', 'cv_result.pdf')
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, data["Name"])
    c.setFont("Helvetica", 14)
    c.drawString(50, height - 75, data["Title"])

    y = height - 110
    for section, content in data.items():
        if section not in ["Name", "Title"] and content:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, section)
            c.setFont("Helvetica", 11)
            text_obj = c.beginText(60, y - 15)
            for line in content.split('\n'):
                text_obj.textLine(line)
            c.drawText(text_obj)
            y -= (15 * (len(content.split('\n')) + 2))

    c.save()
    return output_path

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/demo')
def demo():
    return render_template('demo.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'text': 'No file uploaded'}), 400

    audio_path = os.path.join('uploads', 'temp.wav')
    request.files['audio'].save(audio_path)

    try:
        result = whisper_model.transcribe(audio_path)
        transcript_text = result['text']  

        # ✅ Parse the transcript into structured JSON format
        structured_data = parse_transcript(request.form.get('question_key'), transcript_text)

        return jsonify({'text': transcript_text, 'structured_data': structured_data})
    
        # return jsonify({'text': result['text']})
    except Exception as e:
        return jsonify({'text': f"Error: {str(e)}"}), 500
    finally:
        os.remove(audio_path)

@app.route('/improve', methods=['POST'])
def improve():
    text = request.json.get('text', '')
    if not text:
        return jsonify({'improved_text': 'No text provided.'}), 400

    prompt = f"""Improve and structure the following CV content with professional language and clear sections (Name, Title, Summary, Skills, Experience, Education):\n\n{text}"""

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert in creating professional CVs."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800
        )

        improved_text = response.choices[0].message.content.strip()
        parsed_data = parse_cv_text(improved_text)
        pdf_path = generate_cv_pdf(parsed_data)

        return jsonify({'improved_text': improved_text, 'pdf_url': url_for('download_cv')})
    except Exception as e:
        return jsonify({'improved_text': f"Error: {str(e)}"}), 500

@app.route('/download')
def download_cv():
    return send_file('uploads/cv_result.pdf', as_attachment=True, download_name="Your_CV.pdf")

CV_QUESTIONS = {
    "Name": "What is your full name?",
    "Title": "What is your job title?",
    # "Summary": "Provide a brief professional summary.",
    # "Skills": "List your key skills.",
    # "Experience": "Describe your work experience.",
    # "Education": "Where did you study and what degree did you earn?",
    # "Certifications": "Do you have any certifications or awards?"
}

@app.route('/next_question', methods=['GET'])
def next_question():
    """Get the next question to be displayed on the frontend."""
    question_keys = list(CV_QUESTIONS.keys())
    current_index = int(request.args.get('index', 0))
    
    if current_index < len(question_keys):
        return jsonify({"key":question_keys[current_index],"question": CV_QUESTIONS[question_keys[current_index]], "index": current_index})
    else:
        return jsonify({"message": "All questions completed."})

def parse_transcript(question_key,text):
    """Extracts CV sections from a raw transcript using regex."""
    sections = {key: "" for key in CV_QUESTIONS.keys()}  # Initialize empty structure

    # # Regular expressions to extract sections dynamically
    # patterns = {
    #     "Name": r"(?i)(?:Name[:\-]?\s*)([^\n]*)",
    #     "Title": r"(?i)(?:Title[:\-]?\s*)([^\n]*)",
    #     # "Summary": r"(?i)(?:Summary[:\-]?\s*)([^\n]*)",
    #     # "Skills": r"(?i)(?:Skills[:\-]?\s*)([^\n]*)",
    #     # "Experience": r"(?i)(?:Experience[:\-]?\s*)([^\n]*)",
    #     # "Education": r"(?i)(?:Education[:\-]?\s*)([^\n]*)",
    #     # "Certifications": r"(?i)(?:Certifications[:\-]?\s*)([^\n]*)"
    # }
    # for key, pattern in patterns.items():
    #     match = re.search(pattern, text)
    #     if match:
    sections[question_key] = text;
    print(sections)
    return sections
# Function to generate a DOCX file based on structured CV data
def generate_docx(data, output_filename):
    doc = Document()
    doc.add_heading('Curriculum Vitae', 0)

    for section, content in data.items():
        doc.add_heading(section, level=1)
        if isinstance(content, list):
            for item in content:
                doc.add_paragraph(f"- {item}")
        else:
            doc.add_paragraph(content)

    doc.save(output_filename)
    print(f"Document saved as {output_filename}")
    return output_filename

@app.route('/generate_docx', methods=['POST'])
def generate_docx_file():
    """Generate a DOCX file from structured CV data."""
    data = request.json.get('structured_data', {})

    if not data:
        return jsonify({"error": "No structured data provided."}), 400

    output_filename = "./uploads/output_cv.docx"
    generate_docx(data, output_filename)

    return jsonify({"message": "CV generated successfully", "file": output_filename, "html_file": docx_to_html(output_filename)})


def docx_to_html(docx_path):
    output_html_path = docx_path.replace('.docx', '.html')
    
    # Ensure the DOCX file exists before proceeding
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"Input DOCX file not found: {docx_path}")

    # Convert DOCX to HTML using LibreOffice headless mode
    os.system(f"/Applications/LibreOffice.app/Contents/MacOS/soffice --headless --convert-to html {docx_path}")

    # Check if the HTML file was created
    # if not os.path.exists(output_html_path):
    #     raise FileNotFoundError(f"Failed to generate HTML file: {output_html_path}")

    # Return the path to the generated HTML file
    return output_html_path

if __name__ == '__main__':
    app.run(debug=True)