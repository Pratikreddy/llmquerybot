import streamlit as st
import base64
import openai
import requests
import json
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Set up the page
st.set_page_config(page_title="HS Code Lookup System", layout="wide")

# Load the OpenAI API key from Streamlit secrets
api_key = st.secrets["openai"]["api_key"]
openai.api_key = api_key

# Google Sheets URL and worksheet ID from secrets
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1wgliY7XyZF-p4FUa1MiELUlQ3v1Tg6KDZzWuyW8AMo4/edit?gid=835818411"
worksheet_id = "835818411"

# Set up connection to Google Sheets
conn = st.experimental_connection("gsheets", type=GSheetsConnection)

@st.cache_data
def get_data_from_gsheet(url, worksheet_id):
    try:
        st.write(f"Reading from Google Sheets URL: {url} and Worksheet ID: {worksheet_id}")
        data = conn.read(spreadsheet=url, usecols=list(range(5)), worksheet=worksheet_id)
        return data
    except Exception as e:
        st.error(f"Error reading from Google Sheets: {e}")
        return pd.DataFrame()  # Return an empty DataFrame in case of error

data = get_data_from_gsheet(spreadsheet_url, worksheet_id)

# Construct the initial system message from the Google Sheets data
initial_system_message = """
You are a virtual assistant providing HS Code information. Be professional and informative.
Do not make up any details you do not know. Always sound smart and refer to yourself as Jarvis.

Only output the information given below and nothing else of your own knowledge. This is the only truth. Translate everything to English to the best of your ability.
and only output when prompted towards something don't dump all the codes into the response.

We help you find the right HS Code for your products quickly and accurately. Save time and avoid customs issues with our automated HS Code lookup tool.

Product List:
"""

if not data.empty:
    for index, row in data.iterrows():
        initial_system_message += f"""
{row['Product Name']}
* Definisi: {row['Definition']}
* Bahan: {row['Material']}
* HS Code: {row['HS Code']}
* Specifications: {row['Specifications']}
"""

initial_system_message += """
You are an expert in converting English questions to Pandas DataFrame queries! The DataFrame has the following columns: 'Product Name', 'Definition', 'Material', 'HS Code', 'Specifications'.

For example:
Example 1 - How many entries of records are present? 
The command will be something like this: data.shape[0]

Example 2 - Tell me all the products made of steel? 
The command will be something like this: data[data['Material'] == 'steel']

Generate only the command and not the full code. Do not use backticks.
"""

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

# Function to execute DataFrame queries
def execute_dataframe_query(data, query):
    try:
        result = eval(query)
        return result
    except Exception as e:
        return f"Error executing query: {e}"

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
        "model": "gpt-4o",
        "messages": messages,
        "max_tokens": 3000
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return response.json()

# Helper function to read image bytes and encode them in base64
def read_image_base64(image_path):
    with open(image_path, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

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

            query_result = execute_dataframe_query(data, command)

            if "Error executing query" in query_result:
                st.session_state.chat_history.append({"role": "assistant", "content": "I encountered an error while processing your request."})
            else:
                st.session_state.chat_history.append({"role": "assistant", "content": str(query_result)})
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

# Display data from Google Sheets
st.write("## Product Data")
st.dataframe(data)
