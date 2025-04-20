import os
import cv2
import pytesseract
import fitz  # PyMuPDF
import docx
import subprocess
import streamlit as st
from Google_vision.vision import summarize
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
import spacy
from datetime import datetime


# from MongoDb.mongodb import *

# Set the path for Tesseract OCR executable
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Adjust the path as necessary

# Set up SQLAlchemy
Base = declarative_base()

class DocumentMetadata(Base):
    __tablename__ = 'document_metadata'
    id = Column(Integer, primary_key=True)
    file_path = Column(String)
    title = Column(String)
    author = Column(String)
    # Add more metadata fields as needed

engine = create_engine('sqlite:///document_metadata.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)




# Document processing functions

def preprocess_image(image_path):
    """Preprocess the image for better OCR results."""
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Failed to load image: {image_path}")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Apply thresholding
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
    return thresh

def ocr_image(image_path):
    preprocessed_image = preprocess_image(image_path)
    text = pytesseract.image_to_string(preprocessed_image)
    return text

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
    """Perform OCR on each page of a scanned PDF."""
    doc = fitz.open(file_path)
    text = ""

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap()  # Get the image of the page
        image_path = f"page_{page_num}.png"
        pix.save(image_path)  # Save the image temporarily

        # Perform OCR on the saved image
        page_text = ocr_image(image_path)
        text += f"\n\nPage {page_num + 1}:\n" + page_text

        os.remove(image_path)  # Clean up the temporary image file
    return text

def convert_to_machine_readable(file_path):
    """Main function to convert documents to machine-readable format."""
    if file_path.endswith('.pdf'):
        text = pdf_to_text(file_path)
        if not text.strip():  # If no text is found, assume it's scanned
            st.warning(f"{file_path} file may be a Scanned Document. Attempting OCR.")
            return ocr_pdf(file_path)  # Perform OCR on PDF
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
        # Remove the "D:" prefix and trailing 'Z' or timezone offset if present
        clean_date = raw_date[2:].split('+')[0].split('-')[0].strip('Z')
        # Parse the date
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
nlp = spacy.load('en_core_web_sm')

def analyze_text(text):
    """Perform NLP tasks on the extracted text."""
    doc = nlp(text)
    summary = summarize(text)
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    keywords = [chunk.text for chunk in doc.noun_chunks]

    return {
        'entities': entities,
        'keywords': keywords,
        'summary': summary
    }

# Streamlit Interface

# Configure the page
st.set_page_config(page_title="Doc Processor", page_icon="📄", layout="wide")

st.title("📄 Document Processor")
st.write("Upload documents to extract and analyze content.")

# File uploader
uploaded_files = st.file_uploader(
    "Upload files (PDF, Word, TXT)",
    type=['pdf', 'docx', 'txt','jpg', 'jpeg'],
    accept_multiple_files=True
)

# Process files
if uploaded_files:
    st.progress(100)

    for i, file in enumerate(uploaded_files):
        # Save uploaded file
        if not os.path.exists("uploads"):
            os.makedirs("uploads")
        file_path = os.path.join("uploads", file.name)
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())

        st.success(f"{file.name} uploaded successfully ({file.size // 1024} KB)")

        # Process file
        with st.spinner(f"Processing {file.name}..."):
            # Assume `convert_to_machine_readable` and `analyze_text` are your backend functions
            text = convert_to_machine_readable(file_path)
            analysis=analyze_text(text)
            summary = summarize(text)

        # Tabs for results
        tab1, tab2, tab3 = st.tabs(["📝 Extracted Text", "🔍 Analysis", "🧾 Metadata"])

        with tab1:
            cleaned_text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
            st.text_area("Text Content", cleaned_text, height=400)

        with tab2:
            with st.expander("🔎 Entities"):
                entities = [f"{e[0]} ({e[1]})" for e in analysis["entities"]]
                st.write(", ".join(entities) if entities else "No entities found.")

            with st.expander("🏷️ Keywords"):
                keywords = list(set(kw for kw in analysis["keywords"] if isinstance(kw, str)))[0:30]
                st.write(", ".join(keywords) if keywords else "No keywords found.")

            st.subheader("Summary")
            st.write(summary)

        with tab3:
            st.subheader("File Metadata")
            metadata = extract_metadata_from_pdf(file_path)

            st.subheader("Document Metadata")
            for key, value in metadata.items():
                st.write(f"**{key.capitalize()}**: {value}")

        st.progress((i + 1) / len(uploaded_files))