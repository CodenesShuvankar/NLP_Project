import os
import tempfile
import fitz  # PyMuPDF
import docx
import subprocess
import streamlit as st
import spacy
from datetime import datetime
import google.generativeai as genai
from PIL import Image


def ocr_image(image_path):
    try:
        img = Image.open(image_path)
        prompt_text = "Extract Text from image"
        response = st.session_state.gemini_model.generate_content([prompt_text, img])
        return response.text
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return None


def pdf_to_text(file_path):
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text


def docx_to_text(file_path):
    doc = docx.Document(file_path)
    text = '\n'.join([para.text for para in doc.paragraphs])
    return text


def convert_doc_to_docx(doc_path):
    subprocess.run(['libreoffice', '--headless', '--convert-to', 'docx', doc_path])


def doc_to_text(file_path):
    convert_doc_to_docx(file_path)
    docx_path = file_path.replace('.doc', '.docx')
    return docx_to_text(docx_path)


def ocr_pdf(file_path):
    doc = fitz.open(file_path)
    text = ""
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap()
        image_path = f"page_{page_num}.png"
        pix.save(image_path)
        page_text = ocr_image(image_path)
        text += f"\n\nPage {page_num + 1}:\n" + page_text
        os.remove(image_path)
    return text


def convert_to_machine_readable(file_path):
    if file_path.endswith('.pdf'):
        text = pdf_to_text(file_path)
        if not text.strip():
            st.warning(f"{file_path} file may be a Scanned Document. Attempting OCR.")
            return ocr_pdf(file_path)
        return text
    elif file_path.endswith('.docx'):
        return docx_to_text(file_path)
    elif file_path.endswith('.doc'):
        return doc_to_text(file_path)
    elif file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        return ocr_image(file_path)
    else:
        raise ValueError("Unsupported file format.")


def format_pdf_date(raw_date):
    if not raw_date or not raw_date.startswith('D:'):
        return "Not Available"
    try:
        clean_date = raw_date[2:].split('+')[0].split('-')[0].strip('Z')
        parsed_date = datetime.strptime(clean_date, "%Y%m%d%H%M%S")
        return parsed_date.strftime("%B %d, %Y, %I:%M:%S %p")
    except Exception as e:
        return f"Invalid Format: {raw_date}"


def extract_metadata_from_pdf(file_path):
    try:
        doc = fitz.open(file_path)
        metadata = doc.metadata
        doc.close()
        return {
            'file_path': file_path,
            'title': metadata.get('title', 'Not Available'),
            'author': metadata.get('author', 'Not Available'),
            'subject': metadata.get('subject', 'Not Available'),
            'keywords': metadata.get('keywords', 'Not Available'),
            'creationDate': format_pdf_date(metadata.get('creationDate')),
            'modDate': format_pdf_date(metadata.get('modDate'))
        }
    except Exception as e:
        return {'error': str(e)}


# Load the spaCy model
spacy.cli.download('en_core_web_sm')
nlp = spacy.load('en_core_web_sm')


def analyze_text(text):
    doc = nlp(text)
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    keywords = [chunk.text for chunk in doc.noun_chunks]

    # Generate summary only if Gemini is configured
    summary = ""
    if 'chat_session' in st.session_state:
        try:
            response = st.session_state.chat_session.send_message(
                f"Summarize this document with bullet points:\n\n{text[:1500]}"  # Limit input size
            )
            summary = response.text
        except Exception as e:
            summary = f"Could not generate summary: {str(e)}"

    return {
        'entities': entities,
        'keywords': keywords,
        'summary': summary if summary else "Enable Gemini API for AI summary"
    }


# Streamlit Interface
st.set_page_config(page_title="File Q&A", page_icon="📄", layout="wide")

# Sidebar configuration
with st.sidebar:
    st.title("Gemini Chat")
    st.subheader("Gemini API Configuration")

    # API key input
    api_key = st.text_input("Enter your Gemini API key", type="password")

    if st.button("Submit API Key"):
        try:
            genai.configure(api_key=api_key)
            st.session_state.gemini_model = genai.GenerativeModel('gemini-2.0-flash')
            st.session_state.chat_session = st.session_state.gemini_model.start_chat(history=[])
            st.success("API key configured successfully!")
        except Exception as e:
            st.error(f"Error configuring API: {str(e)}")

    st.markdown("[Get Gemini API Key](https://aistudio.google.com/app/apikey/)")

    st.subheader("Navigation")
    selected_mode = st.selectbox("Select Mode", ["File Q&A"])

# Main content area
st.title("File Q&A")

# File uploader
uploaded_file = st.file_uploader("Choose a file", type=["jpg", "jpeg", "png", "pdf", "txt", "docx"])

# Query bar
user_query = st.text_input("Ask a question about the document(s):",
                           placeholder="Type your question here...")

# Process files

if uploaded_file:
        ##Clear previous caht
        if "last_uploaded_file" not in st.session_state or st.session_state.last_uploaded_file != uploaded_file.name:
            st.session_state.file_messages = []
            st.session_state.last_uploaded_file = uploaded_file.name
        # Create a temporary file with the correct extension
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as file:
            file.write(uploaded_file.getvalue())
            file_path = file.name

        # Process file
        with st.spinner(f"Processing {file.name}..."):
            text = convert_to_machine_readable(file_path)
            analysis = analyze_text(text)
            metadata = extract_metadata_from_pdf(file_path) if file.name.endswith('.pdf') else {
                'file_path': file_path,
                'title': file.name,
                'author': 'Not Available',
                'creationDate': 'Not Available'
            }

        # Tabs for results
        tab1, tab2, tab3 = st.tabs(["📝 Extracted Text", "🔍 Analysis", "🧾 Metadata"])

        with tab1:
            cleaned_text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
            st.text_area("Text Content", cleaned_text, height=400)

        with tab2:
            # Entities section
            st.subheader("Entities")
            if analysis["entities"]:
                # Group entities by type
                entity_types = {}
                for entity, etype in analysis["entities"]:
                    if etype not in entity_types:
                        entity_types[etype] = []
                    entity_types[etype].append(entity)

                # Create a single string with all entities grouped by type
                entities_display = []
                for etype, entities in entity_types.items():
                    entities_display.append(f"--- {etype.upper()} ---")
                    entities_display.extend([f"• {entity}" for entity in entities])

                # Display all entities in a single selectbox
                st.selectbox(
                    f"All Entities ({len(analysis['entities'])})",
                    entities_display,
                    key=f"{file.name}-entities",
                    disabled=False # Makes it read-only
                )
            else:
                st.write("No entities found.")

            # Keywords section
            st.subheader("Keywords")
            if analysis["keywords"]:
                unique_keywords = list(set(analysis["keywords"]))  # Remove duplicates

                # Create formatted display with bullet points
                keywords_display = [f"• {keyword}" for keyword in unique_keywords]

                # Display in a single selectbox (read-only)
                st.selectbox(
                    f"All Keywords ({len(unique_keywords)})",
                    keywords_display,
                    key=f"{file.name}-keywords",
                    disabled=False  # Makes it read-only
                )
            else:
                st.write("No keywords found.")

            # Summary section
            st.subheader("Document Summary")
            st.write(analysis["summary"])

            # Handle user query
            if user_query and 'chat_session' in st.session_state:
                with st.spinner("Generating answer..."):
                    try:
                        context = text[:15000]  # Limit context size
                        response = st.session_state.chat_session.send_message(
                            f"Answer this question based on the document: {user_query}\n\nDocument content:\n{context}"
                        )
                        st.subheader("Answer to your question")
                        st.write(response.text)
                    except Exception as e:
                        st.error(f"Could not generate answer: {str(e)}")

        with tab3:
            st.subheader("File Metadata")
            for key, value in metadata.items():
                st.write(f"**{key.capitalize()}**: {value}")
