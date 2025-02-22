from flask import Flask, render_template_string, send_file, send_from_directory
import os

app = Flask(__name__)

# Function to convert DOCX to HTML using LibreOffice (headless)
def docx_to_html(docx_path):
    output_html_path = docx_path.replace('.docx', '.html')
    
    # Ensure the DOCX file exists before proceeding
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"Input DOCX file not found: {docx_path}")

    # Convert DOCX to HTML using LibreOffice headless mode
    os.system(f"/Applications/LibreOffice.app/Contents/MacOS/soffice --headless --convert-to html {docx_path}")

    # Check if the HTML file was created
    if not os.path.exists(output_html_path):
        raise FileNotFoundError(f"Failed to generate HTML file: {output_html_path}")

    return output_html_path

@app.route('/generate')
def generate_cv():
    docx_path = 'output_cv.docx'
    
    if os.path.exists(docx_path):
        # Convert DOCX to HTML
        html_file = docx_to_html(docx_path)

        # Serve the HTML file directly
        return send_from_directory(directory=os.path.dirname(html_file), path=os.path.basename(html_file))
    else:
        return "File not found", 404

@app.route('/')
def index():
    return send_file('index.html')

if __name__ == '__main__':
    app.run(debug=True)
