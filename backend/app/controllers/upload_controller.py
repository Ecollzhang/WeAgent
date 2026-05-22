import os
import uuid
from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename
from app.utils.response import success_response, error_response

upload_bp = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@upload_bp.route('', methods=['POST'])
@jwt_required()
def upload_file():
    """Upload a file and return its accessible URL."""
    if 'file' not in request.files:
        return error_response('No file provided', code=400)

    file = request.files['file']
    if file.filename == '':
        return error_response('No file selected', code=400)

    if not allowed_file(file.filename):
        return error_response('File type not allowed', code=400)

    # Secure the filename and add UUID to avoid collisions
    original_name = secure_filename(file.filename)
    ext = original_name.rsplit('.', 1)[1].lower() if '.' in original_name else ''
    unique_name = f'{uuid.uuid4().hex}.{ext}'

    upload_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)

    file.save(os.path.join(upload_dir, unique_name))

    url = f'/uploads/{unique_name}'
    print(f'[WeAgent] File saved: {unique_name}')
    return success_response({'url': url}, message='File uploaded')
