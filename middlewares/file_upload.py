from flask import flash, redirect, request, render_template
import os
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def handle_file_upload(request, user_upload_folder, id, name, username, emailAddr, profile_pic):
    # Check if the user upload a requests with a profile pic
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['file']

    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        # Save the uploaded file
        filename = secure_filename('avatar.jpg')
        file_path = os.path.join(user_upload_folder, filename)
        file.save(file_path)
        profile_pic = id + '/' + filename
        print(profile_pic)

        flash('File uploaded successfully')
        return render_template('settings.html', name=name, username=username, email=emailAddr, profile_pic=profile_pic)
    else:
        flash('Invalid file format.')
        return redirect(request.url)