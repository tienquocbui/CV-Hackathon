from flask import Flask, render_template, request, jsonify, send_file, url_for
import openai, whisper, os, re
from dotenv import load_dotenv
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
        "Summary": re.search(r"Summary[:\-]\s*(.*)", text, re.IGNORECASE),
        "Skills": re.search(r"Skills[:\-]\s*(.*)", text, re.IGNORECASE),
        "Experience": re.search(r"Experience[:\-]\s*(.*)", text, re.IGNORECASE),
        "Education": re.search(r"Education[:\-]\s*(.*)", text, re.IGNORECASE),
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

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'text': 'No file uploaded'}), 400

    audio_path = os.path.join('uploads', 'temp.wav')
    request.files['audio'].save(audio_path)

    try:
        result = whisper_model.transcribe(audio_path)
        return jsonify({'text': result['text']})
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

if __name__ == '__main__':
    app.run(debug=True)