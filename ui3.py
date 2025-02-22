from flask import Flask, render_template, send_from_directory, request, jsonify, send_file
import os
from weasyprint import HTML

app = Flask(__name__)

# Function to convert DOCX to HTML using LibreOffice (headless)
def docx_to_html(docx_path):
    output_html_path = docx_path.replace('.docx', '.html')

    # Ensure DOCX file exists
    if not os.path.exists(docx_path):
        raise FileNotFoundError("DOCX file not found.")

    # Convert to HTML
    os.system(f"/Applications/LibreOffice.app/Contents/MacOS/soffice --headless --convert-to html {docx_path}")

    # Ensure HTML was created
    if not os.path.exists(output_html_path):
        raise FileNotFoundError("HTML file conversion failed.")

    return output_html_path

# @app.route('/generate')
# def generate_cv():
#     docx_path = 'output_cv.docx'
    
#     if os.path.exists(docx_path):
#         html_file = docx_to_html(docx_path)
#         return send_from_directory(directory=os.path.dirname(html_file), path=os.path.basename(html_file))
#     else:
#         return "File not found", 404

@app.route('/generate')
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
    
@app.route('/')
def index():
    return render_template('editor.html')


@app.route('/editor')
def editor():
    return render_template('editor.html') 

if __name__ == '__main__':
    app.run(debug=True)
    app = Flask(__name__, template_folder='templates')
    app.config['WTF_CSRF_ENABLED'] = False


