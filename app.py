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

@app.route('/')
def home():
    return render_template("select_course.html", courses=courses_data.keys())

# --- หน้าหลักรายวิชา (ยุบรวมเหลืออันเดียวแล้ว) ---
@app.route('/course/<course_id>')
def course_view(course_id):
    if course_id not in courses_data:
        return redirect(url_for('home'))
    
    students = courses_data[course_id]
    
    # คำนวณสถิติส่งไปให้หน้าเว็บ (Stats Card)
    stats = {
        'Weak': len([s for s in students if s[5] == 'Weak']),
        'Average': len([s for s in students if s[5] == 'Average']),
        'Good': len([s for s in students if s[5] == 'Good'])
    }
    
    return render_template("index.html", 
                           course_id=course_id, 
                           students=students, 
                           stats=stats,
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

# -------- SEARCH & FILTER (แก้ไขระบบ Search ชื่อ + Filter กลุ่ม) --------
@app.route('/search/<course_id>')
def search(course_id):
    query = request.args.get('query')
    filter_group = request.args.get('filter_group')
    students = courses_data.get(course_id, [])
    
    display_students = students 
    found_student = None

    if query:
        # ลองค้นด้วย ID (Jump Search)
        arr = sorted(students, key=lambda x: x[1])
        n = len(arr)
        if n > 0:
            step = int(math.sqrt(n))
            prev = 0
            while prev < n and arr[min(step, n)-1][1] < query:
                prev = step
                step += int(math.sqrt(n))
                if prev >= n: break
            while prev < n and arr[prev][1] < query:
                prev += 1
                if prev == min(step, n): break
            
            if prev < n and arr[prev][1] == query:
                found_student = arr[prev]
                display_students = [found_student]
            else:
                # ถ้าหา ID ไม่เจอ ให้ใช้ Linear Search ค้นหาจาก "ชื่อ"
                display_students = [s for s in students if query.lower() in s[0].lower()]

    if filter_group and filter_group != "All":
        display_students = [s for s in display_students if s[5] == filter_group]

    # ต้องคำนวณ stats ส่งกลับไปด้วยเพื่อให้หน้าเว็บไม่พัง
    stats = {
        'Weak': len([s for s in students if s[5] == 'Weak']),
        'Average': len([s for s in students if s[5] == 'Average']),
        'Good': len([s for s in students if s[5] == 'Good'])
    }

    return render_template("index.html", 
                           course_id=course_id, 
                           students=display_students, 
                           all_students=students, 
                           stats=stats,
                           searched=True,
                           result=found_student,
                           query=query,
                           current_filter=filter_group)

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
        plt.savefig(f"static/chart_{course_id}.png")
        plt.close()

    return redirect(url_for('course_view', course_id=course_id))

if __name__ == '__main__':
    app.run(debug=True)