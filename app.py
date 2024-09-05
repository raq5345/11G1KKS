from flask import Flask, render_template, redirect, url_for, flash, request, send_from_directory, jsonify
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField, StringField
from wtforms.validators import InputRequired
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'static/files'

# Make enumerate available in Jinja2 templates
app.jinja_env.globals.update(enumerate=enumerate)

class UploadFileForm(FlaskForm):
    folder = StringField("Select or Enter Folder", validators=[InputRequired()])
    file = FileField("File", validators=[InputRequired()])
    custom_name = StringField("Custom File Name")
    submit = SubmitField("Upload File")

class CreateFolderForm(FlaskForm):
    parent_folder = StringField("Parent Folder (Optional)")
    new_folder = StringField("New Folder Name", validators=[InputRequired()])
    submit = SubmitField("Create Folder")

class SearchForm(FlaskForm):
    search = StringField("Search Folders")
    submit = SubmitField("Search")

def get_folders(base_folder=None):
    folders = []
    upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], base_folder) if base_folder else app.config['UPLOAD_FOLDER']
    for root, dirs, _ in os.walk(upload_dir):
        for dir_name in dirs:
            relative_path = os.path.relpath(os.path.join(root, dir_name), app.config['UPLOAD_FOLDER'])
            folders.append(relative_path)
    return folders

@app.route('/', methods=['GET', 'POST'])
@app.route('/home', methods=['GET', 'POST'])
def home():
    upload_form = UploadFileForm()
    folder_form = CreateFolderForm()

    # Get all folders for display purposes
    folders = get_folders()

    # Handle the creation of a new folder
    if folder_form.validate_on_submit() and folder_form.submit.data:
        parent_folder = folder_form.parent_folder.data.strip() if folder_form.parent_folder.data else ''
        new_folder = secure_filename(folder_form.new_folder.data.strip())

        # Correctly construct the full path for the new folder
        if parent_folder:
            folder_path = os.path.join(app.config['UPLOAD_FOLDER'], parent_folder, new_folder)
        else:
            folder_path = os.path.join(app.config['UPLOAD_FOLDER'], new_folder)

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            flash(f"Folder '{new_folder}' created successfully in '{parent_folder if parent_folder else 'root'}'.", "success")
        else:
            flash(f"Folder '{new_folder}' already exists in '{parent_folder if parent_folder else 'root'}'.", "error")
        return redirect(url_for('home'))

    # Handle file upload
    if upload_form.validate_on_submit() and upload_form.submit.data:
        folder_path = upload_form.folder.data.strip()  # Full path from form input
        if folder_path and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], folder_path)):
            uploaded_file = upload_form.file.data
            original_filename = secure_filename(uploaded_file.filename)
            original_extension = os.path.splitext(original_filename)[1]  # Extract the original file extension

            # Determine the final filename, preserving the extension if necessary
            if upload_form.custom_name.data:
                custom_name = secure_filename(upload_form.custom_name.data.strip())
                custom_extension = os.path.splitext(custom_name)[1]
                filename = custom_name if custom_extension else custom_name + original_extension
            else:
                filename = original_filename

            # Verify that the file has a valid extension
            if not os.path.splitext(filename)[1]:
                filename += original_extension

            save_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_path, filename)
            uploaded_file.save(save_path)

            flash(f"File '{filename}' uploaded to '{folder_path}'.", "success")
        else:
            flash("Please select a valid folder.", "error")
        return redirect(url_for('home'))

    return render_template('index.html', upload_form=upload_form, folder_form=folder_form, folders=folders)


@app.route('/files', methods=['GET', 'POST'])
def files():
    search_form = SearchForm()
    current_folder = request.args.get('folder', '')  # This should be a relative path like 'b1/b2/b3'
    folders = {}

    # Construct the base path correctly with all parent directories
    base_path = os.path.join(app.config['UPLOAD_FOLDER'], current_folder.lstrip('/'))

    files = []
    if os.path.exists(base_path) and os.path.isdir(base_path):
        for entry in os.listdir(base_path):
            entry_path = os.path.join(base_path, entry)
            if os.path.isdir(entry_path):
                subfolder_files = os.listdir(entry_path)
                folders[entry] = {
                    'files': subfolder_files,
                    'file_count': len(subfolder_files),
                    'last_upload_time': max(
                        [datetime.fromtimestamp(os.path.getmtime(os.path.join(entry_path, f))) for f in subfolder_files]
                    ).timestamp() if subfolder_files else None
                }
            elif os.path.isfile(entry_path):
                files.append(entry)

    # Handle search functionality
    if search_form.validate_on_submit() and search_form.submit.data:
        search_query = search_form.search.data.strip().lower()
        folders = {folder: data for folder, data in folders.items() if search_query in folder.lower() or any(search_query in f.lower() for f in data['files'])}
        files = [f for f in files if search_query in f.lower()]

    return render_template('files.html', folders=folders, files=files, search_form=search_form, path=current_folder)


@app.route('/search', methods=['GET', 'POST'])
def search():
    search_form = SearchForm()
    folders = []
    results = []

    if search_form.validate_on_submit():
        search_query = search_form.search.data.strip().lower()
        folders = get_folders()
        results = [folder for folder in folders if search_query in folder.lower()]

    return render_template('search.html', search_form=search_form, results=results)


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return redirect(url_for('static', filename='files/' + filename), code=301)

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M:%S'):
    if value is None:
        return "No files"
    return datetime.fromtimestamp(value).strftime(format)

@app.before_request
def before_request():
    pass

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
