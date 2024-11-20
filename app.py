import os
import psycopg2
import uuid
from datetime import datetime
from flask import Flask, redirect, render_template, request, flash, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash
from functools import wraps
from middlewares.file_upload import handle_file_upload
import traceback

app = Flask(__name__, static_folder='static')
app.config['UPLOAD_FOLDER'] = 'static/users_uploads'
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')
app.config['DEBUG'] = True
csrf = CSRFProtect(app)

# WEBSITE_HOSTNAME exists only in production environment
if 'WEBSITE_HOSTNAME' not in os.environ:
    # local development, where we'll use environment variables
    print("Loading config.development and environment variables from .env file.")
    app.config.from_object('azureproject.development')
else:
    # production
    print("Loading config.production.")
    app.config.from_object('azureproject.production')

app.config.update(
    SQLALCHEMY_DATABASE_URI=app.config.get('DATABASE_URI'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)

# Initialize the database connection
db = SQLAlchemy(app)

# Enable Flask-Migrate commands "flask db init/migrate/upgrade" to work
migrate = Migrate(app, db)

# The import must be done after db initialization due to circular import issue
from models import User, BlogPost, Comment, Chat, Message, ChatMessage, Notification, LikedBlog

# Hàm để lấy kết nối và cursor
def getDB():
    # Lấy thông tin cấu hình từ biến môi trường hoặc cấu hình trong app
    db_url = os.getenv('DATABASE_URL', 'postgresql://wexuolpbnk:pVnipiv4oftoae$8@team7-python-flask-postgresql-server.postgres.database.azure.com:5432/team7-python-flask-postgresql-database')

    # Thiết lập kết nối với PostgreSQL
    conn = psycopg2.connect(db_url)
    
    # Tạo cursor để thực thi câu lệnh SQL
    cursor = conn.cursor()

    # Đóng gói trong một lớp để sử dụng với context manager
    class DBContextManager:
        def __init__(self, conn, cursor):
            self.conn = conn
            self.cursor = cursor
        
        def __enter__(self):
            return self.cursor, self.conn
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            # Đảm bảo đóng kết nối và commit
            self.cursor.close()
            if exc_type is None:
                self.conn.commit()  # Commit transaction if no exception
            else:
                self.conn.rollback()  # Rollback if there's an exception
            self.conn.close()

    return DBContextManager(conn, cursor)

def check_session(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FileField, TextAreaField, Form, EmailField
from wtforms.validators import DataRequired, Email, Length, Optional
from wtforms.fields import EmailField
import re

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired(), Email()])



# Register route
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    message = ""

    if form.validate_on_submit():
        emailAddr = form.email.data.strip()
        username = form.username.data.strip()
        password = form.password.data.strip()

        # Kiểm tra tính mạnh của mật khẩu
        if not re.fullmatch(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{6,}$', password):
            message = "Password must be at least 6 characters, include uppercase, lowercase, numbers, and special characters."
            return render_template("register.html", form=form, message=message)

        # Kiểm tra username hợp lệ
        if not re.match(r'^[A-Za-z0-9_]+$', username):
            message = "Username must only contain letters, numbers, or underscores."
            return render_template("register.html", form=form, message=message)

        # Kiểm tra email tồn tại
        try:
            with getDB() as (cursor, conn):  # Sử dụng context manager để mở kết nối và cursor
                cursor.execute('SELECT id, password FROM "user" WHERE "emailAddr" = %s', (emailAddr,))
                if cursor.fetchone():
                    message = "User already exists"
                else:
                    id = str(uuid.uuid4())
                    hashed_password = generate_password_hash(password)
                    try:
                        # Sửa câu lệnh SQL để đảm bảo rằng tên cột là chính xác
                        cursor.execute("INSERT INTO \"user\" (id, username, \"emailAddr\", password) VALUES (%s, %s, %s, %s)", 
                                    (id, username, emailAddr, hashed_password))
                        session['loggedin'] = True
                        session['id'] = id
                        return redirect('/home')
                    except Exception as e:
                        message = f"An error occurred during registration: {e}"

        except Exception as e:
            message = f"Database error: {str(e)}"

    return render_template("register.html", form=form, message=message)






from werkzeug.security import check_password_hash

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])

@app.route("/login", methods=["GET", "POST"])
def login():
    message = ""
    form = LoginForm()  # Khởi tạo form

    if request.method == "POST" and form.validate_on_submit():
        emailAddr = form.email.data.strip()  # Lấy email từ form
        password = form.password.data.strip()  # Lấy password từ form

        try:
            # Sử dụng context manager để tự động quản lý kết nối và cursor
            with getDB() as (cursor, conn):  # Sử dụng đúng cú pháp context manager
                # Đảm bảo rằng tên cột trong câu truy vấn chính xác
                cursor.execute('SELECT id, password FROM "user" WHERE "emailAddr" = %s', (emailAddr,))
                user_info = cursor.fetchone()

                if user_info:
                    id, hashed_password = user_info
                    # Kiểm tra mật khẩu
                    if check_password_hash(hashed_password, password):
                        session['loggedin'] = True
                        session['id'] = id
                        return redirect('/home')   
                    else:
                        message = "Wrong Email or Password"
                else:
                    message = "Wrong Email or Password"
        except Exception as e:
            # Log lỗi nếu có
            message = f"Error: {str(e)}"

    return render_template("login.html", form=form, message=message)



@app.route("/home")
@app.route("/")
@check_session
def home():
    with getDB() as (cursor, conn):
        id = session.get('id')
        profile_pic, data = None, []

        # Kiểm tra ID hợp lệ
        if not id:
            return redirect('/login')

        # Kiểm tra user có tồn tại
        cursor.execute("SELECT id FROM \"user\" WHERE id = %s", (id,))
        user_data = cursor.fetchone()
        if not user_data:
            return redirect('/login')

        # Truy vấn số lượng thông báo
        cursor.execute("SELECT COUNT(*) FROM \"notification\" WHERE myid = %s", (str(id),))
        count_noti = cursor.fetchone()[0]  # Truy xuất giá trị đầu tiên (COUNT(*)) trong tuple

        cursor.execute("SELECT COUNT(*) FROM \"notification\" WHERE myid = %s AND ischat = TRUE", (str(id),))
        count_noti_chat = cursor.fetchone()[0]  # Truy xuất giá trị đầu tiên (COUNT(*)) trong tuple

        # Lấy danh sách blog
        cursor.execute("SELECT title, content FROM \"blogPosts\" WHERE publish = TRUE ORDER BY RANDOM() LIMIT 5")
        blog_info = cursor.fetchall() or []

        # Lấy thông tin người dùng
        cursor.execute("SELECT username FROM \"user\" WHERE id = %s", (id,))
        user_info = cursor.fetchone()
        user_info = user_info[0] if user_info else "Unknown"  # Truy cập tên người dùng bằng chỉ số

        # Kiểm tra ảnh đại diện
        avatar_path = os.path.join(app.config['UPLOAD_FOLDER'], str(id), 'avatar.jpg')
        profile_pic = str(id) + '/avatar.jpg' if os.path.exists(avatar_path) else "../../img/avatar.jpg"

        # Lấy danh sách thông báo
        cursor.execute("SELECT myid, content, timestamp, from_id, ischat FROM \"notification\" WHERE myid = %s", (str(id),))
        noti_list = cursor.fetchall() or []

        for noti in noti_list:
            myid, content, timestamp, fromid, ischat = noti  # Truy cập tuple trực tiếp

            # Lấy thông tin người gửi
            cursor.execute("SELECT username FROM \"user\" WHERE id = %s", (fromid,))
            sender_name = cursor.fetchone()
            sender_name = sender_name[0] if sender_name else "Unknown"  # Truy cập tên người gửi từ tuple

            sender_ava_path = os.path.join(app.config['UPLOAD_FOLDER'], str(fromid), 'avatar.jpg')
            sender_pic = str(fromid) + '/avatar.jpg' if os.path.exists(sender_ava_path) else "../../img/avatar.jpg"

            # Lấy room ID (rid) từ bảng chat
            cursor.execute(
                "SELECT id FROM \"chat\" WHERE (\"userID1\" = %s AND \"userID2\" = %s) OR (\"userID1\" = %s AND \"userID2\" = %s)",
                (id, fromid, fromid, id)
            )
            rid = cursor.fetchone()
            rid = rid[0] if rid else None  # Truy cập rid từ tuple

            # Thêm thông báo vào danh sách
            data.append({
                "myid": myid,
                "fromid": fromid,
                "fromname": sender_name,
                "content": content,
                "time": timestamp,
                "sender_pic": sender_pic,
                "ischat": ischat,
                "rid": rid
            })

        # Render giao diện với dữ liệu đã xử lý
        return render_template(
            'index.html',
            blog_info=blog_info,
            user_info=user_info,
            profile_pic=profile_pic,
            myid=id,
            data=data,
            count_noti=count_noti,
            count_noti_chat=count_noti_chat
        )







@app.route('/profile')
@check_session
def profile():
    # Lấy ID từ session
    user_id = session.get('id')
    if not user_id:
        return redirect('/login')  # Chuyển hướng nếu không có ID

    try:
        with getDB() as (cursor, conn):
            # Kiểm tra người dùng tồn tại
            user_info = cursor.execute("SELECT username FROM \"user\" WHERE id = %s", (user_id,)).fetchone()
            if not user_info:
                return redirect('/login')  # Chuyển hướng nếu người dùng không tồn tại

            username = user_info[0]

            # Truy vấn dữ liệu liên quan đến blog và thông tin khác
            blog_count = cursor.execute("SELECT COUNT(*) FROM \"blogPosts\" WHERE \"userID\" = %s", (user_id,)).fetchone()
            blog_info = cursor.execute(
                "SELECT id, title, content, authorname, publish FROM \"blogPosts\" WHERE \"userID\" = %s",
                (user_id,)
            ).fetchall()
            published_blogs = cursor.execute(
                "SELECT id, title, authorname, publish FROM \"blogPosts\" WHERE \"userID\" = %s AND publish = 1",
                (user_id,)
            ).fetchall()

            # Xử lý blog đã thích
            liked_blogs_title = cursor.execute(
                "SELECT title FROM \"likedBlogs\" WHERE liked = 1 AND \"userID\" = %s",
                (user_id,)
            ).fetchall()

            liked_blogs_titles = [title_blog[0] for title_blog in liked_blogs_title]
            total_blog = cursor.execute(
                "SELECT id, title, authorname, publish FROM \"blogPosts\" WHERE title IN %s",
                (tuple(liked_blogs_titles),)
            ).fetchall()

            # Xử lý ảnh đại diện
            upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
            avatar_path = os.path.join(upload_folder, str(user_id), 'avatar.jpg')
            if os.path.exists(avatar_path):
                profile_pic = os.path.join(str(user_id), 'avatar.jpg')
            else:
                profile_pic = "../../img/avatar.jpg"

            # Kết xuất template
            return render_template(
                'profile.html',
                username=username,
                blog_info=blog_info,
                profile_pic=profile_pic,
                published_blogs=published_blogs,
                blog_count=blog_count,
                liked_blogs=total_blog
            )
    except Exception as error:
        # Ghi chi tiết lỗi vào log
        app.logger.error(f"ERROR: {error}")
        app.logger.error(traceback.format_exc())  # Ghi chi tiết lỗi vào log
        return jsonify({"error": "Internal Server Error"}), 500

    return redirect('/login')




class SettingsForm(FlaskForm):
    name = StringField('Name', validators=[Optional(), Length(max=80)])  # Tên có thể bỏ qua, tối đa 80 ký tự
    username = StringField('Username', validators=[Optional(), Length(max=80)])  # Username có thể bỏ qua, tối đa 80 ký tự
    email = StringField('Email', validators=[Optional(), Email(), Length(max=80)])  # Email có thể bỏ qua, kiểm tra đúng định dạng email và tối đa 80 ký tự
    password = PasswordField('Password', validators=[Optional(), Length(min=8, max=80)])  # Mật khẩu có thể bỏ qua, tối thiểu 8 ký tự và tối đa 80 ký tự
    bio = TextAreaField('Bio', validators=[Optional(), Length(max=160)])  # Bio có thể bỏ qua, tối đa 160 ký tự
    avatar = FileField('Avatar')  # Avatar có thể bỏ qua

@app.route('/settings', methods=["GET", "POST"])
@check_session
def settings():
    user_id = session.get('id')
    if not user_id:
        return redirect(url_for('login'))

    try:
        # Kiểm tra xem id có tồn tại trong database không
        with getDB() as (cursor, conn):
            cursor.execute("SELECT id FROM user WHERE id = %s", (user_id,))
            if cursor.fetchone() is None:        
                return redirect(url_for('login'))  # Redirect nếu id không tồn tại

            # Lấy thông tin người dùng
            cursor.execute("SELECT name, username, emailAddr, password FROM user WHERE id = %s", (user_id,))
            user_info = cursor.fetchone()

        if user_info is None:
            return "User not found", 404

        name, username, emailAddr, hashed_password = user_info
        print(hashed_password)

        profile_pic = None

        # Thư mục upload của người dùng
        user_upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(user_id))

        if request.method == "POST":
            # Kiểm tra các trường cập nhật từ người dùng
            if 'name' in request.form:
                new_name = request.form['name']
                with getDB() as (cursor, conn):
                    cursor.execute("UPDATE user SET name = %s WHERE id = %s", (new_name, user_id))
                name = new_name

            if 'username' in request.form:
                new_username = request.form['username']
                with getDB() as (cursor, conn):
                    cursor.execute("UPDATE user SET username = %s WHERE id = %s", (new_username, user_id))
                username = new_username

            if 'email' in request.form:
                new_email = request.form['email']
                with getDB() as (cursor, conn):
                    cursor.execute("UPDATE user SET emailAddr = %s WHERE id = %s", (new_email, user_id))
                emailAddr = new_email   

            if 'password' in request.form:
                new_password = request.form['password']
                if new_password:
                    if bcrypt.checkpw(new_password.encode('utf-8'), hashed_password):
                        print('Please provide a password different from your old one!')
                        return redirect(request.url)
                    else:   
                        new_hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                        with getDB() as (cursor, conn):
                            cursor.execute("UPDATE user SET password = %s WHERE id = %s", (new_hashed_password, user_id))
                        hashed_password = new_hashed_password
                else:
                    pass

            # Quản lý upload file
            result = handle_file_upload(request, user_upload_folder, user_id, name, username, emailAddr, profile_pic)
            if result:
                return result 

        avatar_path = os.path.join(app.config['UPLOAD_FOLDER'], str(user_id), 'avatar.jpg')
        print(avatar_path)     
        if os.path.exists(avatar_path):
            profile_pic = os.path.join(str(user_id), 'avatar.jpg')
        if profile_pic is None:
            profile_pic = os.path.join("", "../../img/avatar.jpg")

        return render_template('settings.html', name=name, username=username, email=emailAddr, profile_pic=profile_pic)
    
    except Exception as e:
        return f"An error occurred: {str(e)}", 500



# Logout route
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    return redirect('/login')


@app.route("/save_blog", methods=["GET", "POST"])
@check_session
def save_blog():
    id = session.get('id')

    if not id:        
        return redirect(url_for('login'))

    # Sử dụng getDB() với context manager
    with getDB() as (cursor, conn):
        # Lấy thông tin người dùng từ cơ sở dữ liệu
        user_info = cursor.execute("SELECT id, username FROM \"user\" WHERE id = %s", (id,)).fetchone()
        if not user_info:
            app.logger.error("User not found in database")
            return redirect(url_for('login'))  # Người dùng không tồn tại

        username = user_info[1]

        if request.method == "POST":
            try:
                if not request.is_json:
                    app.logger.error("Invalid or missing JSON payload")
                    return "Invalid or missing JSON payload", 400

                blogTitle = request.json.get('blogTitle')
                blogContent = request.json.get('blogContent')

                # Kiểm tra xem blogTitle và blogContent có hợp lệ không
                if blogTitle and blogContent:
                    # Thêm blog mới vào cơ sở dữ liệu
                    cursor.execute(
                        "INSERT INTO \"blogPosts\" (\"userID\", title, content, authorname) VALUES (%s, %s, %s, %s)",
                        (id, blogTitle, blogContent, username)
                    )
                    conn.commit()
                    app.logger.info(f"Blog successfully uploaded by user {username} with title: {blogTitle}")
                    return "Blog successfully uploaded!"
                else:
                    app.logger.error("Missing blog title or content")
                    return "Missing blog title or content", 400
            except Exception as error:
                app.logger.error(f"ERROR in /save_blog: {error}")
                app.logger.error(traceback.format_exc())  # Ghi chi tiết lỗi vào log
                return jsonify({"error": "Server error occurred", "message": str(error)}), 500
    return None




@app.route("/delete_blog", methods=["POST"])
@check_session
def delete_blog():
    id = session.get("id")

    # Sử dụng getDB() với context manager
    with getDB() as (cursor, conn):  # unpack cursor và conn từ context manager
        # Kiểm tra id người dùng
        cursor.execute("SELECT id FROM \"user\" WHERE id = ?", (id,)).fetchone()
        if not id:        
            return redirect(url_for('login'))

        try:
            blog_id = request.form.get('blog_id')

            if blog_id:
                # Xóa blog khỏi cơ sở dữ liệu
                cursor.execute("DELETE FROM \"blogPosts\" WHERE id = ?", (blog_id,))
                conn.commit()

            return redirect(url_for('profile'))
        except Exception as error:
            print(f"ERROR: {error}", flush=True)
            return "Internal Server Error", 500



@app.route("/update_published", methods=["POST"])
@check_session
def published():
    id = session.get('id')

    # Sử dụng context manager để lấy cursor và connection
    with getDB() as (cursor, conn):  # unpack cursor và conn từ context manager
        # Kiểm tra xem id có tồn tại trong cơ sở dữ liệu không
        cursor.execute("SELECT id FROM \"user\" WHERE id = ?", (id,)).fetchone()
        if not id:        
            return redirect(url_for('login'))

        try:
            blogID = request.json.get('blogID')
            published_status = request.json.get('published')

            if blogID is not None and published_status is not None:
                # Cập nhật trạng thái publish của bài viết
                cursor.execute("UPDATE \"blogPosts\" SET publish = ? WHERE id = ?", (published_status, blogID))
                conn.commit()
                return 'Updated'
            else:
                return "Missing data", 400

        except Exception as error:
            print(f"ERROR: {error}", flush=True)
            return "Server error occurred", 500



@app.route('/blog/<string:blog_title>')
@check_session
def view_blog(blog_title):
    id = session.get('id')

    # Sử dụng context manager để lấy cursor và connection
    with getDB() as (cursor, conn):  # unpack cursor và conn từ context manager
        # Kiểm tra xem id có tồn tại trong cơ sở dữ liệu không
        cursor.execute("SELECT id FROM \"user\" WHERE id = ?", (id,)).fetchone()
        if not id:        
            return redirect(url_for('login'))

        # Giải mã title từ URL
        decode_title = unquote(blog_title)

        # Lấy thông tin bài viết từ cơ sở dữ liệu
        blog_post = cursor.execute(
            "SELECT title, content, likes, authorname, \"userID\" FROM \"blogPosts\" WHERE title = ? AND publish = 1",
            (decode_title,)
        ).fetchone()

        if blog_post:
            title, content, likes, authorname, userID = blog_post

            # Lấy thông tin bình luận của bài viết
            comment_content = cursor.execute(
                "SELECT username, comment FROM \"commentsBlog\" WHERE title = ?", (decode_title,)
            ).fetchall()

            # Kiểm tra xem người dùng đã thích bài viết chưa
            liked = cursor.execute(
                "SELECT liked FROM \"likedBlogs\" WHERE title = ? AND userID = ?", (decode_title, id)
            ).fetchone()
            liked = liked[0] if liked else 0

            # Trả về trang blog với các thông tin
            return render_template(
                'blog.html',
                title=title,
                content=content,
                likes=likes,
                comment_content=comment_content,
                id=userID,
                authorname=authorname,
                liked=liked
            )
        else:
            return redirect(url_for('home'))



@app.route('/new_chat', methods=["POST"])
@check_session
def new_chat():
    id = session.get('id')

    try:
        # Sử dụng with để quản lý kết nối và cursor
        with getDB() as (cursor, conn):
            # Kiểm tra xem id người dùng có tồn tại trong cơ sở dữ liệu không
            cursor.execute("SELECT id FROM \"user\" WHERE id = ?", (id,))
            if not cursor.fetchone():  # Sửa kiểm tra nếu không tìm thấy người dùng
                return redirect(url_for('login'))  # Redirect nếu người dùng không tồn tại

            # Lấy thông tin từ form
            search_input = request.form.get('search_input')
            invite_input = request.form.get('invite_input')

            if search_input:
                # Kiểm tra định dạng email hoặc username
                if re.match(r'^[\w\.-]+@[\w\.-]+$', search_input):  # Kiểm tra email
                    recipient_info = cursor.execute(
                        "SELECT id, username, \"emailAddr\" FROM \"user\" WHERE emailAddr = ?", (search_input,)
                    ).fetchone()
                else:  # Kiểm tra username
                    recipient_info = cursor.execute(
                        "SELECT id, username, \"emailAddr\" FROM \"user\" WHERE username = ?", (search_input,)
                    ).fetchone()

                if recipient_info:
                    recipient_id, recipient_username, recipient_email = recipient_info

                    # Kiểm tra xem cuộc trò chuyện đã tồn tại chưa
                    chat_exists = cursor.execute(
                        "SELECT id FROM chat WHERE (userID1 = ? AND userID2 = ?) OR (userID1 = ? AND userID2 = ?)",
                        (id, recipient_id, recipient_id, id)
                    ).fetchone()
                    if chat_exists:
                        return jsonify({'error': 'Chat already exists'}), 400

                    # Kiểm tra xem đã có lời mời chưa
                    notification_check = cursor.execute(
                        "SELECT * FROM notification WHERE myid = ? AND from_id = ?", (recipient_id, id)
                    ).fetchone()
                    if notification_check:
                        return jsonify({'error': 'You are already invited', 'chat_id': recipient_id, 'content': invite_input}), 404
                    else:
                        # Tạo mới chat và lưu tin nhắn đầu tiên
                        chat_id = str(uuid.uuid4())
                        cursor.execute(
                            "INSERT INTO chat (id, \"userID1\", \"userID2\") VALUES (?, ?, ?)", (chat_id, id, recipient_id)
                        )
                        conn.commit()
                        cursor.execute("INSERT INTO messages (room_id) VALUES (?)", (chat_id,))
                        conn.commit()

                        return jsonify({'success': 'New chat created successfully', 'chat_id': chat_id, 'content': invite_input}), 200
                else:
                    return jsonify({'error': 'User not found'}), 404
    except Exception as error:
        print(f"ERROR: {error}", flush=True)
        return "Internal Server Error", 500

@app.route('/chat/', methods=["GET", "POST"])
@check_session
def allChat():
    id = session.get('id')

    # Kiểm tra id có tồn tại trong cơ sở dữ liệu không
    with getDB() as (cursor, conn):
        cursor.execute("SELECT id FROM \"user\" WHERE id = %s", (id,))
        if not cursor.fetchone():        
            return redirect(url_for('login'))  # Redirect đến trang login nếu người dùng không tồn tại

        try:
            # Lấy room_id từ query string
            room_id = request.args.get("rid", None)
            count_noti_chat = cursor.execute("SELECT count(*) from notification where myid= %s and ischat = 1", (id,)).fetchone()

            # Truy vấn tất cả các phòng chat mà người dùng tham gia
            chat_list = cursor.execute("SELECT id, \"userID1\", \"userID2\" FROM chat WHERE userID1 = %s OR userID2 = %s", (id, id)).fetchall()
            count_noti = cursor.execute("SELECT count(*) from notification where myid= %s", (id,)).fetchone()

            data = []
            messages = []

            # Lấy thông tin người dùng
            queryname = cursor.execute("SELECT id, username from \"user\" where id = %s", (id,)).fetchone()
            myid, ownname = queryname

            des_id = None
            if chat_list:
                if room_id: 
                    get_desit = cursor.execute("SELECT \"userID1\", \"userID2\" FROM chat WHERE id = %s", (room_id,)).fetchall()
                    if get_desit: 
                        id1, id2 = get_desit[0]
                        des_id = id1 if id1 != id else id2

                for chat in chat_list:
                    chat_roomID, userID1, userID2 = chat
                    try:
                        # Lấy tất cả các tin nhắn trong phòng chat
                        messages_th = cursor.execute("SELECT id, content, timestamp, sender_id, sender_username, room_id FROM chat_messages WHERE room_id = %s", (chat_roomID,)).fetchall()

                        # Lấy tin nhắn mới nhất trong phòng chat
                        latest_message = cursor.execute("SELECT id, content, timestamp, sender_id, sender_username, room_id FROM chat_messages WHERE room_id = %s ORDER BY timestamp DESC LIMIT 1", (chat_roomID,)).fetchone()

                        if userID1 == id:
                            friend = cursor.execute("SELECT username from user where id = %s", (userID2,)).fetchone()
                        else:
                            friend = cursor.execute("SELECT username from user where id = %s", (userID1,)).fetchone()
                        
                        if room_id == chat_roomID:
                            for message in messages_th:
                                var1, var2, var3, var4, var5, var6 = message
                                messages.append({
                                    "content": var2,
                                    "timestamp": var3,
                                    "sender_username": var5,
                                })

                    except (AttributeError, IndexError):
                        latest_message = "This place is empty. No messages ..." 

                    data.append({
                        "username": friend[0] if friend else "Unknown",
                        "room_id": chat_roomID,
                        "last_message": latest_message,
                    })

            messages = messages if room_id else []

            profile_pic = None
            avatar_path = os.path.join(app.config['UPLOAD_FOLDER'], str(id))
            avatar_path_full = avatar_path + '/avatar.jpg'

            if os.path.exists(avatar_path_full):
                profile_pic = f'{id}/avatar.jpg'
            if not profile_pic:
                profile_pic = os.path.join("", "../../img/avatar.jpg")

            if not chat_list:
                return render_template('chatbox-code.html', room_id=room_id, data=data, messages=messages, ownname=ownname, myid=myid, profile_pic=profile_pic, count_noti=count_noti, des_id=des_id, count_noti_chat=count_noti_chat)
            else:
                return render_template('chatbox-code.html', room_id=room_id, data=data, messages=messages, ownname=ownname, myid=myid, profile_pic=profile_pic, count_noti=count_noti, des_id=des_id, count_noti_chat=count_noti_chat)

        except Exception as error:
            print(f"ERROR: {error}", flush=True)
            return "Internal Server Error", 500


@app.route('/deletenoti', methods=["POST"])
@check_session
def deletenoti():
    id = session.get('id')

    try:
        # Sử dụng with để quản lý kết nối và cursor
        with getDB() as (cursor, conn):
            # Kiểm tra xem người dùng có tồn tại trong cơ sở dữ liệu không
            cursor.execute("SELECT id FROM user WHERE id = ?", (id,))
            if not cursor.fetchone():
                return redirect(url_for('login'))  # Redirect nếu người dùng không tồn tại

            # Chuyển đổi dữ liệu JSON thành dictionary
            data = request.data.decode('utf-8')  
            data_dict = json.loads(data)  

            if 'fromid' in data_dict and 'toid' in data_dict:
                fromid = data_dict['fromid']
                toid = data_dict['toid']

                # Kiểm tra xem người nhận có tồn tại trong cơ sở dữ liệu không
                recipient_info = cursor.execute("SELECT id FROM user WHERE id = ?", (toid,)).fetchone()
                if recipient_info:
                    # Xóa thông báo từ người gửi đến người nhận
                    cursor.execute("DELETE FROM notification WHERE myid = ? AND from_id = ?", (id, fromid))
                    conn.commit()
                    return jsonify({'success': 'Notification deleted'}), 200
                else:
                    return jsonify({'error': 'Recipient user not found'}), 404
            else:
                return jsonify({'error': 'Invalid data format'}), 400
    except Exception as error:
        print(f"ERROR: {error}", flush=True)
        return jsonify({"error": "Internal Server Error"}), 500



@app.route('/accept', methods=["POST"])
@check_session
def accept():
    id = session.get('id')

    try:
        # Sử dụng with để quản lý kết nối và cursor
        with getDB() as (cursor, conn):
            # Kiểm tra xem người dùng có tồn tại trong cơ sở dữ liệu không
            cursor.execute("SELECT id FROM user WHERE id = ?", (id,))
            if not cursor.fetchone():
                return redirect(url_for('login'))  # Redirect nếu người dùng không tồn tại

            data = request.data.decode('utf-8')  
            data_dict = json.loads(data)

            if 'data' in data_dict:
                senderid = data_dict['data']
                # Tìm kiếm người dùng trong cơ sở dữ liệu theo email hoặc username
                recipient_info = None
                if re.match(r'^[\w\.-]+@[\w\.-]+$', senderid):
                    recipient_info = cursor.execute("SELECT id FROM user WHERE emailAddr = ?", (senderid,)).fetchone()
                else:
                    recipient_info = cursor.execute("SELECT id FROM user WHERE username = ?", (senderid,)).fetchone()

                if recipient_info:
                    recipient_id = recipient_info[0]
                    chat_exists = cursor.execute("SELECT id FROM chat WHERE (userID1 = ? AND userID2 = ?) OR (userID1 = ? AND userID2 = ?)", (id, recipient_id, recipient_id, id)).fetchone()
                    
                    if chat_exists:
                        return jsonify({'error': 'Chat already exists'}), 400
                    else:
                        chat_id = str(uuid.uuid4())
                        cursor.execute("INSERT INTO chat (id, \"userID1\", \"userID2\") VALUES (?, ?, ?)", (chat_id, id, recipient_id))
                        conn.commit()

                        chat_roomID = chat_id
                        cursor.execute("INSERT INTO messages (room_id) VALUES (?)", (chat_roomID,))
                        conn.commit()

                        cursor.execute("DELETE FROM notification WHERE myid = ? AND from_id = ?", (id, senderid))
                        conn.commit()

                        return jsonify({'success': 'New chat created successfully', 'chatroom': chat_roomID}), 200
                else:
                    return jsonify({'error': 'User not found'}), 404
    except Exception as error:
        print(f"ERROR: {error}", flush=True)
        return jsonify({"error": "Internal Server Error"}), 500


@app.route('/updateLike', methods=["POST"])
@check_session
def update_like():
    id = session.get('id')

    try:
        # Sử dụng with để quản lý kết nối và cursor
        with getDB() as (cursor, conn):
            post_title = request.form.get('post_title')
            action = request.form.get('action')
            like_unlike = 1 if action == "like" else 0

            # Kiểm tra xem người dùng đã thích blog này chưa
            blog_and_user_existed = cursor.execute("SELECT * FROM \"likedBlogs\" WHERE title = ? AND userID = ?", (post_title, id)).fetchone()

            if blog_and_user_existed:
                # Cập nhật trạng thái thích/không thích
                cursor.execute("UPDATE \"likedBlogs\" SET liked = ? WHERE title = ? AND userID = ?", (like_unlike, post_title, id))
            else:
                # Thêm vào bảng likedBlogs nếu chưa có
                cursor.execute("INSERT INTO \"likedBlogs\" (title, \"userID\", liked) VALUES (?, ?, ?)", (post_title, id, like_unlike))

            conn.commit()
            return jsonify({"message": "Likes updated successfully"}), 200
    except Exception as error:
        print(f"ERROR: {error}", flush=True)
        return jsonify({"error": "Internal Server Error"}), 500


@app.route('/addComment/<string:blog_title>', methods=["POST"])
@check_session
def addComments(blog_title):
    id = session.get('id')

    try:
        # Sử dụng with để quản lý kết nối và cursor
        with getDB() as (cursor, conn):
            commentContent = request.form.get('content')
            
            if not commentContent:
                return jsonify({"error": "Comment can't be empty"}), 400

            # Thêm comment vào bảng commentsBlog
            cursor.execute("INSERT INTO \"commentsBlog\" (title, username, comment) VALUES (?, ?, ?)", (blog_title, id, commentContent))
            conn.commit()

            return jsonify({"message": "Comment added successfully"}), 200
    except Exception as error:
        print(f"ERROR: {error}", flush=True)
        return jsonify({"error": "Internal Server Error"}), 500


@app.route('/user/<string:user_id>', methods=["GET", "POST"])
@check_session
def viewProfile(user_id):
    id = session.get('id')

    if not id:
        return redirect(url_for('login'))  # Redirect nếu không có session hợp lệ

    decoded_id = unquote(user_id)

    try:
        # Sử dụng with để quản lý kết nối và cursor
        with getDB() as (cursor, conn):
            # Lấy thông tin người dùng từ cơ sở dữ liệu
            user_info = cursor.execute("SELECT name, username, \"emailAddr\" FROM user WHERE id = ?", (decoded_id,)).fetchone()
            if user_info:
                name, username, emailAddr = user_info
                
                # Lấy tất cả các blog đã xuất bản của người dùng
                all_blogs = cursor.execute("SELECT title, likes FROM \"blogPosts\" WHERE userID = ? AND publish = 1", (decoded_id,)).fetchall()

                if not all_blogs:
                    return render_template("userProfile.html", all_blogs=[], name=name, username=username, emailAddr=emailAddr, message="No blogs found")
                else:
                    return render_template("userProfile.html", all_blogs=all_blogs, name=name, username=username, emailAddr=emailAddr)
            else:
                return jsonify({"error": "User not found"}), 404
    except Exception as error:
        print(f"ERROR: {error}", flush=True)
        return jsonify({"error": "Internal Server Error"}), 500


# Date formatting filter
@app.template_filter("ftime")
def ftime(date):
    if isinstance(date, str):
        return date

    try:
        dt = datetime.fromtimestamp(int(date))
    except ValueError:
        return str(date)
    
    time_format = "%I:%M %p"
    formatted_time = dt.strftime(time_format)
    formatted_time += " | " + dt.strftime("%m/%d")
    return formatted_time
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
