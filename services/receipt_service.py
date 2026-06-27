import os
import uuid
from werkzeug.utils import secure_filename
from flask import send_from_directory
from config import Config

def allowed_file(filename):
    """Checks if the uploaded file has a valid extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def save_receipt(file):
    """
    Saves the receipt file to the upload directory.
    Returns the unique saved filename if successful, otherwise None.
    """
    if not file or file.filename == '':
        return None
    
    if allowed_file(file.filename):
        # Clean the original filename
        filename = secure_filename(file.filename)
        
        # Split extension and name to generate a unique key
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{uuid.uuid4().hex[:10]}{ext}"
        
        # Ensure uploads directory exists
        upload_dir = Config.UPLOAD_FOLDER
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file to path
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)
        
        return unique_filename
    
    return None

def delete_receipt(filename):
    """Deletes the receipt file from storage if it exists."""
    if not filename:
        return False
    try:
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception:
        pass
    return False

def serve_receipt_file(filename):
    """Serves the receipt file for viewing or downloading."""
    return send_from_directory(Config.UPLOAD_FOLDER, filename)
