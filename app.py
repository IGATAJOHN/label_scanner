from flask import Flask, request, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import cv2
import numpy as np
import re
import time
import base64
from flask_migrate import Migrate
app = Flask(__name__)
app.config['SECRET_KEY'] = '558b6e7e7c83f54e4367a9a554f09763'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///label_scanner.db'
app.config['UPLOAD_FOLDER'] = 'uploads/'

db = SQLAlchemy(app)
migrate=Migrate(app,db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
# Create the uploads folder if it does not exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
# Models
class Label(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_path = db.Column(db.String(150), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    keywords = db.Column(db.String(100))
    description = db.Column(db.String(250))
    upload_count = db.Column(db.Integer, default=1)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))

with app.app_context():
     db.create_all()
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return render_template('home.html')
@app.route('/detailed_results')
def detailed_results():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    labels = Label.query.paginate(page=page, per_page=per_page)

    next_url = url_for('detailed_results', page=labels.next_num) if labels.has_next else None
    prev_url = url_for('detailed_results', page=labels.prev_num) if labels.has_prev else None

    return render_template('detailed_results.html', labels=labels.items, next_url=next_url, prev_url=prev_url)

@app.route('/layout')
def layout():
    labels = Label.query.all()
    return render_template('layout.html', labels=labels)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Login failed. Check your username and/or password', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
        else:
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/upload', methods=['GET', 'POST'])
def upload_image():
    if request.method == 'POST':
        product_name = request.form.get('product_name', 'Unknown Product')
        brand = request.form.get('brand', 'Unknown Brand')
        image = request.files.get('image')
        keywords = request.form.get('keywords', '')
        description = request.form.get('description', '')

        if image:
            image_path = os.path.join('static/uploads', image.filename)
            image.save(image_path)
        
        else:
            photo_data = request.form.get('photo')
            if photo_data:
                import base64
                photo_data = photo_data.split(",")[1]
                image_data = base64.b64decode(photo_data)
                image_path = os.path.join('uploads', f"{product_name}_{brand}.png")
                with open(image_path, "wb") as fh:
                    fh.write(image_data)
            else:
                flash('No image provided!', 'error')
                return redirect(url_for('upload_image'))

        existing_label = Label.query.filter_by(product_name=product_name, brand=brand).first()
        if existing_label:
            existing_label.upload_count += 1
        else:
            new_label = Label(image_path=image_path, product_name=product_name, brand=brand,
                              keywords=keywords, description=description)
            db.session.add(new_label)

        db.session.commit()
        flash('Image uploaded successfully!', 'success')
        return redirect(url_for('upload_image'))
    return render_template('upload.html')

@app.route('/results')
@login_required
def results():
    matches = Label.query.all()
    return render_template('results.html', matches=matches)
def compare_images(img1, img2):
    # Resize images to the same size for comparison
    img1 = cv2.resize(img1, (100, 100))
    img2 = cv2.resize(img2, (100, 100))
    
    # Convert images to grayscale
    img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    
    # Calculate the difference and threshold it
    difference = cv2.absdiff(img1, img2)
    _, diff = cv2.threshold(difference, 30, 255, cv2.THRESH_BINARY)
    
    # Calculate the percentage of different pixels
    percentage_diff = np.sum(diff) / (100 * 100 * 255)
    
    # Define a threshold for matching
    threshold = 0.1  # Adjust this threshold based on your requirements
    
    return percentage_diff < threshold
def find_best_match(uploaded_image, database_images):
    matches = []
    for label in database_images:
        db_image = cv2.imread(label.image_path)
        if compare_images(uploaded_image, db_image):
            matches.append((label, label.upload_count))
    return sorted(matches, key=lambda x: x[1], reverse=True)
if __name__ == '__main__':
   
    app.run(debug=True)
