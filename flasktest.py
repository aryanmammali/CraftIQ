import os
import sqlite3
import cv2
import torch
import supervision as sv
from ultralytics import YOLO
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename

#Flask Setup 
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MODEL_FOLDER'] = 'static/models'  
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['MODEL_FOLDER'], exist_ok=True)

# Gemini AI Setup 
GEMINI_API_KEY = "AIzaSyAuctFZu4tnAVwMmH2_EupQFd47o6JddBA"
genai.configure(api_key=GEMINI_API_KEY)

# YOLO Setup 
model = YOLO("yolov8s.pt")

# SQLite Database Setup 
db_path = r"C:\Users\Aryan\OneDrive\Desktop\miniproject\manufacture.db"
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()

# Preload known labels from DB
cursor.execute("SELECT product_name FROM manufacturing")
db_labels = {row[0].lower() for row in cursor.fetchall()}

# 3D Model Mapping
object_to_model = {
    "mobile": "cell_phone.glb",
    "laptop": "laptop.glb",
    "car": "carupdated.glb",
    "fan":"fan.glb",
    "motorcycle":"bike.glb",
    "airplane":"airplane.glb"
}

# Routes 

@app.route('/')
def home():
    return render_template("index.html")


@app.route('/process-image', methods=['POST'])
def process_image():
    query_product_name = None

    # 1. Manual Input
    if 'manual_input' in request.form:
        query_product_name = request.form['manual_input'].strip().lower()

    # 2. Image Upload
    elif 'file' in request.files:
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({"error": "No file selected."})

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        image = cv2.imread(filepath)
        if image is None:
            return jsonify({"error": "Could not read uploaded image."})

        results = model(image)
        detections = sv.Detections.from_ultralytics(results[0])
        detected_objects = list(set(model.names[class_id].lower() for class_id in detections.class_id))

        if not detected_objects:
            return jsonify({"response": "No objects detected in the image."})

        if len(detected_objects) == 1:
            query_product_name = detected_objects[0]
            model_filename = object_to_model.get(query_product_name)
            model_url = f"/models/{model_filename}" if model_filename else None

            return jsonify({
                "response": f"Detected: {query_product_name.capitalize()}",
                "detected_object": query_product_name,
                "model_url": model_url
            })

        return jsonify({"multiple_objects": detected_objects})

    else:
        return jsonify({"error": "No input provided (file or manual)."})

    # 3. Query from Database or Gemini
    if query_product_name:
        mapping = {
            "cell phone": "mobile",
            "smartphone": "mobile",
            "notebook": "laptop",
            "sheet": "paper"
        }
        query_product_name = mapping.get(query_product_name, query_product_name)

        if query_product_name in db_labels:
            cursor.execute("SELECT product_id FROM manufacturing WHERE LOWER(product_name) = ?", (query_product_name,))
            product = cursor.fetchone()

            if product:
                product_id = product[0]
                cursor.execute('''
                    SELECT step_number, step_name, step_description
                    FROM manufacturing_steps
                    WHERE product_id = ?
                    ORDER BY step_number
                ''', (product_id,))
                steps = cursor.fetchall()

                if steps:
                    response_text = f"🛠️ Manufacturing Process for {query_product_name.capitalize()}:\n\n"
                    for step in steps:
                        response_text += f"🔹 Step {step[0]}: {step[1]}\n➡️ {step[2]}\n\n"

                    model_filename = object_to_model.get(query_product_name)
                    model_url = f"/models/{model_filename}" if model_filename else None

                    return jsonify({
                        "response": response_text.strip(),
                        "model_url": model_url
                    })
                else:
                    return jsonify({"response": "Manufacturing steps not found in database."})
        else:
            # Fallback to Gemini AI
            try:
                gemini_model = genai.GenerativeModel("gemini-2.0-flash")
                prompt = f"Explain how a {query_product_name} is manufactured, including steps."
                response = gemini_model.generate_content(prompt)

                if hasattr(response, 'text'):
                    return jsonify({"response": response.text})
                else:
                    return jsonify({"response": "AI could not generate a response."})
            except Exception as e:
                print("Gemini Error:", e)
                return jsonify({"response": "Error contacting AI service."})

    return jsonify({"response": "Could not process the request."})


@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.get_json()
    user_input = data.get("message", "").lower()

    manufacturing_keywords = [
        "manufacturing", "how is", "made", "assembled", "working",
        "physics", "mechanism", "parts", "object", "material",
        "process", "machinery", "components", "tools", "production",
        "equipment", "fabrication","work"
    ]

    if not any(keyword in user_input for keyword in manufacturing_keywords):
        return jsonify({
            "response": "⚙️ I can only assist with manufacturing, objects, machines, tools, physics, and production-related queries."
        })

    try:
        gemini_model = genai.GenerativeModel("gemini-2.0-flash")
        response = gemini_model.generate_content(user_input)

        if hasattr(response, 'text'):
            return jsonify({"response": response.text})
        else:
            return jsonify({"response": "I couldn’t understand. Please ask a manufacturing-related question!"})
    except Exception as e:
        print("Gemini Error:", e)
        return jsonify({"response": "Something went wrong while contacting AI."})


@app.route('/models/<path:filename>')
def serve_3d_model(filename):
    return send_from_directory(app.config['MODEL_FOLDER'], filename)


# Run App 
if __name__ == '__main__':
    app.run(debug=True)
