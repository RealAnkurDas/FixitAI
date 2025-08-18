from flask import Flask, request, Response, render_template
from spare import RepairAssistantSystem
import os, time, tempfile

app = Flask(__name__)
system = RepairAssistantSystem()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.form.get("message", "")
    image_file = request.files.get("image")

    image_path = None
    if image_file and image_file.filename != "":
        # Save to temp file
        tmp_dir = tempfile.mkdtemp()
        image_path = os.path.join(tmp_dir, image_file.filename)
        image_file.save(image_path)

    # AI response
    full_response = system.process_user_input(user_input, image_path)

    def generate():
        for word in full_response.split():
            yield word + " "
            time.sleep(0.04)
    return Response(generate(), mimetype="text/plain")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
