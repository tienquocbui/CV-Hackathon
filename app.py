from flask import Flask, render_template, request, jsonify, send_file, url_for
import openai, whisper, os, re
from dotenv import load_dotenv
from docx import Document 
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__, static_folder='static')
whisper_model = whisper.load_model("small")
os.makedirs('uploads', exist_ok=True)


def parse_cv_text(text):
    """Parse CV sections from raw text."""
    return {k: (v.group(1).strip() if v else "") for k, v in {
        "Name": re.search(r"Name[:\-]\s*(.*)", text, re.IGNORECASE),
        "Title": re.search(r"Title[:\-]\s*(.*)", text, re.IGNORECASE),
    }.items()}

def generate_cv_pdf(data):
    """Generate CV in PDF format."""
    output_path = os.path.join('uploads', 'cv_result.pdf')
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, data.get("Name", ""))
    c.setFont("Helvetica", 14)
    c.drawString(50, height - 75, data.get("Title", ""))

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

def generate_docx(data, output_filename):
    """Generate a DOCX CV."""
    doc = Document()
    doc.add_heading('Curriculum Vitae', 0)
    for section, content in data.items():
        doc.add_heading(section, level=1)
        doc.add_paragraph(content if isinstance(content, str) else "\n".join(content))
    doc.save(output_filename)
    return output_filename

def docx_to_html(docx_path):
    """Convert DOCX to HTML using LibreOffice."""
    output_html_path = docx_path.replace('.docx', '.html')
    os.system(f"/Applications/LibreOffice.app/Contents/MacOS/soffice --headless --convert-to html {docx_path}")
    return output_html_path

def parse_cv_text(text):
    """Parse CV sections from raw text."""
    return {k: (v.group(1).strip() if v else "") for k, v in {
        "Name": re.search(r"Name[:\-]\s*(.*)", text, re.IGNORECASE),
        "Title": re.search(r"Title[:\-]\s*(.*)", text, re.IGNORECASE),
    }.items()}

def generate_cv_pdf(data):
    """Generate CV in PDF format."""
    output_path = os.path.join('uploads', 'cv_result.pdf')
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, data.get("Name", ""))
    c.setFont("Helvetica", 14)
    c.drawString(50, height - 75, data.get("Title", ""))

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

def generate_docx(data, output_filename):
    """Generate a DOCX CV."""
    doc = Document()
    doc.add_heading('Curriculum Vitae', 0)
    for section, content in data.items():
        doc.add_heading(section, level=1)
        doc.add_paragraph(content if isinstance(content, str) else "\n".join(content))
    doc.save(output_filename)
    return output_filename

def docx_to_html(docx_path):
    """Convert DOCX to HTML using LibreOffice."""
    output_html_path = docx_path.replace('.docx', '.html')
    os.system(f"/Applications/LibreOffice.app/Contents/MacOS/soffice --headless --convert-to html {docx_path}")
    return output_html_path

@app.route('/')
def home(): return render_template('index.html')

@app.route('/demo')
def demo(): return render_template('demo.html')

@app.route('/about')
def about(): return render_template('about.html')

@app.route('/features')
def features(): return render_template('features.html')

@app.route('/pricing')
def pricing(): return render_template('pricing.html')

@app.route('/contact')
def contact(): return render_template('contact.html')

@app.route('/download')
def download_cv():
    return send_file('uploads/cv_result.pdf', as_attachment=True, download_name="Your_CV.pdf")

CV_QUESTIONS = {
    "Name": "What is your full name?",
    "Title": "What is your job title?",
    "Summary": "Provide a brief professional summary.",
    "Skills": "List your key skills.",
    "Experience": "Describe your work experience.",
    "Education": "Where did you study and what degree did you earn?",
    "Certifications": "Do you have any certifications or awards?"
}

@app.route('/next_question', methods=['GET'])
def next_question():
    """🔎 Get the next CV question."""
    index = int(request.args.get('index', 0))
    keys = list(CV_QUESTIONS.keys())
    return jsonify({"key": keys[index], "question": CV_QUESTIONS[keys[index]]}) if index < len(keys) else jsonify({"message": "All questions completed."})

@app.route('/transcribe', methods=['POST'])
def transcribe():
    """🎙️ Handle audio transcription with Whisper model."""
    if 'audio' not in request.files:
        return jsonify({'text': 'No file uploaded'}), 400

    audio_path = os.path.join('uploads', 'temp.wav')
    request.files['audio'].save(audio_path)

    try:
        result = whisper_model.transcribe(audio_path)
        transcript_text = result['text']
        structured_data = {request.form.get('question_key'): transcript_text}
        return jsonify({'text': transcript_text, 'structured_data': structured_data})
    except Exception as e:
        return jsonify({'text': f"Error: {str(e)}"}), 500
    finally:
        os.remove(audio_path)

@app.route('/generate_docx', methods=['POST'])
def generate_docx_file():
    """📄 Generate DOCX from structured data."""
    data = request.json.get('structured_data', {})
    if not data:
        return jsonify({"error": "No structured data provided."}), 400

    output_filename = "./uploads/output_cv.docx"
    generate_docx(data, output_filename)
    return jsonify({
        "message": "CV generated successfully",
        "file": output_filename,
        "html_file": docx_to_html(output_filename)
    })

@app.route('/improve', methods=['POST'])
def improve():
    """💎 Improve CV content with OpenAI."""
    text = request.json.get('text', '')
    if not text:
        return jsonify({'improved_text': 'No text provided.'}), 400

    prompt = f"Improve and structure the following CV content with professional language and clear sections:\n\n{text}"
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
        generate_cv_pdf(parsed_data)
        return jsonify({'improved_text': improved_text, 'pdf_url': url_for('download_cv')})
    except Exception as e:
        return jsonify({'improved_text': f"Error: {str(e)}"}), 500

# -------------------- 🚀 RUN APP --------------------

if __name__ == '__main__':
    app.run(debug=True)