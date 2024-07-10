from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mysqldb import MySQL
import cv2
import face_recognition
import numpy as np
import base64

app = Flask(__name__)
app.config.from_object('config.Config')

mysql = MySQL(app)

# Load the Haar Cascade Classifier for face detection
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

def convert_image(image):
    # Convert the image to grayscale for face detection using Haar Cascade
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Detect faces using Haar Cascade
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30))
    
    if len(faces) == 0:
        raise ValueError("No faces found in the image.")
    
    # Assuming only one face is detected for simplicity
    (x, y, w, h) = faces[0]
    face_roi = gray[y:y+h, x:x+w]
    
    # Compute face encodings using face_recognition library
    face_encoding = face_recognition.face_encodings(image, [(y, x+w, y+h, x)])[0]
    
    return face_encoding

@app.route('/')
def index():
    return "Index Page"

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        image_file = request.files['image']
        image_data = image_file.read()
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        try:
            face_encoding = convert_image(img)  # Assuming this function converts the image to face encoding
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        cursor = mysql.connection.cursor()
        
        # Check if the username already exists in the database
        cursor.execute('''SELECT * FROM users WHERE username = %s''', (username,))
        user = cursor.fetchone()

        if user:
            # Update the existing record for the specified username
            cursor.execute('''UPDATE users SET face_encoding = %s WHERE username = %s''', (face_encoding.tostring(), username))
            mysql.connection.commit()
            cursor.close()
            return jsonify({'success': 'Face encoding updated successfully.'}), 200
        else:
            error_message = f"User '{username}' does not exist."
            return jsonify({'error': error_message}), 404

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        image_data = request.form['image'].split(",")[1]
        image_data = base64.b64decode(image_data)
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        try:
            face_encoding = convert_image(img)
        except ValueError as e:
            error_message = str(e)
            return render_template('login.html', error_message=error_message)

        cursor = mysql.connection.cursor()
        cursor.execute(''' SELECT username, face_encoding FROM users ''')
        users = cursor.fetchall()
        cursor.close()

        for user in users:
            stored_encoding = np.frombuffer(user[1], np.float64)
            matches = face_recognition.compare_faces([stored_encoding], face_encoding)
            if matches[0]:
                session['username'] = user[0]
                return redirect('http://localhost/FoodOrder/index.php?username=' + session['username'])

        # If no match found, display an alert
        return render_template('login.html', error_message='Face not recognized.')

    return render_template('login.html')


@app.route('/home')
def home():
    if 'username' in session:
        return f"{session['username']}!"
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)