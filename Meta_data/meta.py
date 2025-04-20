import os
import fitz  # PyMuPDF
from PIL import Image
from PIL.ExifTags import TAGS



def extract_pdf_metadata(file_path):
    """Extract metadata from a PDF file."""
    doc = fitz.open(file_path)
    return doc.metadata


def extract_image_metadata(image_path):
    """Extract EXIF metadata from an image file."""
    image = Image.open(image_path)
    exif_data = image.getexif()
    metadata = {TAGS.get(tag_id, tag_id): value for tag_id, value in exif_data.items()}
    return metadata


def extract_general_metadata(file_path):
    """Extract general file metadata."""
    stats = os.stat(file_path)
    metadata = {
        'size (bytes)': stats.st_size,
        'last modified': stats.st_mtime,
        'creation time': stats.st_ctime
    }
    return metadata


def extract_metadata(file_path):
    """Extract metadata based on file type."""
    if file_path.endswith('.pdf'):
        return extract_pdf_metadata(file_path)
    elif file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        return extract_image_metadata(file_path)
    else:
        return extract_general_metadata(file_path)


