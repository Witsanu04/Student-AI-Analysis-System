from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import numpy as np
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

from sklearn.model_selection import train_test_split
from sklearn.svm import SVC

app = Flask(__name__)

if not os.path.exists('static'):
    os.makedirs('static')

# ---------------- DATA ----------------
# ใช้ Dictionary เก็บข้อมูลแยกตามรหัสวิชา
courses_data = {
    "CE331": [],
    "CE332": [],
    "CE334": []
}
class_names = ['Weak', 'Average', 'Good']

# ---------------- AI MODEL ----------------
raw_data = np.array([
    [30,1,14],[49,2,13],[55,3,12],[62,5,10],[71,7,8],
    [79,9,6],[86,10,5],[91,12,3],[97,15,0]
])
y = np.array([0,0,0,1,1,1,2,2,2])

X_train, X_test, y_train, y_test = train_test_split(raw_data, y, test_size=0.3, random_state=42)
model = SVC(kernel='linear')
model.fit(X_train, y_train)

def get_group(score, attendance, absence):
    pred = model.predict([[score, attendance, absence]])
    return class_names[pred[0]]

# ---------------- ROUTES ----------------

# หน้าแรกสำหรับเลือกวิชา
@app.route('/')
def home():
    return render_template("select_course.html", courses=courses_data.keys())

# หน้าหลักของแต่ละรายวิชา
@app.route('/course/<course_id>')
def course_view(course_id):
    if course_id not in courses_data:
        return redirect(url_for('home'))
    
    students = courses_data[course_id]
    return render_template("index.html", 
                           course_id=course_id, 
                           students=students, 
                           searched=False)

# -------- ADD --------
@app.route('/add/<course_id>', methods=['POST'])
def add(course_id):
    if course_id in courses_data:
        name = request.form['name']
        sid = request.form['id']
        score = float(request.form['score'])
        attendance = float(request.form['attendance'])
        absence = float(request.form['absence'])

        group = get_group(score, attendance, absence)
        courses_data[course_id].append([name, sid, score, attendance, absence, group])
    
    return redirect(url_for('course_view', course_id=course_id))

# -------- UPLOAD EXCEL --------
@app.route('/upload/<course_id>', methods=['POST'])
def upload(course_id):
    file = request.files['file']
    if file and course_id in courses_data:
        try:
            df = pd.read_excel(file)
            for _, row in df.iterrows():
                name, sid = row.iloc[0], str(row.iloc[1])
                score, att, absn = float(row.iloc[2]), float(row.iloc[3]), float(row.iloc[4])
                group = get_group(score, att, absn)
                courses_data[course_id].append([name, sid, score, att, absn, group])
        except Exception as e:
            print(f"Error: {e}")
            
    return redirect(url_for('course_view', course_id=course_id))

# -------- SEARCH (JUMP SEARCH) --------
@app.route('/search/<course_id>')
def search(course_id):
    sid = request.args.get('id')
    students = courses_data.get(course_id, [])
    
    found_student = None
    if sid and students:
        # เรียงลำดับก่อนค้นหา
        arr = sorted(students, key=lambda x: x[1])
        n = len(arr)
        step = int(math.sqrt(n))
        prev = 0
        
        while prev < n and arr[min(step, n)-1][1] < sid:
            prev = step
            step += int(math.sqrt(n))
            if prev >= n: break
            
        while prev < n and arr[prev][1] < sid:
            prev += 1
            if prev == min(step, n): break
            
        if prev < n and arr[prev][1] == sid:
            found_student = arr[prev]

    # แก้จุดตาย: ต้องส่ง course_id กลับไปด้วยเสมอ
    return render_template("index.html", 
                           course_id=course_id, 
                           students=students, 
                           result=found_student, 
                           searched=True)

# -------- GRAPH --------
@app.route('/graph/<course_id>')
def graph(course_id):
    students = courses_data.get(course_id, [])
    if students:
        scores = [s[2] for s in students]
        plt.figure(figsize=(6,4))
        plt.hist(scores, bins=10, color='skyblue', edgecolor='black')
        plt.title(f"Score Distribution - {course_id}")
        plt.tight_layout()
        # เซฟชื่อไฟล์แยกตามวิชาเพื่อไม่ให้ทับกัน
        plt.savefig(f"static/chart_{course_id}.png")
        plt.close()

    return redirect(url_for('course_view', course_id=course_id))

if __name__ == '__main__':
    app.run(debug=True)