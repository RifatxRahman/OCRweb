import os
import json
import tempfile
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'replace-with-a-secure-random-key')

UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
METADATA_FILE = os.path.join(app.root_path, 'metadata.json')
ALLOWED_EXT = {'.png', '.jpg', '.jpeg'}
MAX_CONTENT_LENGTH = 6 * 1024 * 1024  # 6 MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def load_metadata():
    if not os.path.exists(METADATA_FILE):
        return []
    try:
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_metadata_atomic(entries):
    dirpath = os.path.dirname(METADATA_FILE) or '.'
    fd, tmp_path = tempfile.mkstemp(dir=dirpath, prefix='meta_', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, METADATA_FILE)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass

def append_metadata(entry):
    entries = load_metadata()
    entries.append(entry)
    save_metadata_atomic(entries)

def allowed_file(filename, mimetype=None):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXT:
        return False
    if mimetype and not mimetype.startswith('image/'):
        return False
    return True

@app.errorhandler(RequestEntityTooLarge)
def file_too_large(e):
    return "Uploaded file is too large (max 6MB)", 413

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        writing_style = request.form.get('writing_style', '')
        handedness = request.form.get('handedness', '')
        age_group = request.form.get('age_group', '')
        gender = request.form.get('gender', '')

        session['metadata'] = {
            'writing_style': writing_style,
            'handedness': handedness,
            'age_group': age_group,
            'gender': gender
        }
        return redirect(url_for('upload_photo'))
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_photo():
    metadata = session.get('metadata')
    if not metadata:
        return redirect(url_for('index'))

    if request.method == 'POST':
        file = request.files.get('photo')
        if not file:
            return "No file uploaded", 400
        if file.filename == '':
            return "No selected file", 400
        if not allowed_file(file.filename, mimetype=file.mimetype):
            return "File type not allowed", 400

        original = secure_filename(file.filename)
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        unique_suffix = os.urandom(4).hex()
        ext = os.path.splitext(original)[1].lower()
        filename = f"banglaocr_{timestamp}_{unique_suffix}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        try:
            file.save(filepath)
        except RequestEntityTooLarge:
            return "File too large", 413
        except Exception:
            return "Failed to save file", 500

        entry = {
            'filename': filename,
            'original_name': original,
            'timestamp': timestamp,
            **metadata
        }
        append_metadata(entry)

        return redirect(url_for('thank_you'))

    return render_template('upload.html')

@app.route('/thankyou')
def thank_you():
    contrib_count = len(load_metadata())
    return render_template('thankyou.html', count=contrib_count)

if __name__ == '__main__':
    app.run(debug=True)





if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
