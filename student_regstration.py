import sqlite3
import io
from PIL import Image
import face_recognition
import numpy as np
import cv2

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
    conn.commit()
    conn.close()
    print("Database and table created successfully.")

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

# Function to fetch student details by ID
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
    else:
        print("Student not found.")

    conn.close()

# Function to mark attendance from a group photo
def mark_attendance(photo_path):
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    # Load the group photo
    group_image = face_recognition.load_image_file(photo_path)
    group_face_encodings = face_recognition.face_encodings(group_image)

    # Fetch all student face encodings from the database
    cursor.execute("SELECT id, name, face_encoding FROM students")
    students = cursor.fetchall()

    present_students = []
    for student in students:
        student_id = student[0]
        student_name = student[1]
        student_face_encoding = np.frombuffer(student[2], dtype=np.float64)

        # Compare each face encoding in the group photo with the student's encoding
        for face_encoding in group_face_encodings:
            matches = face_recognition.compare_faces([student_face_encoding], face_encoding)
            if True in matches:
                present_students.append((student_id, student_name))
                break

    # Mark attendance (this can be modified to suit your needs)
    print("Attendance marked for the following students:")
    for student_id, student_name in present_students:
        print(f"ID: {student_id}, Name: {student_name}")

    conn.close()

# Main execution flow
if __name__ == "__main__":
    create_database()
    
    while True:
        print("\n1. Register Student")
        print("2. Fetch Student")
        print("3. Mark Attendance from Group Photo")
        print("4. Exit")
        choice = input("Enter your choice: ")

        if choice == '1':
            name = input("Enter student name: ")
            age = int(input("Enter student age: "))
            email = input("Enter student email: ")
            image_path = input("Enter image path: ")
            student_id = register_student(name, age, email, image_path)

        elif choice == '2':
            student_id = int(input("Enter student ID to fetch: "))
            fetch_student(student_id)

        elif choice == '3':
            photo_path = input("Enter path to the group photo: ")
            mark_attendance(photo_path)

        elif choice == '4':
            print("Exiting the program.")
            break

        else:
            print("Invalid choice. Please try again.")
