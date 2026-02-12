from flask import Flask, render_template, request
import os
from services.demucs_service import separate_audio
from flask import send_from_directory

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
SEPARATED_FOLDER = "separated"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SEPARATED_FOLDER, exist_ok=True)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    audio = request.files.get("audio")

    if not audio:
        return "No file uploaded", 400

    file_path = os.path.join(UPLOAD_FOLDER, audio.filename)
    audio.save(file_path)

    output_folder = separate_audio(file_path)

    return render_template("result.html", folder=output_folder)


@app.route('/separated/<path:filename>')
def serve_separated_file(filename):
    return send_from_directory('separated', filename)


if __name__ == "__main__":
    app.run(debug=True)
