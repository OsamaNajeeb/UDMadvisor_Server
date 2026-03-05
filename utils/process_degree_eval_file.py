import base64
from email import message_from_binary_file
from bs4 import BeautifulSoup
# from sql_client import find_element
import json
import ast
import html
from flask import jsonify
import re 
import pandas as pd


def get_content(cell,index):
    cell_content = cell.decode_contents()
   
    if index == 0:
        if "Yes" in cell_content: return "Yes" 
        return "No"

    cell_soup = BeautifulSoup(cell_content, 'lxml')
    remaining_text = cell_soup.div.next_sibling

    return remaining_text.strip()
    
def clean_text(text):
    text = re.sub(r'=\s*', '', text)

    # Fix missing spaces between words by adding a space before capital letters if needed
    text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)  # Add space between lowercase-uppercase transitions

    # Restore spaces that may have been lost before hyphens
    text = re.sub(r'(?<=\w)-(?=\w)', ' - ', text)  # Ensure spaces around hyphens

    # Remove non-breaking spaces and weird encoded characters
    text = text.replace('\xa0', ' ').replace('&nbsp;', ' ')

    # Collapse multiple spaces into one
    text = re.sub(r'\s+', ' ', text)

    text = text.strip()
        
    return text 



def parse_requirement_table(table):
    """
    Parse an HTML table handling rowspans and colspans.
    Returns a list of rows (each row is a list of cell texts).
    """
    rows = table.find_all("tr")
    grid = []
    # Dictionary to track cells with rowspan that should appear in future rows.
    # Keys are (row_index, col_index) tuples.
    spanning = {}
    
    for row_index, row in enumerate(rows):
        cells = row.find_all("td")
        row_data = []
        col = 0
        # Check if any cell from previous row spans into this row.
        while (row_index, col) in spanning:
            row_data.append(spanning[(row_index, col)])
            col += 1
        
        for cell in cells:
            # Remove header divs (e.g., the "Met", "Requirement", etc. labels)
            for header in cell.find_all("div", class_="xe-col-xs"):
                header.decompose()
            text = cell.get_text(separator=" ", strip=True)
            rowspan = int(cell.get("rowspan", 1))
            colspan = int(cell.get("colspan", 1))
            
            # Fill in the cell (and duplicate if colspan > 1)
            for i in range(col, col + colspan):
                row_data.append(text)
                # If rowspan > 1, mark this cell for the following rows.
                if rowspan > 1:
                    for j in range(1, rowspan):
                        spanning[(row_index + j, i)] = text
            col += colspan
        grid.append(row_data)
    return grid

def clean_duplicate_not_met_requirements(course_list):
    # Extract courses that fulfill requirements
    met_requirements = {}
    pattern = re.compile(r"Met with program requirement: ([A-Z]+ \d+)")
    
    for course in course_list:
        match = pattern.search(course)
        if match:
            met_course = match.group(1)
            met_requirements[course] = met_course
    
    # Filter out redundant requirements
    filtered_list = []
    for course in course_list:
        if course in met_requirements and met_requirements[course] in course_list:
            continue  # Skip redundant requirement
        filtered_list.append(course)
    
    return filtered_list

def process_degree_eval_file(file):
    mhtml_file = file
    
    # Step 1: Read and parse the MHTML file
    with open(mhtml_file, 'rb') as file:
        msg = message_from_binary_file(file)
        
    # Step 2: Find and decode the HTML part
    html_part = None

    for part in msg.walk():
        if part.get_content_type() == "text/html":
            html_part = part.get_payload(decode=True)
            break

    if html_part is None:
        raise Exception("No MHTML was found. You may have uploaded an empty file.")
        # return jsonify({"message": "There was no HTML found"}), 400


    # Decode HTML content 
    html_content = html_part.decode('utf-8')

    # Parse the HTML content
    soup = BeautifulSoup(html_content, "html.parser")
    requirement_tables = soup.findAll("tbody")

    all_requirements = []
    
    # Define the column names
    columns = ["met", "requirement", "term", "satisfied_by", "title", "attribute", "credits", "grade", "source"]

    for tbody in requirement_tables:
        # Parse the table and create a grid of cells
        grid = parse_requirement_table(tbody)

        # Convert grid rows into a list of dictionaries.
        # If a row has fewer than 9 columns (due to rowspan), we fill missing values from previous row if needed.
        parsed_data = []
        last_row = {}
        for row in grid:
            # Pad row if necessary
            if len(row) < len(columns):
                row += [""] * (len(columns) - len(row))
            # For the 'met' and 'requirement' columns, if empty, inherit from the last row.
            current = dict(zip(columns, row[:len(columns)]))
            if not current["met"]:
                current["met"] = last_row.get("met", "")
            if not current["requirement"]:
                current["requirement"] = last_row.get("requirement", "")
            parsed_data.append(current)
            last_row = current

        all_requirements.extend(parsed_data)
    
    all_requirements_df = pd.DataFrame(all_requirements, columns=columns)
    
    all_requirements_df = all_requirements_df[all_requirements_df["met"].isin(["Yes", "No"])]
    pattern = r'^\s*\d+(\.\d+)?\s*$'

    # # Filter out invalid rows
    all_requirements_df = all_requirements_df[~all_requirements_df["requirement"].str.match(pattern, na=False)]
    all_requirements_df = all_requirements_df.drop_duplicates()
    all_requirements_df = all_requirements_df.drop_duplicates(subset=["requirement", "title"])
    all_requirements_df = all_requirements_df[
        ~all_requirements_df["requirement"].str.strip().str.startswith(
            ("Message:", "Any additional", "*Reminder", "All Previously Unused Credits", "Upper division check")
        )
    ]
    all_requirements_df = all_requirements_df[
        ~all_requirements_df["requirement"].str.strip().str.contains(
           "Met with program requirements"
        )
    ]
    all_requirements_df["requirement"] = all_requirements_df["requirement"].str.replace('\u00a0', ' ', regex=False).replace(r"\/", "/")    
    all_requirements_df["satisfied_by"] = all_requirements_df["satisfied_by"].str.replace('\u00a0', ' ', regex=False).replace(r"\/", "/")   


    requirements_met = []
    requirements_not_met = []

    # Iterate through each row in the DataFrame
    for _, row in all_requirements_df.iterrows():
        if row['met'] == 'Yes' and len(row['title']) > 0:
            
            # Append an object with title, requirement, and grade for met requirements
            requirements_met.append({
                'title': clean_text(row['title']),
                'requirement': row['satisfied_by'],
                'grade': row['grade'],
                'attributes': row['attribute'].replace("KA", "")
            })
        elif row['met'] == 'No':
            # Append just the requirement string for requirements not met
            requirements_not_met.append(clean_text(row['requirement']))

    filtered_requirements_not_met = clean_duplicate_not_met_requirements(requirements_not_met)

    def deduplicate_by_requirement(course_list):
        seen = set()
        deduped = []
        for course in course_list:
            req = course['requirement']
            if req not in seen:
                deduped.append(course)
                seen.add(req)
        return deduped

    # usage
    cleaned_list = deduplicate_by_requirement(requirements_met)

    return {
        "requirements_satisfied":  cleaned_list,
        "requirements_not_satisfied": filtered_requirements_not_met   
    }
    




