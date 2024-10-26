import streamlit as st
import sqlite3
import io
from PIL import Image
import face_recognition
import numpy as np
import pandas as pd
import os

# Function to create a database connection
def create_connection():
    conn = sqlite3.connect("students.db")
    return conn

# Function to create a class table if it doesn't exist
def create_class_table(class_name):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute(f'''CREATE TABLE IF NOT EXISTS {class_name} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        age INTEGER,
                        email TEXT UNIQUE,
                        image BLOB,
                        face_encoding BLOB
                    )''')
    conn.commit()
    conn.close()

# Function to convert binary data to an image
def convert_to_image(data):
    return Image.open(io.BytesIO(data))

# Function to register a student
def register_student(name, age, email, image_file, class_name):
    create_class_table(class_name)  # Ensure class table exists
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        image_data = image_file.read()
        face_encoding = get_face_encoding(image_file)

        cursor.execute(f'''INSERT INTO {class_name} (name, age, email, image, face_encoding)
                           VALUES (?, ?, ?, ?, ?)''',
                       (name, age, email, image_data, face_encoding))
        conn.commit()
        st.success(f"Student registered successfully in {class_name} class!")
        
    except sqlite3.IntegrityError:
        st.error("Error: Email already exists.")
    except Exception as e:
        st.error(f"An error occurred: {e}")
    finally:
        conn.close()

# Function to get face encoding from an image file
def get_face_encoding(image_file):
    image = face_recognition.load_image_file(image_file)
    encodings = face_recognition.face_encodings(image)
    if encodings:
        return encodings[0].tobytes()  # Convert to bytes for storing in DB
    return None

# Function to fetch student details and calculate attendance percentage
def fetch_student(student_id, class_name):
    conn = create_connection()
    cursor = conn.cursor()
    
    # Fetch student details
    cursor.execute(f"SELECT * FROM {class_name} WHERE id=?", (student_id,))
    student = cursor.fetchone()
    
    if not student:
        conn.close()
        return None, None, None
    
    # Fetch attendance records and calculate attendance percentage
    cursor.execute('''SELECT status FROM attendance 
                      WHERE student_id=? AND class_name=?''', (student_id, class_name))
    attendance_records = cursor.fetchall()
    
    total_classes = len(attendance_records)
    attended_classes = sum(1 for record in attendance_records if record[0] == 'Present')
    attendance_percentage = (attended_classes / total_classes) * 100 if total_classes > 0 else 0

    conn.close()
    return student, total_classes, attendance_percentage

# Function to mark attendance from a group photo
def mark_attendance(photo_file, period, class_name):
    create_class_table(class_name)  # Ensure class table exists
    conn = create_connection()
    cursor = conn.cursor()

    group_image = face_recognition.load_image_file(photo_file)
    group_face_encodings = face_recognition.face_encodings(group_image)

    cursor.execute(f"SELECT id, name, face_encoding FROM {class_name}")
    students = cursor.fetchall()

    present_students = []
    absent_students = []

    for student in students:
        student_id = student[0]
        student_name = student[1]
        student_face_encoding = np.frombuffer(student[2], dtype=np.float64)

        for face_encoding in group_face_encodings:
            matches = face_recognition.compare_faces([student_face_encoding], face_encoding, tolerance=0.6)
            if True in matches:
                present_students.append((student_id, student_name))
                break
        else:
            absent_students.append((student_id, student_name))

    # Log attendance in attendance table
    cursor.execute('''CREATE TABLE IF NOT EXISTS attendance (
                        student_id INTEGER,
                        class_name TEXT,
                        date TEXT,
                        period TEXT,
                        status TEXT
                    )''')

    for student_id, student_name in present_students:
        cursor.execute('''INSERT INTO attendance (student_id, class_name, date, period, status)
                          VALUES (?, ?, DATE('now'), ?, 'Present')''', (student_id, class_name, period))

    for student_id, student_name in absent_students:
        cursor.execute('''INSERT INTO attendance (student_id, class_name, date, period, status)
                          VALUES (?, ?, DATE('now'), ?, 'Absent')''', (student_id, class_name, period))

    conn.commit()
    conn.close()

    # Create DataFrames for present and absent students
    present_df = pd.DataFrame(present_students, columns=['Student ID', 'Name'])
    absent_df = pd.DataFrame(absent_students, columns=['Student ID', 'Name'])

    return present_df, absent_df

# Function to delete the database
def delete_database():
    if os.path.exists("students.db"):
        os.remove("students.db")
        st.success("Database deleted successfully.")
    else:
        st.error("Database does not exist.")

# Streamlit UI
st.title("Attendance Management System")

menu = ["Register Student", "Fetch Student Details", "Mark Attendance", "Delete Database"]
choice = st.sidebar.selectbox("Select an option", menu)

class_name = st.text_input("Enter the class name:")

if choice == "Register Student" and class_name:
    st.subheader("Register a New Student")
    name = st.text_input("Name")
    age = st.number_input("Age", min_value=0)
    email = st.text_input("Email")
    image_file = st.file_uploader("Upload Image", type=["jpg", "jpeg", "png"])

    if st.button("Register"):
        if name and age and email and image_file:
            register_student(name, age, email, image_file, class_name)
        else:
            st.error("Please fill in all fields.")

elif choice == "Fetch Student Details" and class_name:
    st.subheader("Fetch Student Details")
    student_id = st.number_input("Enter Student ID", min_value=1)

    if st.button("Fetch"):
        student, total_classes, attendance_percentage = fetch_student(student_id, class_name)
        if student:
            st.write("ID:", student[0])
            st.write("Name:", student[1])
            st.write("Age:", student[2])
            st.write("Email:", student[3])
            st.write("Class:", class_name)
            image_data = student[4]
            st.image(convert_to_image(image_data), caption="Student Image")
            
            # Display attendance report
            st.write("### Attendance Report")
            st.write("Total Classes:", total_classes)
            st.write("Attendance Percentage:", f"{attendance_percentage:.2f}%")
        else:
            st.error("Student not found.")

elif choice == "Mark Attendance" and class_name:
    st.subheader("Mark Attendance from Group Photo")
    photo_file = st.file_uploader("Upload Group Photo", type=["jpg", "jpeg", "png"])
    period = st.text_input("Enter Period (e.g., '1st Period')")

    if st.button("Mark Attendance"):
        if photo_file and period:
            present_df, absent_df = mark_attendance(photo_file, period, class_name)
            st.write("Attendance Marked:")
            st.write("### Present Students")
            st.dataframe(present_df)
            st.write("### Absent Students")
            st.dataframe(absent_df)
        else:
            st.error("Please fill in all fields.")

elif choice == "Delete Database":
    if st.button("Delete Database"):
        delete_database()
