from flask import Flask, render_template, request, jsonify, send_file, url_for, send_from_directory
import openai, whisper, os, re
from dotenv import load_dotenv
from docx import Document 
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from weasyprint import HTML


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

@app.route('/features')
def features():
    return render_template('features.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

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

# @app.route('/download')
# def download_cv():
#     return send_file('uploads/cv_result.pdf', as_attachment=True, download_name="Your_CV.pdf")

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

# @app.route('/generate_docx', methods=['POST'])
# def generate_docx_file():
#     """Generate a DOCX file from structured CV data."""
#     data = request.json.get('structured_data', {})

#     if not data:
#         return jsonify({"error": "No structured data provided."}), 400

#     output_filename = "./uploads/output_cv.docx"
#     generate_docx(data, output_filename)

#     return jsonify({"message": "CV generated successfully", "file": output_filename, "html_file": docx_to_html(output_filename)})


def docx_to_html(docx_path, output_html_path):
    """Convert DOCX to HTML and save the result to a file."""
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"Input DOCX file not found: {docx_path}")

    # Convert DOCX to HTML using LibreOffice headless mode
    os.system(f"/Applications/LibreOffice.app/Contents/MacOS/soffice --headless --convert-to html {docx_path} --outdir ./uploads")

    # # Check if the HTML file was created
    # if not os.path.exists(output_html_path):
    #     raise FileNotFoundError(f"Failed to generate HTML file: {output_html_path}")

    return output_html_path



def html_to_pdf(html_path, pdf_path):
    # Read the HTML file
    html = HTML(filename=html_path)

    # Render HTML to PDF and save it
    html.write_pdf(pdf_path)

# Route to generate PDF from DOCX
@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    try:
        data = request.get_json()
        html_content = data.get('html')

        if not html_content:
            return jsonify({"error": "No HTML content provided"}), 400

        # Save the HTML content to a temporary file
        temp_html_path = "temp_document.html"
        with open(temp_html_path, "w", encoding="utfç-8") as file:
            file.write(html_content)

        # Convert the HTML file to a PDF
        pdf_path = "output.pdf"
        HTML(filename=temp_html_path).write_pdf(pdf_path)

        # Return the generated PDF file as a response
        return send_file(pdf_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/editor')
def editor():
    return render_template('editor.html') 

@app.route('/generate_html')
def generate_cv():
    docx_path = 'output_cv.docx'
    
    if os.path.exists(docx_path):
        html_file = docx_to_html(docx_path)

        # Read HTML and remove unwanted tags
        with open(html_file, 'r', encoding="utf-8") as file:
            html_content = file.read()

        # Remove unwanted <html>, <body>, etc.
        html_content = html_content.replace("<html>", "").replace("</html>", "")
        html_content = html_content.replace("<body>", "").replace("</body>", "")

        return html_content  # Send as raw HTML (not JSON)
    else:
        return "File not found", 404
    

@app.route('/generate_docx', methods=['POST'])
def generate_docx_file():
    """Generate a DOCX file from structured CV data."""
    data = request.json.get('structured_data', {})

    if not data:
        return jsonify({"error": "No structured data provided."}), 400

    # Generate DOCX
    output_docx_filename = "./uploads/output_cv.docx"
    generate_docx(data, output_docx_filename)

    # Convert DOCX to HTML
    output_html_filename = "./uploads/output_cv.html"
    try:
        html_file = docx_to_html(output_docx_filename, output_html_filename)
    except Exception as e:
        return jsonify({"error": f"Error converting DOCX to HTML: {str(e)}"}), 500

    # Return file links for both DOCX and HTML
    return jsonify({
        "message": "CV generated successfully", 
        "file": url_for('download_cv', filename='output_cv.docx'),
        "html_file": url_for('download_html', filename='output_cv.html')
    })

@app.route('/download_html/<filename>')
def download_html(filename):
    return send_from_directory('uploads', filename)

@app.route('/download_cv/<filename>')
def download_cv(filename):
    return send_from_directory('uploads', filename)


if __name__ == '__main__':
    app.run(debug=True)