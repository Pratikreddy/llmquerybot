import streamlit as st
import sqlite3
import pandas as pd
import openai
import requests
import base64

# Load the OpenAI API key from Streamlit secrets
api_key = st.secrets["openai"]["api_key"]
openai.api_key = api_key

# Define the data
data = {
    "HS Code": [84137099, 40101900, 73181510, 73181590, 73182100, 73182100, 73194020, 40101200, 73079910, 40101200],
    "Product Name": [
        "Centrifugal Fire Pump Horizontal Split Case", 
        "Conveyor Belt, Fabric Belt; 2400 MM X EP 200 X 4 PLY X 10 MM",
        "M12 x 120mm Lg Hex Hd HT Bolt BZP",
        "Bolt (M27X260X30)",
        "SEW - Retaining Ring DIN472 100X3-FS",
        "Crusher SP; Oil Retaining Ring",
        "Clamp, C: 4in Forged Ultra Strong Drop Steel Clamp Bar Type",
        "Conveyor Belt Type: 2200 EP 630/4 6+3 Y ME Belt Conveyor Belt Conveyor",
        "Lubrication Fitting Assortment: Automotive Hydraulic Grease Nipple",
        "Stud, Recessed: Threaded Both End"
    ],
    "Definition": [
        "Fire pump using centrifugal principle to pump water, with horizontally split casing design",
        "Fabric conveyor belt with specifications: Width: 2400mm, Thickness: 10mm, Fabric Layer Thickness: 4mm, Number of Fabric Layers: 4, Tensile Strength: EP 200, Grade: M",
        "Large hex head high tensile strength bolt with bright zinc plating, commonly used in various industrial and construction applications",
        "High-strength hex bolt with metric thread diameter of 27mm, length of 260mm, and head height of 30mm. Commonly used in industrial applications requiring high strength and reliability.",
        "Retaining ring used to hold components in place, outer diameter of 100mm and thickness of 3mm",
        "Oil retaining ring used in coal crusher scoop coupling, with an outer diameter of 100mm and thickness of 3mm to prevent oil leakage",
        "Strong forged steel C clamp bar type with 4 inch length, jaw opening up to 100mm, and throat depth of 60mm",
        "Conveyor belt type EP630/4 with width of 2200mm, cover thickness of 6+3mm, DIN Y grade, and polyester material, capable of withstanding loads up to 630 kg/m",
        "Lubrication fitting assortment used for automotive components, consisting of 12 different grease nipple sizes including SAE, ANF, BSP, Metric, and BSF",
        "Special long threaded stud used on electromagnetic vibratory model FV890 with component code EQ 2482, with a length of 900mm and includes 4 M42 nuts"
    ],
    "Material": [
        "Cast Iron / Steel", "Polyester (EP)", "Bright Zinc Plated", "Bright Zinc Plated", "Stainless Steel", 
        "Stainless Steel", "Stainless Steel", "Polyester", "-", "Polyester"
    ],
    "Specifications": [
        "-", 
        "Width: 2400mm, Thickness: 10mm, Fabric Layer Thickness: 4mm, Number of Fabric Layers: 4", 
        "Diameter: M12, Length: 120mm, Large Hex Head", 
        "Diameter: M27, Length: 260mm, Head Height: 30mm", 
        "Outer Diameter: 100mm, Thickness: 3mm",
        "Outer Diameter: 100mm, Thickness: 3mm",
        "Jaw Opening: 100mm, Throat Depth: 60mm",
        "Width: 2200mm, Cover Thickness: 6+3mm, DIN Y Grade",
        "12 Sizes: SAE, ANF, BSP, Metric, BSF",
        "Length: 900mm, Includes 4 M42 Nuts"
    ]
}

# Convert data to DataFrame
df = pd.DataFrame(data)

# Connect to SQLite database (or create it)
conn = sqlite3.connect('hs_codes.db')

# Create table
conn.execute('''
CREATE TABLE IF NOT EXISTS HS_CODES (
    HS_Code INTEGER,
    Product_Name TEXT,
    Definition TEXT,
    Material TEXT,
    Specifications TEXT
)
''')

# Insert data into table
df.to_sql('HS_CODES', conn, if_exists='replace', index=False)

# Commit and close connection
conn.commit()
conn.close()

# Set up the page
st.set_page_config(page_title="HS Code Lookup System", layout="wide")

# Initialize chat history as a session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Title and description
st.title("HS Code Lookup System")
st.write("Automated and accurate HS Code information at your fingertips.")

# Display chat history
for message in st.session_state.chat_history:
    if message["role"] == "user":
        st.markdown(f"<div style='border: 2px solid blue; padding: 10px; margin: 10px 0; border-radius: 8px; width: 80%; float: right; clear: both;'>{message['content']}</div>", unsafe_allow_html=True)
    elif message["role"] == "assistant":
        st.markdown(f"<div style='border: 2px solid green; padding: 10px; margin: 10px 0; border-radius: 8px; width: 80%; float: left; clear: both;'>{message['content']}</div>", unsafe_allow_html=True)

# Function to read image bytes and encode them in base64
def read_image_base64(image_path):
    with open(image_path, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Function to execute SQL query
def execute_sql_query(query, db='hs_codes.db'):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return rows

# Function to process prompt with OpenAI API
def process_prompt_openai(system_prompt, chat_history):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    messages = [{"role": "system", "content": system_prompt}]
    for entry in chat_history:
        messages.append({"role": entry["role"], "content": entry["content"]})

    payload = {
        "model": "gpt-4",
        "messages": messages,
        "max_tokens": 3000
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return response.json()

# Function to handle message sending and processing
def send_message():
    user_prompt = st.session_state.input_buffer
    imgpaths = [f"temp_image_{i}.png" for i, _ in enumerate(uploaded_files)] if uploaded_files else []

    if not user_prompt and not uploaded_files:
        st.write("Please provide a text input, an image, or both.")
    else:
        if uploaded_files:
            # Save the uploaded files temporarily
            for i, uploaded_file in enumerate(uploaded_files):
                with open(imgpaths[i], "wb") as f:
                    f.write(uploaded_file.getbuffer())

        # Append structured messages to chat history
        if user_prompt:
            st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        
        # Determine if the user prompt is a query or a regular message
        if any(keyword in user_prompt.lower() for keyword in ["how", "what", "tell", "show", "get", "find"]):
            response = process_prompt_openai(initial_system_message, st.session_state.chat_history)
            command = response['choices'][0]['message']['content'].strip()

            # Display the query for transparency
            st.write(f"Executing query: {command}")

            query_result = execute_sql_query(command)

            if query_result:
                st.session_state.chat_history.append({"role": "assistant", "content": str(query_result)})
            else:
                st.session_state.chat_history.append({"role": "assistant", "content": "I encountered an error while processing your request."})
        else:
            st.session_state.chat_history.append({"role": "assistant", "content": "Thank you for your message!"})
        
        st.session_state.input_buffer = ""

    st.experimental_rerun()  # Trigger rerun to clear input and update chat history

# Input for chat messages
user_input = st.text_input("Type your message here:", key="input_buffer")

# File upload for up to 3 images
uploaded_files = st.file_uploader("Upload up to 3 image files", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

# Display thumbnails of uploaded images
if uploaded_files:
    for uploaded_file in uploaded_files:
        st.image(uploaded_file, width=100)

# Send button
st.button("Send", on_click=send_message)

# Display data from SQLite
def load_data():
    conn = sqlite3.connect('hs_codes.db')
    df = pd.read_sql_query("SELECT * FROM HS_CODES", conn)
    conn.close()
    return df

st.write("## Product Data")
st.dataframe(load_data())
