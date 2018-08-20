import hashlib
import os
import uuid
from datetime import datetime

from PIL import Image
from flask import flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_mail import Message
from werkzeug.utils import secure_filename

from flaskmod import app, db, mail
from forms import LoginForm, RegistrationForm, RequestResetForm, UpdateAccount, ResetPasswordForm
from models import File, User


@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for('data', path="home/"))
    return redirect(url_for('register'))


@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        flash("Account created for {}".format(form.username.data), 'success')
        hashed_pwd = hashlib.md5(form.password.data).hexdigest()
        user = User(username=form.username.data, email=form.email.data, date_of_birth=form.dob.data,
                    phone_number=form.phone_number.data, password=hashed_pwd)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('register'))
    return render_template('register.html', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('data', path='home/'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and hashlib.md5(form.password.data).hexdigest() == user.password:
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('data', path="home/"))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


def get_user_files(parent_path):
    if current_user.is_authenticated:
        files = File.query.filter(File.user_id == current_user.id, File.parent_path == "/" + parent_path,
                                  File.deleted_at.is_(None)).all()
        return files
    return []


@app.route("/data/<path:path>")
def data(path="home/"):
    return render_template("data.html", path=path, title="Data", files=get_user_files(path), func=get_user_files)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('register'))


def save_picture(form_picture):
    uni_id = uuid.uuid4().hex
    fname, fext = os.path.splitext(form_picture.filename)
    picture = uni_id + fext
    pic_path = os.path.join("/home/jalpesh/Drashti/projects/drive/flaskmod/static/profile_pics", picture)
    output_size = (256, 256)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(pic_path)
    return picture


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccount()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.phone_number = form.phone_number.data
        current_user.date_of_birth = form.dob.data
        db.session.commit()
        flash("Your account info has been updated", 'success')
        return redirect(url_for('account'))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.phone_number.data = current_user.phone_number
        form.dob.data = current_user.date_of_birth
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account', image_file=image_file, form=form)


@app.route("/upload_file/<path:path>", methods=['GET', 'POST'])
def upload_file(path):
    if request.method == "POST":
        file = request.files['file']

        filename = ".".join(secure_filename(file.filename).split(".")[:-1]) + "_" + str(current_user.id)
        ext = os.path.splitext(file.filename)[-1]
        filename = filename + ext
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        parent_path = request.form.get('parent_path')
        size = os.path.getsize(file_path)
        filedata = File(user_id=current_user.id, child_path=filename, type=ext, original_path="/home/ubuntu/data",
                        filename=filename,
                        size=size, parent_path='/' + parent_path.strip('/') + '/')
        db.session.add(filedata)
        db.session.commit()
        return redirect(url_for("data", path=path))

    else:
        return render_template("upload_file.html", path=path)


@app.route("/create_folder/<path:path>", methods=['GET', 'POST'])
def create_folder(path):
    if request.method == "POST":
        parent_path = request.form.get('parent_path')
        child_path = request.form.get('folder')
        type = "dir"
        filedata = File(user_id=current_user.id, child_path=child_path, type=type, original_path="/home/ubuntu/data",
                        parent_path='/' + parent_path.strip('/') + '/', filename=child_path)
        db.session.add(filedata)
        db.session.commit()
        return redirect(url_for("data", path=path))
    else:
        return render_template("create_folder.html", path=path)


@app.route("/getfile/<int:id>")
def getfile(id):
    file = File.query.filter_by(id=id).first()
    if current_user.is_authenticated and current_user.id == file.user_id:
        file_path = os.path.join(file.original_path, file.filename)
        return send_file(file_path, as_attachment=True)
    else:
        return redirect(url_for('login'))


@app.route("/delete/<int:id>")
def delete(id):
    file_data = File.query.filter_by(id=id).first()
    if current_user.is_authenticated and current_user.id == file_data.user_id:
        file_data.deleted_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for('data', path="home/"))


def send_reset_email(user):
    token = user.get_token()
    msg = Message('Password Reset Request', sender='dhrashti.2563@gmail.com', recipients=[user.email])
    msg.body = ''' To reset the password click on the below link.
    {}
    If you did not request for this change please ignore the email and no changes will be done.    
    '''.format(url_for('reset_token', token = token, _external=True))
    mail.send(msg)


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('data', path=path))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash("Reset link has been sent in an email and will expire in 15 mins")
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('data', path=path))
    user = User.verify_reset_token(token)
    if user is None:
        flash('The link is invalid or expired. Please try again', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_pwd = hashlib.md5(form.password.data).hexdigest()
        user.password = hashed_pwd
        db.session.commit()
        flash("Password has been changed successfully!!")
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)
