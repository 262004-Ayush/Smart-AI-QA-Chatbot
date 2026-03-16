import streamlit as st
import requests
from bs4 import BeautifulSoup
import os
import re
import json

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

.white-text{
color:white;
font-weight:bold;
}

/* Orange open link button */
.orange-link-btn {
display: inline-block;
background-color: #fd7c2a;
color: white !important;
padding: 8px 16px;
border-radius: 6px;
font-size: 14px;
font-weight: normal;
text-decoration: none !important;
margin: 4px 0;
transition: background-color 0.2s ease;
}

.orange-link-btn:hover {
background-color: #e06010 !important;
color: white !important;
text-decoration: none !important;
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
# ORANGE LINK BUTTON HELPER
# -----------------------------

def open_link_button(url):
    st.markdown(
        f'<a href="{url}" target="_blank" class="orange-link-btn">🔗 Open Link</a>',
        unsafe_allow_html=True
    )

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


def stream_code_model(prompt):
    """Streaming response - word by word"""

    payload = {
        "model": "meta/llama-3.1-70b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 4000,
        "stream": True
    }

    r = requests.post(API_URL, headers=headers, json=payload, stream=True)

    for line in r.iter_lines():
        if line:
            line = line.decode("utf-8")
            if line.startswith("data: "):
                line = line[6:]
                if line.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(line)
                    delta = chunk["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield delta
                except:
                    continue


def ask_code_model(prompt):
    """Non-streaming - full response"""

    payload = {
        "model": "meta/llama-3.1-70b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 4000
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


def extract_page_info(html):

    soup = BeautifulSoup(html, "html.parser")

    inputs = []
    for tag in soup.find_all(["input", "textarea", "select"]):
        name = tag.get("name") or tag.get("id") or "N/A"
        typ = tag.get("type") or tag.name
        inputs.append({
            "Field": name,
            "Type": typ
        })

    buttons = []
    for tag in soup.find_all(["button", "input"]):
        if tag.get("type") in ["submit", "button", "reset"]:
            label = tag.get_text(strip=True) or tag.get("value") or tag.get("name") or "N/A"
            buttons.append({
                "Button": label,
                "Type": tag.get("type") or "button"
            })

    title = soup.title.string if soup.title else "N/A"

    headings = []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = tag.get_text(strip=True)
        if text:
            headings.append(text)

    links_count = len(soup.find_all("a", href=True))
    forms_count = len(soup.find_all("form"))

    page_summary = {
        "title": title,
        "headings": headings[:10],
        "forms_count": forms_count,
        "links_count": links_count
    }

    return inputs, buttons, page_summary

# -----------------------------
# TEST CASE GENERATOR - STREAMING
# -----------------------------

def generate_test_cases_stream(inputs, buttons, page_summary):

    prompt = f"""
You are a senior QA engineer with 10+ years of experience.

Website Page Analysis:
- Page Title: {page_summary['title']}
- Page Headings: {page_summary['headings']}
- Total Forms: {page_summary['forms_count']}
- Total Links: {page_summary['links_count']}

Input Fields Detected:
{inputs}

Buttons Detected:
{buttons}

Generate comprehensive manual test cases covering ALL sections below.
For EVERY test case provide Test Case ID, Title, Steps, Example Input Data, Expected Result.
Minimum 3 test cases per section. Complete all 7 sections fully without stopping.

## Positive Test Cases
## Negative Test Cases
## Edge Cases
## Boundary Value Analysis
## Equivalence Partitioning
## UI & Functional Test Cases
## Security Test Cases

Include exact example input values for every test case.
"""

    return stream_code_model(prompt)

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
            open_link_button(msg["url"])

        if msg.get("page_summary"):
            ps = msg["page_summary"]
            st.markdown(f"""
**🌐 Page Title:** {ps['title']}
**📋 Forms Found:** {ps['forms_count']}
**🔗 Links Found:** {ps['links_count']}
**📌 Headings:** {', '.join(ps['headings'][:5]) if ps['headings'] else 'N/A'}
""")

        if msg.get("table"):
            st.markdown("#### 📥 Detected Input Fields")
            st.table(msg["table"])

        if msg.get("buttons"):
            st.markdown("#### 🔘 Detected Buttons")
            st.table(msg["buttons"])

        if msg.get("test_cases"):

            st.markdown("### 🧪 AI Generated Test Cases")
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

                inputs, buttons, page_summary = extract_page_info(html)

                open_link_button(user_input)

                st.markdown(f"""
**🌐 Page Title:** {page_summary['title']}
**📋 Forms Found:** {page_summary['forms_count']}
**🔗 Links Found:** {page_summary['links_count']}
**📌 Headings:** {', '.join(page_summary['headings'][:5]) if page_summary['headings'] else 'N/A'}
""")

                st.markdown("#### 📥 Detected Input Fields")
                st.table(inputs)

                if buttons:
                    st.markdown("#### 🔘 Detected Buttons")
                    st.table(buttons)

                st.markdown("### 🧪 Generated Test Cases")

                # Streaming output - word by word
                test_cases = st.write_stream(
                    generate_test_cases_stream(inputs, buttons, page_summary)
                )

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "✅ Page Analysis Complete",
                    "table": inputs,
                    "buttons": buttons,
                    "test_cases": test_cases,
                    "page_summary": page_summary,
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
