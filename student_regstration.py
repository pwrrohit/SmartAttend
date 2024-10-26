import sqlite3
import io
from PIL import Image
import face_recognition
import numpy as np
import os

# Database setup
def create_database():
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    # Create table for student registration with face encoding
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER NOT NULL,
        email TEXT NOT NULL UNIQUE,
        image BLOB NOT NULL,
        face_encoding BLOB
    )
    ''')

    # Create table for attendance
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        period TEXT NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY (student_id) REFERENCES students (id)
    )
    ''')

    conn.commit()
    conn.close()
    print("Database and tables created successfully.")

# Function to convert image file to binary
def convert_to_binary(file_path):
    with open(file_path, 'rb') as file:
        return file.read()

# Function to get face encoding from an image
def get_face_encoding(image_path):
    image = face_recognition.load_image_file(image_path)
    encodings = face_recognition.face_encodings(image)
    if encodings:
        return encodings[0].tobytes()  # Convert to bytes for storing in DB
    return None

# Function to register a student
def register_student(name, age, email, image_path):
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    try:
        # Convert image to binary format
        image_data = convert_to_binary(image_path)
        face_encoding = get_face_encoding(image_path)

        # Insert student data into the table
        cursor.execute('''
        INSERT INTO students (name, age, email, image, face_encoding)
        VALUES (?, ?, ?, ?, ?)
        ''', (name, age, email, image_data, face_encoding))

        conn.commit()
        student_id = cursor.lastrowid  # Get the ID of the last inserted row
        print(f"Student registered successfully with ID: {student_id}")
        return student_id
        
    except sqlite3.IntegrityError:
        print("Error: Email already exists.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

# Function to update student details
def update_student(student_id, name=None, age=None, email=None, image_path=None):
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    try:
        if image_path:
            image_data = convert_to_binary(image_path)
            face_encoding = get_face_encoding(image_path)
            cursor.execute('''
            UPDATE students 
            SET name = COALESCE(?, name),
                age = COALESCE(?, age),
                email = COALESCE(?, email),
                image = COALESCE(?, image),
                face_encoding = COALESCE(?, face_encoding)
            WHERE id = ?
            ''', (name, age, email, image_data, face_encoding, student_id))
        else:
            cursor.execute('''
            UPDATE students 
            SET name = COALESCE(?, name),
                age = COALESCE(?, age),
                email = COALESCE(?, email)
            WHERE id = ?
            ''', (name, age, email, student_id))

        conn.commit()
        print(f"Student ID {student_id} updated successfully.")
        
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

# Function to delete a student
def delete_student(student_id):
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM students WHERE id=?", (student_id,))
        conn.commit()
        print(f"Student ID {student_id} deleted successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

# Function to fetch student details and attendance report by ID
def fetch_student(student_id):
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM students WHERE id=?", (student_id,))
    student = cursor.fetchone()
    
    if student:
        print(f"ID: {student[0]}")
        print(f"Name: {student[1]}")
        print(f"Age: {student[2]}")
        print(f"Email: {student[3]}")
        
        # Convert binary image data back to an image
        image_data = student[4]
        image = Image.open(io.BytesIO(image_data))
        image.show()

        # Fetch attendance report
        cursor.execute("SELECT date, period, status FROM attendance WHERE student_id=?", (student_id,))
        attendance_records = cursor.fetchall()
        
        print("\nAttendance Report:")
        for record in attendance_records:
            print(f"Date: {record[0]}, Period: {record[1]}, Status: {record[2]}")
    else:
        print("Student not found.")

    conn.close()

# Function to mark attendance from a group photo
def mark_attendance(photo_path, period):
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    # Load the group photo
    group_image = face_recognition.load_image_file(photo_path)
    group_face_encodings = face_recognition.face_encodings(group_image)

    # Fetch all student face encodings from the database
    cursor.execute("SELECT id, name, face_encoding FROM students")
    students = cursor.fetchall()

    present_students = []
    absent_students = []
    
    for student in students:
        student_id = student[0]
        student_name = student[1]
        student_face_encoding = np.frombuffer(student[2], dtype=np.float64)

        # Compare each face encoding in the group photo with the student's encoding
        for face_encoding in group_face_encodings:
            matches = face_recognition.compare_faces([student_face_encoding], face_encoding, tolerance=0.6)
            if True in matches:
                present_students.append((student_id, student_name))
                break
        else:
            absent_students.append((student_id, student_name))

    # Mark attendance for present students
    for student_id, student_name in present_students:
        cursor.execute('''
        INSERT INTO attendance (student_id, date, period, status)
        VALUES (?, DATE('now'), ?, 'Present')
        ''', (student_id, period))

    # Mark attendance for absent students
    for student_id, student_name in absent_students:
        cursor.execute('''
        INSERT INTO attendance (student_id, date, period, status)
        VALUES (?, DATE('now'), ?, 'Absent')
        ''', (student_id, period))

    conn.commit()
    
    # Print attendance result
    print("Attendance marked:")
    for student_id, student_name in present_students:
        print(f"Present: ID: {student_id}, Name: {student_name}")
    for student_id, student_name in absent_students:
        print(f"Absent: ID: {student_id}, Name: {student_name}")

    conn.close()

# Function to delete the database
def delete_database():
    if os.path.exists("students.db"):
        os.remove("students.db")
        print("Database deleted successfully.")
    else:
        print("Database does not exist.")

# Main execution flow
if __name__ == "__main__":
    create_database()
    
    while True:
        print("\n1. Student Registration (Add, Update, Delete)")
        print("2. Fetch Student Details and Attendance Report")
        print("3. Mark Attendance from Group Photo")
        print("4. Delete Database")
        print("5. Exit")
        choice = input("Enter your choice: ")

        if choice == '1':
            action = input("Enter 'add' to add new student, 'update' to update existing student, or 'delete' to delete a student: ")
            if action == 'add':
                name = input("Enter student name: ")
                age = int(input("Enter student age: "))
                email = input("Enter student email: ")
                image_path = input("Enter image path: ")
                student_id = register_student(name, age, email, image_path)

            elif action == 'update':
                student_id = int(input("Enter student ID to update: "))
                name = input("Enter new name (or press Enter to skip): ") or None
                age = input("Enter new age (or press Enter to skip): ")
                age = int(age) if age else None
                email = input("Enter new email (or press Enter to skip): ") or None
                image_path = input("Enter new image path (or press Enter to skip): ") or None
                update_student(student_id, name, age, email, image_path)

            elif action == 'delete':
                student_id = int(input("Enter student ID to delete: "))
                delete_student(student_id)

            else:
                print("Invalid action. Please try again.")

        elif choice == '2':
            student_id = int(input("Enter student ID to fetch: "))
            fetch_student(student_id)

        elif choice == '3':
            photo_path = input("Enter path to the group photo: ")
            period = input("Enter the period (e.g., '1st Period'): ")
            mark_attendance(photo_path, period)

        elif choice == '4':
            delete_database()

        elif choice == '5':
            print("Exiting the program.")
            break

        else:
            print("Invalid choice. Please try again.")
