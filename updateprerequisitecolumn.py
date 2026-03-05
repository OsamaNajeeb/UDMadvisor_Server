import sqlite3

# Paths to your SQLite database files
db_with_prereqs_path = "temp.db"
db_without_prereqs_path = "fall2025.db"

# Connect to both databases
conn1 = sqlite3.connect(db_with_prereqs_path)  # DB that has pre_requisites
conn2 = sqlite3.connect(db_without_prereqs_path)  # DB missing pre_requisites

cursor_with_prereqs = conn1.cursor()
cursor_without_prereqs = conn2.cursor()

# Fetch courses with prerequisites from db_with_prereqs
cursor_with_prereqs.execute("""
    SELECT course_code, section, pre_requisite FROM courses WHERE pre_requisite IS NOT NULL
""")

prereq_data = cursor_with_prereqs.fetchall()

# Update courses in db_without_prereqs
for course_code, section, pre_requisite in prereq_data:
    cursor_without_prereqs.execute("""
        UPDATE courses 
        SET pre_requisite = ? 
        WHERE course_code = ? AND section = ? AND (pre_requisite IS NULL OR pre_requisite = 'None')
    """, (pre_requisite, course_code, section))

# Commit changes and close connections
conn2.commit()
conn1.close()
conn2.close()

print("Prerequisites updated successfully!")