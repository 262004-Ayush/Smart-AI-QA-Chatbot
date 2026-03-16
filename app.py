import streamlit as st
import requests
from bs4 import BeautifulSoup
import os
import re

# -----------------------------
# NVIDIA API CONFIG
# -----------------------------

API_KEY = os.getenv("NVIDIA_API_KEY")
API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# -----------------------------
# PAGE CONFIG
# -----------------------------

st.set_page_config(page_title="AI Smart QA Chatbot", layout="wide")

# -----------------------------
# CUSTOM CSS
# -----------------------------

st.markdown("""
<style>

/* Default buttons green */
div.stButton > button {
background-color:#28a745;
color:white;
border:none;
padding:10px 16px;
border-radius:6px;
font-weight:600;
}

div.stButton > button:hover {
background-color:#1e7e34;
color:white;
}

/* Generate Selenium button BLUE */
button[kind="secondary"]{
background-color:#007bff !important;
color:white !important;
}

button[kind="secondary"]:hover{
background-color:#0056b3 !important;
}

/* Sidebar clear chat BLUE */
section[data-testid="stSidebar"] button{
background-color:#007bff !important;
color:white !important;
}

/* Open website button */
a.stLinkButton button {
background-color:#28a745;
color:white;
border:none;
padding:10px 16px;
border-radius:6px;
font-weight:600;
}

.white-text{
color:white;
font-weight:bold;
}

</style>
""", unsafe_allow_html=True)

# -----------------------------
# TITLE
# -----------------------------

st.title("🤖 AI Smart QA Chatbot")

st.markdown(
"Ask testing questions or paste a website URL to generate test cases and automation script."
)

# -----------------------------
# SESSION STATE
# -----------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

# -----------------------------
# SIDEBAR HISTORY
# -----------------------------

st.sidebar.title("Chat History")

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.sidebar.write(msg["content"])

if st.sidebar.button("Clear Chat"):
    st.session_state.messages = []
    st.rerun()

# -----------------------------
# AI MODEL FUNCTIONS
# -----------------------------

def ask_qa_model(prompt):

    payload = {
        "model": "meta/llama-3.1-8b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 800
    }

    r = requests.post(API_URL, headers=headers, json=payload)

    return r.json()["choices"][0]["message"]["content"]


def ask_code_model(prompt):

    payload = {
        "model": "meta/llama-3.1-70b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 1200
    }

    r = requests.post(API_URL, headers=headers, json=payload)

    return r.json()["choices"][0]["message"]["content"]

# -----------------------------
# WEBSITE SCRAPER
# -----------------------------

def get_html(url):

    try:
        headers_req = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers_req, timeout=10)
        return r.text
    except:
        return None


def extract_inputs(html):

    soup = BeautifulSoup(html, "html.parser")

    inputs = []

    for tag in soup.find_all(["input", "textarea", "select"]):

        name = tag.get("name") or tag.get("id") or "N/A"
        typ = tag.get("type") or tag.name

        inputs.append({
            "Field": name,
            "Type": typ
        })

    return inputs

# -----------------------------
# TEST CASE GENERATOR
# -----------------------------

def generate_test_cases(inputs):

    prompt = f"""
You are a senior QA engineer.

Website form fields:

{inputs}

Generate:
Positive test cases
Negative test cases
Edge cases
Boundary value analysis
Equivalence partitioning
"""

    return ask_qa_model(prompt)

# -----------------------------
# SELENIUM SCRIPT GENERATOR
# -----------------------------

def generate_selenium_script(url, inputs):

    prompt = f"""
Generate a complete Java Selenium end to end automation script.

Website URL:
{url}

Input fields:
{inputs}

Rules:

Return only Java code.
Do not include comments.
Do not include prerequisites.

Structure:

public class AutomationTest

public static void main(String[] args)

Inside main method first line must be:

WebDriver driver = new ChromeDriver();

Then open website, fill fields and submit form.
"""

    return ask_code_model(prompt)

# -----------------------------
# DISPLAY CHAT
# -----------------------------

for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):

        st.markdown(msg["content"])

        if msg.get("url"):
            st.link_button("Open Website", msg["url"])

        if msg.get("table"):
            st.table(msg["table"])

        if msg.get("test_cases"):

            st.markdown("### AI Generated Test Cases")
            st.markdown(msg["test_cases"])

            if st.button("Generate JAVA Selenium Automation Script", key=msg["url"], type="secondary"):

                code = generate_selenium_script(msg["url"], msg["table"])

                st.markdown("### This Automation Script Performs End-to-End Testing")

                st.code(code, language="java")

                st.markdown(
                    '<p class="white-text">Change waits, input, buttons, value according to your requirement</p>',
                    unsafe_allow_html=True
                )

# -----------------------------
# USER INPUT
# -----------------------------

if user_input := st.chat_input("Ask testing question or paste website URL"):

    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):

        if re.match(r'https?://', user_input):

            html = get_html(user_input)

            if html:

                inputs = extract_inputs(html)

                st.link_button("Open Website", user_input)

                st.table(inputs)

                test_cases = generate_test_cases(inputs)

                st.markdown("### Generated Test Cases")
                st.markdown(test_cases)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Detected Input Fields",
                    "table": inputs,
                    "test_cases": test_cases,
                    "url": user_input
                })

            else:
                st.error("Unable to fetch website")

        else:

            prompt = f"""
You are a software testing expert.

Answer clearly:

{user_input}
"""

            answer = ask_qa_model(prompt)

            st.markdown(answer)

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer
            })

    st.rerun()
