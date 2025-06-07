from flask import Flask, request, send_from_directory, render_template_string, redirect
import os, base64, uuid, json
import face_recognition

app = Flask(__name__)
os.makedirs("uploads", exist_ok=True)
os.makedirs("registered", exist_ok=True)

@app.route('/')
def index():
    return redirect("/entry")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return open("register.html").read()
    name = request.form['name']
    dob = request.form['dob']
    citizenship = request.form['citizenship']
    photo = request.files['photo']
    filename = f"{uuid.uuid4()}.jpg"
    filepath = os.path.join("registered", filename)
    photo.save(filepath)
    record = {
        "name": name,
        "dob": dob,
        "citizenship": citizenship,
        "photo": filename
    }
    with open(os.path.join("registered", filename.replace(".jpg", ".json")), "w") as f:
        json.dump(record, f)
    return redirect("/register")

@app.route('/entry')
def entry():
    return open("entry.html").read()

@app.route('/upload', methods=['POST'])
def upload():
    data = request.get_json()
    if data and 'image' in data:
        image_data = data['image'].split(',')[1]
        filename = f"{uuid.uuid4()}.jpg"
        filepath = os.path.join("uploads", filename)
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(image_data))

        # Process face match
        try:
            entry_img = face_recognition.load_image_file(filepath)
            entry_encodings = face_recognition.face_encodings(entry_img)
            if not entry_encodings:
                print("No face found.")
                return ('', 204)

            entry_encoding = entry_encodings[0]
            best_match = None
            best_distance = 0.5

            for file in os.listdir("registered"):
                if file.endswith(".jpg"):
                    reg_img_path = os.path.join("registered", file)
                    reg_data_path = reg_img_path.replace(".jpg", ".json")

                    reg_img = face_recognition.load_image_file(reg_img_path)
                    reg_encodings = face_recognition.face_encodings(reg_img)
                    if reg_encodings:
                        distance = face_recognition.face_distance([reg_encodings[0]], entry_encoding)[0]
                        if distance < best_distance:
                            best_distance = distance
                            with open(reg_data_path) as f:
                                data = json.load(f)
                            best_match = data
                            best_match["confidence"] = f"{(1 - distance):.2f}"
                            best_match["photo"] = file

            if best_match:
                with open(os.path.join("uploads", filename.replace(".jpg", ".json")), "w") as f:
                    json.dump(best_match, f)
        except Exception as e:
            print(f"Error: {e}")
    return ('', 204)

@app.route('/officer')
def officer():
    entries = []
    for f in os.listdir("uploads"):
        if f.endswith(".jpg"):
            match_path = os.path.join("uploads", f.replace(".jpg", ".json"))
            match_data = None
            if os.path.exists(match_path):
                with open(match_path) as m:
                    match_data = json.load(m)
            entries.append({
                "photo": f,
                "match": match_data
            })
    return render_template_string(open("officer.html").read(), entries=entries)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory("uploads", filename)

@app.route('/registered/<filename>')
def registered_file(filename):
    return send_from_directory("registered", filename)

@app.route('/static/<filename>')
def static_file(filename):
    return send_from_directory("static", filename)

@app.route('/decision/<filename>', methods=['POST'])
def decision(filename):
    os.remove(os.path.join("uploads", filename))
    json_path = os.path.join("uploads", filename.replace(".jpg", ".json"))
    if os.path.exists(json_path):
        os.remove(json_path)
    return redirect("/officer")

if __name__ == '__main__':
    app.run(debug=True)