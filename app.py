import streamlit as st
from google import genai
from PyPDF2 import PdfReader
from docx import Document
import re


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AI Document Analyzer",
    page_icon="📄",
    layout="wide"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>

.main-title {
    font-size: 42px;
    font-weight: bold;
    text-align: center;
    margin-bottom: 5px;
}

.subtitle {
    text-align: center;
    color: #666;
    font-size: 18px;
    margin-bottom: 30px;
}

.info-card {
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #ddd;
    margin-bottom: 15px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# API CONFIGURATION
# ============================================================

try:
    API_KEY = st.secrets["API_KEY"]
except Exception:
    API_KEY = None


# ============================================================
# GEMINI CLIENT
# ============================================================

def get_client():

    if not API_KEY:
        return None

    try:
        return genai.Client(api_key=API_KEY)
    except Exception:
        return None


# ============================================================
# AI FUNCTION
# ============================================================

def ask_ai(prompt):

    client = get_client()

    if client is None:
        return (
            "❌ Gemini API key is missing or could not be loaded.\n\n"
            "Please add API_KEY to Streamlit Secrets."
        )

    try:

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )

        return response.text

    except Exception as e:

        error_message = str(e)

        if "429" in error_message:
            return (
                "❌ API quota/rate limit reached.\n\n"
                "Please wait and try again later, or check your "
                "Gemini API usage and limits."
            )

        if "401" in error_message or "403" in error_message:
            return (
                "❌ API authentication failed.\n\n"
                "Please check your Gemini API key."
            )

        return f"❌ AI request failed:\n\n{error_message}"


# ============================================================
# PDF TEXT EXTRACTION
# ============================================================

def extract_pdf_text(uploaded_file):

    try:

        reader = PdfReader(uploaded_file)

        text = ""

        for page in reader.pages:

            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

        return text

    except Exception as e:

        raise Exception(f"Could not read PDF: {e}")


# ============================================================
# DOCX TEXT EXTRACTION
# ============================================================

def extract_docx_text(uploaded_file):

    try:

        document = Document(uploaded_file)

        text = ""

        for paragraph in document.paragraphs:

            if paragraph.text.strip():
                text += paragraph.text + "\n"

        return text

    except Exception as e:

        raise Exception(f"Could not read DOCX file: {e}")


# ============================================================
# TXT TEXT EXTRACTION
# ============================================================

def extract_txt_text(uploaded_file):

    try:

        return uploaded_file.read().decode("utf-8")

    except Exception as e:

        raise Exception(f"Could not read TXT file: {e}")


# ============================================================
# GENERAL DOCUMENT EXTRACTION
# ============================================================

def extract_document_text(uploaded_file):

    file_name = uploaded_file.name.lower()

    if file_name.endswith(".pdf"):

        return extract_pdf_text(uploaded_file)

    elif file_name.endswith(".docx"):

        return extract_docx_text(uploaded_file)

    elif file_name.endswith(".txt"):

        return extract_txt_text(uploaded_file)

    else:

        raise Exception("Unsupported file type.")


# ============================================================
# TEXT STATISTICS
# ============================================================

def calculate_statistics(text):

    words = text.split()

    characters = len(text)

    paragraphs = [
        paragraph
        for paragraph in text.split("\n")
        if paragraph.strip()
    ]

    word_count = len(words)

    reading_time = max(1, round(word_count / 200))

    return {
        "words": word_count,
        "characters": characters,
        "paragraphs": len(paragraphs),
        "reading_time": reading_time
    }


# ============================================================
# LIMIT TEXT SENT TO AI
# ============================================================

def prepare_document_for_ai(text):

    # Prevent extremely large documents from creating
    # unnecessarily huge API requests.

    max_characters = 60000

    if len(text) <= max_characters:

        return text

    return (
        text[:max_characters]
        + "\n\n[Document truncated for AI analysis]"
    )


# ============================================================
# SUMMARY FUNCTION
# ============================================================

def generate_summary(document_text, response_length, ai_mode):

    document_text = prepare_document_for_ai(document_text)

    prompt = f"""
You are an expert document analysis assistant.

Analyze the document below.

AI Mode:
{ai_mode}

Response Length:
{response_length}

DOCUMENT:
----------------
{document_text}
----------------

Create a clear summary using exactly these sections:

# Executive Summary

Explain the document in simple and clear language.

# Key Points

List the most important points.

# Main Topics

Identify the major topics discussed.

# Important Conclusions

Explain the important conclusions or findings.

Important rules:

- Use ONLY information found in the document.
- Do not invent facts.
- If something is not available in the document, say so.
- Keep the response organized and easy to read.
"""

    return ask_ai(prompt)


# ============================================================
# ASK DOCUMENT FUNCTION
# ============================================================

def ask_document(document_text, question, explanation_level, ai_mode):

    document_text = prepare_document_for_ai(document_text)

    prompt = f"""
You are an AI assistant that answers questions about a document.

AI Mode:
{ai_mode}

Explanation Level:
{explanation_level}

DOCUMENT:
----------------
{document_text}
----------------

USER QUESTION:
{question}

Instructions:

1. Answer using the document as the primary source.
2. Do not invent information.
3. If the answer cannot be found in the document, say:

"I could not find this information in the uploaded document."

4. Explain the answer clearly.
5. Use examples only when they are supported by the document.
"""

    return ask_ai(prompt)


# ============================================================
# SIMPLE EXPLANATION FUNCTION
# ============================================================

def explain_simply(document_text, topic, explanation_level):

    document_text = prepare_document_for_ai(document_text)

    prompt = f"""
You are a friendly teacher.

Use the uploaded document to explain the requested topic.

DOCUMENT:
----------------
{document_text}
----------------

TOPIC OR TEXT TO EXPLAIN:
{topic}

Student Level:
{explanation_level}

Explain using:

1. Simple definition
2. Step-by-step explanation
3. Important points
4. Simple example if appropriate
5. Short recap

Do not add information that is not supported by the document.
"""

    return ask_ai(prompt)


# ============================================================
# IMPORTANT INFORMATION FUNCTION
# ============================================================

def extract_information(document_text):

    document_text = prepare_document_for_ai(document_text)

    prompt = f"""
Analyze this document and extract important information.

DOCUMENT:
----------------
{document_text}
----------------

Organize the answer using these sections:

# Important Names

# Important Dates

# Important Numbers

# Definitions

# Important Terms

# Main Arguments

# Important Facts

# Conclusions

Only include information actually found in the document.
Do not invent anything.
"""

    return ask_ai(prompt)


# ============================================================
# STUDY NOTES FUNCTION
# ============================================================

def generate_notes(document_text, explanation_level):

    document_text = prepare_document_for_ai(document_text)

    prompt = f"""
You are a university teacher creating study notes.

DOCUMENT:
----------------
{document_text}
----------------

Student Level:
{explanation_level}

Convert the document into student-friendly study notes.

Use this structure:

# Topic

## Definition

## Explanation

## Key Points

- Point
- Point
- Point

## Examples

## Important Terms

## Exam Revision Points

Rules:

- Use simple language.
- Keep important information.
- Do not invent information.
- Make the notes useful for exam preparation.
"""

    return ask_ai(prompt)


# ============================================================
# QUIZ FUNCTION
# ============================================================

def generate_quiz(document_text, number_of_questions, question_type):

    document_text = prepare_document_for_ai(document_text)

    prompt = f"""
You are a university teacher creating a quiz.

DOCUMENT:
----------------
{document_text}
----------------

Create {number_of_questions} questions.

Question Type:
{question_type}

All questions must be based ONLY on the document.

For Multiple Choice Questions use:

Question:
A.
B.
C.
D.

Correct Answer:
Explanation:

For True/False use:

Statement:
Answer:
Explanation:

For Short Answer use:

Question:
Answer:

Do not use information outside the document.
"""

    return ask_ai(prompt)


# ============================================================
# FLASHCARD FUNCTION
# ============================================================

def generate_flashcards(document_text):

    document_text = prepare_document_for_ai(document_text)

    prompt = f"""
Create useful study flashcards from this document.

DOCUMENT:
----------------
{document_text}
----------------

Create important flashcards.

Use this format:

## Flashcard 1

Front:
Question or important term

Back:
Answer or definition

## Flashcard 2

Front:
Question or important term

Back:
Answer or definition

Create flashcards from the most important concepts.

Only use information from the document.
"""

    return ask_ai(prompt)


# ============================================================
# DOCUMENT SEARCH
# ============================================================

def search_document(document_text, keyword):

    keyword = keyword.strip()

    if not keyword:
        return []

    text_lower = document_text.lower()

    keyword_lower = keyword.lower()

    results = []

    start = 0

    while True:

        position = text_lower.find(keyword_lower, start)

        if position == -1:
            break

        context_start = max(0, position - 150)

        context_end = min(
            len(document_text),
            position + len(keyword) + 150
        )

        context = document_text[
            context_start:context_end
        ]

        results.append(context)

        start = position + len(keyword)

    return results


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">📄 AI Document Analyzer</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Upload a document, analyze it, ask questions, create study notes, '
    'generate quizzes and much more with AI.'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# SESSION STATE
# ============================================================

if "document_text" not in st.session_state:
    st.session_state.document_text = ""

if "file_name" not in st.session_state:
    st.session_state.file_name = ""


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("⚙️ AI Settings")

response_length = st.sidebar.selectbox(
    "📝 Response Length",
    [
        "Short",
        "Medium",
        "Detailed"
    ]
)

explanation_level = st.sidebar.selectbox(
    "🎓 Explanation Level",
    [
        "Beginner",
        "Intermediate",
        "Advanced"
    ]
)

ai_mode = st.sidebar.selectbox(
    "🤖 AI Mode",
    [
        "Summary",
        "Study",
        "Research",
        "General"
    ]
)

st.sidebar.markdown("---")

st.sidebar.info(
    "Upload one document and use the tools in the tabs "
    "to analyze it."
)


# ============================================================
# DOCUMENT UPLOAD
# ============================================================

st.header("📄 Upload Document")

uploaded_file = st.file_uploader(
    "Choose a PDF, DOCX or TXT file",
    type=["pdf", "docx", "txt"]
)


# ============================================================
# PROCESS DOCUMENT
# ============================================================

if uploaded_file is not None:

    # Process only when a new file is uploaded
    if uploaded_file.name != st.session_state.file_name:

        try:

            with st.spinner("📖 Reading your document..."):

                extracted_text = extract_document_text(
                    uploaded_file
                )

            if not extracted_text.strip():

                st.error(
                    "❌ The document appears to be empty "
                    "or no readable text was found."
                )

                st.session_state.document_text = ""
                st.session_state.file_name = ""

            else:

                st.session_state.document_text = extracted_text
                st.session_state.file_name = uploaded_file.name

                st.success(
                    f"✅ {uploaded_file.name} loaded successfully!"
                )

        except Exception as e:

            st.error(f"❌ {e}")

            st.session_state.document_text = ""
            st.session_state.file_name = ""


# ============================================================
# DOCUMENT INFORMATION
# ============================================================

if st.session_state.document_text:

    document_text = st.session_state.document_text

    statistics = calculate_statistics(document_text)

    st.subheader("📊 Document Statistics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "📄 File",
            st.session_state.file_name
        )

    with col2:
        st.metric(
            "📝 Words",
            statistics["words"]
        )

    with col3:
        st.metric(
            "🔤 Characters",
            statistics["characters"]
        )

    with col4:
        st.metric(
            "⏱️ Reading Time",
            f"{statistics['reading_time']} min"
        )

    st.write(
        f"**Paragraphs:** {statistics['paragraphs']}"
    )

    with st.expander("👀 Preview Extracted Text"):

        st.text_area(
            "Document Text",
            document_text[:10000],
            height=300,
            disabled=True
        )

# ============================================================
# CURRENT DOCUMENT TEXT
# ============================================================

document_text = st.session_state.document_text


# ============================================================
# NAVIGATION TABS
# ============================================================

tabs = st.tabs([
    "📊 Dashboard",
    "📝 Summary",
    "❓ Ask Document",
    "🎓 Study Notes",
    "🧠 Quiz",
    "🔑 Important Info",
    "📖 Flashcards",
    "🔍 Search",
    "💡 Explain Simply"
])


# ============================================================
# DASHBOARD
# ============================================================

with tabs[0]:

    st.header("📊 Dashboard")

    if not document_text:

        st.info(
            "👆 Upload a document above to start analyzing it."
        )

    else:

        st.success(
            "Your document is ready for AI analysis!"
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            st.info(
                "📝\n\n"
                "Generate a complete AI summary."
            )

        with col2:

            st.info(
                "❓\n\n"
                "Ask questions about your document."
            )

        with col3:

            st.info(
                "🎓\n\n"
                "Create study notes and quizzes."
            )

        st.markdown("---")

        st.write(
            "### Available Tools"
        )

        st.write(
            """
            - 📝 AI Summary
            - ❓ Document Q&A
            - 🎓 Study Notes
            - 🧠 Quiz Generator
            - 🔑 Important Information
            - 📖 Flashcards
            - 🔍 Document Search
            - 💡 Simple Explanation
            """
        )


# ============================================================
# SUMMARY
# ============================================================

with tabs[1]:

    st.header("📝 AI Document Summary")

    if not document_text:

        st.warning("Please upload a document first.")

    else:

        if st.button(
            "✨ Generate Summary",
            use_container_width=True
        ):

            with st.spinner(
                "🤖 AI is analyzing your document..."
            ):

                result = generate_summary(
                    document_text,
                    response_length,
                    ai_mode
                )

            st.markdown(result)


# ============================================================
# ASK DOCUMENT
# ============================================================

with tabs[2]:

    st.header("❓ Ask AI About This Document")

    if not document_text:

        st.warning("Please upload a document first.")

    else:

        question = st.text_area(
            "Ask your question",
            placeholder=(
                "Example: What are the main findings "
                "of this document?"
            ),
            height=120
        )

        if st.button(
            "🤖 Ask AI",
            use_container_width=True
        ):

            if not question.strip():

                st.warning(
                    "Please enter a question."
                )

            else:

                with st.spinner(
                    "🔎 Searching the document and generating an answer..."
                ):

                    result = ask_document(
                        document_text,
                        question,
                        explanation_level,
                        ai_mode
                    )

                st.markdown(result)


# ============================================================
# STUDY NOTES
# ============================================================

with tabs[3]:

    st.header("🎓 Study Notes Generator")

    if not document_text:

        st.warning("Please upload a document first.")

    else:

        if st.button(
            "📚 Generate Study Notes",
            use_container_width=True
        ):

            with st.spinner(
                "📚 Creating study notes..."
            ):

                result = generate_notes(
                    document_text,
                    explanation_level
                )

            st.markdown(result)


# ============================================================
# QUIZ
# ============================================================

with tabs[4]:

    st.header("🧠 Quiz Generator")

    if not document_text:

        st.warning("Please upload a document first.")

    else:

        col1, col2 = st.columns(2)

        with col1:

            number_of_questions = st.selectbox(
                "Number of Questions",
                [5, 10, 15]
            )

        with col2:

            question_type = st.selectbox(
                "Question Type",
                [
                    "Multiple Choice Questions",
                    "True / False",
                    "Short Answer"
                ]
            )

        if st.button(
            "🧠 Generate Quiz",
            use_container_width=True
        ):

            with st.spinner(
                "🧠 Creating your quiz..."
            ):

                result = generate_quiz(
                    document_text,
                    number_of_questions,
                    question_type
                )

            st.markdown(result)


# ============================================================
# IMPORTANT INFORMATION
# ============================================================

with tabs[5]:

    st.header("🔑 Important Information Extractor")

    if not document_text:

        st.warning("Please upload a document first.")

    else:

        if st.button(
            "🔑 Extract Important Information",
            use_container_width=True
        ):

            with st.spinner(
                "🔎 Extracting important information..."
            ):

                result = extract_information(
                    document_text
                )

            st.markdown(result)


# ============================================================
# FLASHCARDS
# ============================================================

with tabs[6]:

    st.header("📖 Flashcard Generator")

    if not document_text:

        st.warning("Please upload a document first.")

    else:

        if st.button(
            "📖 Generate Flashcards",
            use_container_width=True
        ):

            with st.spinner(
                "📖 Creating flashcards..."
            ):

                result = generate_flashcards(
                    document_text
                )

            st.markdown(result)


# ============================================================
# SEARCH
# ============================================================

with tabs[7]:

    st.header("🔍 Search Document")

    if not document_text:

        st.warning("Please upload a document first.")

    else:

        keyword = st.text_input(
            "Enter a keyword or phrase",
            placeholder="Example: Artificial Intelligence"
        )

        if keyword:

            results = search_document(
                document_text,
                keyword
            )

            st.write(
                f"### 🔎 Found {len(results)} match(es)"
            )

            if results:

                for index, result in enumerate(
                    results,
                    start=1
                ):

                    with st.expander(
                        f"Match {index}"
                    ):

                        st.write(result)

            else:

                st.info(
                    "No matches found in the document."
                )


# ============================================================
# EXPLAIN SIMPLY
# ============================================================

with tabs[8]:

    st.header("💡 Explain in Simple Words")

    if not document_text:

        st.warning("Please upload a document first.")

    else:

        topic = st.text_area(
            "Enter a topic, paragraph or concept",
            placeholder=(
                "Example: Explain the concept of "
                "machine learning from this document."
            ),
            height=150
        )

        if st.button(
            "💡 Explain Simply",
            use_container_width=True
        ):

            if not topic.strip():

                st.warning(
                    "Please enter something to explain."
                )

            else:

                with st.spinner(
                    "👨‍🏫 Preparing a simple explanation..."
                ):

                    result = explain_simply(
                        document_text,
                        topic,
                        explanation_level
                    )

                st.markdown(result)


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "📄 AI Document Analyzer | "
    "Built with Python + Streamlit + Google Gemini"
)
