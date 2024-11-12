import os
from datetime import datetime

from flask import Flask, redirect, render_template, request, send_from_directory, url_for
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from functools import wraps

app = Flask(__name__, static_folder='static')
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

def check_session(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Register route
@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""
    if request.method == "POST":
        emailAddr = request.form['email'].strip()
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        if len(password) < 6:
            flash("Password must be at least 6 characters.")
            return render_template("register.html", message=message)

        cursor, conn = getDB()
        rows = cursor.execute("SELECT username FROM user WHERE emailAddr = ?", (emailAddr,)).fetchall()

        if rows:
            message = "User already exists"
        else:
            id = str(uuid.uuid4())
            hashed_password = generate_password_hash(password)
            session['loggedin'] = True
            session['id'] = id

            query = "INSERT INTO user (id, username, emailAddr, password) VALUES (?, ?, ?, ?)"
            cursor.execute(query, (id, username, emailAddr, hashed_password))
            conn.commit()
            return redirect('/home')
    return render_template("register.html", message=message)


# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    try:
        if request.method == "POST":
            emailAddr = request.form['email'].strip()
            password = request.form['password'].strip()

            cursor, conn = getDB()
            user_info = cursor.execute("SELECT id, password FROM user WHERE emailAddr = ?", (emailAddr,)).fetchone()

            if user_info:
                id, hashed_password = user_info
                if check_password_hash(hashed_password, password):
                    session['loggedin'] = True
                    session['id'] = id
                    return redirect('/home')   
                else:
                    message = "Wrong Email or Password"
                    return render_template('login.html', message=message)
            else:
                message = "Wrong Email or Password"
                return render_template('login.html', message=message)
    except Exception as error:
        print(f"ERROR: {error}", flush=True)
    return render_template("login.html")


# Home route
@app.route("/")
@app.route("/home")
@check_session
def home():
    cursor, conn = getDB()
    id = session['id']
    profile_pic, data = None, []

    cursor.execute("SELECT id FROM user WHERE id = ?", (id,)).fetchone()
    if id:        
        count_noti = cursor.execute("SELECT count(*) from notification where myid = ?", (id,)).fetchone()
        count_noti_chat = cursor.execute("SELECT count(*) from notification where myid = ? and ischat = 1", (id,)).fetchone()
        
        blog_info = cursor.execute("SELECT title, content FROM blogPosts WHERE publish = 1 ORDER BY RANDOM() LIMIT 5").fetchall()
        user_info = cursor.execute("SELECT username FROM user WHERE id = ?", (id,)).fetchone()
        
        avatar_path = os.path.join(app.config['UPLOAD_FOLDER'], id, 'avatar.jpg')
        if os.path.exists(avatar_path):
            profile_pic = id + '/avatar.jpg'
        if profile_pic is None:
            profile_pic = os.path.join("", "../../img/avatar.jpg")
        
        noti_list = cursor.execute("SELECT myid, content, timestamp, from_id, ischat from notification where myid = ?", (id,)).fetchall()
        if noti_list:
            for noti in noti_list:
                myid, content, timestamp, fromid, ischat = noti
                sender_name = cursor.execute("SELECT username from user where id = ?", (fromid,)).fetchone()
                sender_ava_path = os.path.join(app.config['UPLOAD_FOLDER'], fromid, 'avatar.jpg')
                sender_pic = fromid + '/avatar.jpg' if os.path.exists(sender_ava_path) else os.path.join("", "../../img/avatar.jpg")
                rid = cursor.execute("SELECT id FROM chat WHERE (userID1 = ? AND userID2 = ?) OR (userID1= ? AND userID2 = ?)", (id, fromid, fromid, id)).fetchall()
                
                data.append({
                    "myid": myid,
                    "fromid": fromid,
                    "fromname": sender_name,
                    "content": content,
                    "time": timestamp,
                    "sender_pic": sender_pic,
                    "ischat": ischat,
                    "rid": rid if rid else None
                })
        
        return render_template('index.html', blog_info=blog_info, user_info=user_info, profile_pic=profile_pic, myid=id, data=data, count_noti=count_noti, count_noti_chat=count_noti_chat)
    return redirect('/login')


# Profile route
@app.route('/profile')
@check_session
def profile():
    cursor, conn = getDB()
    id = session['id']
    profile_pic = None

    cursor.execute("SELECT id FROM user WHERE id = ?", (id,)).fetchone()
    if id:   
        blog_count = cursor.execute("SELECT COUNT(*) FROM blogPosts WHERE userID = ?", (id,)).fetchone()[0]
        username = cursor.execute("SELECT username FROM user WHERE id = ?", (id,)).fetchone()[0]
        blog_info = cursor.execute("SELECT id, title, content, authorname, publish FROM blogPosts WHERE userID = ?", (id,)).fetchall()
        published_blogs = cursor.execute("SELECT id, title, authorname, publish FROM blogPosts WHERE userID = ? and publish = 1", (id,)).fetchall()
        
        liked_blogs_title = cursor.execute("SELECT title FROM likedBlogs WHERE liked =  1 and userID = ?", (id,)).fetchall()
        total_blog = []
        for title_blog in liked_blogs_title:
            final_title = title_blog[0]
            liked_blogs = cursor.execute("SELECT id, title, authorname, publish FROM blogPosts WHERE title = ?", (final_title,)).fetchall()
            total_blog += liked_blogs

        avatar_path = os.path.join(app.config['UPLOAD_FOLDER'], id, 'avatar.jpg')
        if os.path.exists(avatar_path):
            profile_pic = id + '/avatar.jpg'
        if profile_pic is None:
            profile_pic = os.path.join("", "../../img/avatar.jpg")

        return render_template('profile.html', username=username, blog_info=blog_info, profile_pic=profile_pic, published_blogs=published_blogs, blog_count=blog_count, liked_blogs=total_blog)
    return redirect('/login')


# Settings user information route
@app.route('/settings', methods=["GET", "POST"])
@check_session
def settings():
    id = session.get('id')
    cursor, conn = getDB()
    
    cursor.execute("SELECT id FROM user WHERE id = ?", (id,)).fetchone()
    if not id:        
        return redirect(url_for('login'))

    user_info = cursor.execute("SELECT name, username, emailAddr, password FROM user WHERE id = ?", (id,)).fetchone()
    name, username, emailAddr, hashed_password = user_info
    profile_pic = None

    if request.method == "POST":
        if 'name' in request.form:
            new_name = request.form['name']
            cursor.execute("UPDATE user SET name = ? WHERE id = ?", (new_name, id))
            conn.commit()
            name = new_name

        if 'username' in request.form:
            new_username = request.form['username']
            cursor.execute("UPDATE user SET username = ? WHERE id = ?", (new_username, id))
            conn.commit()
            username = new_username

        if 'email' in request.form:
            new_email = request.form['email']
            cursor.execute("UPDATE user SET emailAddr = ? WHERE id = ?", (new_email, id))
            conn.commit()
            emailAddr = new_email   

        if 'password' in request.form:
            new_password = request.form['password']
            if new_password and not check_password_hash(hashed_password, new_password):
                new_hashed_password = generate_password_hash(new_password)
                cursor.execute("UPDATE user SET password = ? WHERE id = ?", (new_hashed_password, id))
                conn.commit()

    avatar_path = os.path.join(app.config['UPLOAD_FOLDER'], id, 'avatar.jpg')
    if os.path.exists(avatar_path):
        profile_pic = id + '/avatar.jpg'
    if profile_pic is None:
        profile_pic = os.path.join("", "../../img/avatar.jpg")

    return render_template('settings.html', name=name, username=username, email=emailAddr, profile_pic=profile_pic)
# Logout route
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    return redirect('/login')


# Create blog route
@app.route("/save_blog", methods=["GET", "POST"])
@check_session
def save_blog():
    id = session.get('id')
    cursor, conn = getDB()
    
    # Kiểm tra xem id có tồn tại trong cơ sở dữ liệu không
    cursor.execute("SELECT id FROM user WHERE id = ?", (id,)).fetchone()
    if not id:        
        return redirect(url_for('login'))

    # Lấy thông tin người dùng từ cơ sở dữ liệu
    user_info = cursor.execute("SELECT id, username FROM user WHERE id = ?", (id,)).fetchone()
    username = user_info[1]

    if request.method == "POST":
        try:
            blogTitle = request.json.get('blogTitle')
            blogContent = request.json.get('blogContent')

            if blogTitle and blogContent:
                # Thêm blog mới vào cơ sở dữ liệu
                cursor.execute(
                    "INSERT INTO blogPosts (userID, title, content, authorname) VALUES (?, ?, ?, ?)",
                    (id, blogTitle, blogContent, username)
                )
                conn.commit()
                return "Blog successfully uploaded!"
            else:
                return "Missing blog title or content", 400
        except Exception as error:
            print(f"ERROR: {error}", flush=True)
            return "Server error occurred", 500
    return None


# Delete blog route
@app.route("/delete_blog", methods=["POST"])
@check_session
def delete_blog():
    id = session.get("id")
    cursor, conn = getDB()

    # Kiểm tra id người dùng
    cursor.execute("SELECT id FROM user WHERE id = ?", (id,)).fetchone()
    if not id:        
        return redirect(url_for('login'))

    try:
        blog_id = request.form.get('blog_id')
        cursor.execute("DELETE FROM blogPosts WHERE id = ?", (blog_id,))
        conn.commit()
        return redirect(url_for('profile'))
    except Exception as error:
        print(f"ERROR: {error}", flush=True)
        return "Internal Server Error", 500


# Update blog publish status
@app.route("/update_published", methods=["POST"])
@check_session
def published():
    id = session.get('id')
    cursor, conn = getDB()

    cursor.execute("SELECT id FROM user WHERE id = ?", (id,)).fetchone()
    if not id:        
        return redirect(url_for('login'))

    try:
        blogID = request.json.get('blogID')
        published = request.json.get('published')

        cursor.execute("UPDATE blogPosts SET publish = ? WHERE id = ?", (published, blogID))
        conn.commit()
        return 'Updated'
    except Exception as error:
        print(f"ERROR: {error}", flush=True)
        return "Server error occurred", 500


# View individual blog
@app.route('/blog/<string:blog_title>')
@check_session
def view_blog(blog_title):
    id = session.get('id')
    cursor, conn = getDB()

    cursor.execute("SELECT id FROM user WHERE id = ?", (id,)).fetchone()
    if not id:        
        return redirect(url_for('login'))

    decode_title = unquote(blog_title)
    blog_post = cursor.execute(
        "SELECT title, content, likes, authorname, userID FROM blogPosts WHERE title = ? AND publish = 1",
        (decode_title,)
    ).fetchone()

    if blog_post:
        title, content, likes, authorname, userID = blog_post
        comment_content = cursor.execute(
            "SELECT username, comment FROM commentsBlog WHERE title = ?", (decode_title,)
        ).fetchall()
        liked = cursor.execute(
            "SELECT liked FROM likedBlogs WHERE title = ? AND userID = ?", (decode_title, id)
        ).fetchone()
        liked = liked[0] if liked else 0

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


# Create new chat
@app.route('/new_chat', methods=["POST"])
@check_session
def new_chat():
    id = session.get('id')
    cursor, conn = getDB()

    cursor.execute("SELECT id FROM user WHERE id = ?", (id,)).fetchone()
    if not id:        
        return redirect(url_for('login'))

    try:
        search_input = request.form.get('search_input')
        invite_input = request.form.get('invite_input')

        if search_input:
            # Kiểm tra định dạng email hoặc username
            if re.match(r'^[\w\.-]+@[\w\.-]+$', search_input):
                recipient_info = cursor.execute(
                    "SELECT id, username, emailAddr FROM user WHERE emailAddr = ?", (search_input,)
                ).fetchone()
            else:
                recipient_info = cursor.execute(
                    "SELECT id, username, emailAddr FROM user WHERE username = ?", (search_input,)
                ).fetchone()

            if recipient_info:
                recipient_id, recipient_username, recipient_email = recipient_info
                chat_exists = cursor.execute(
                    "SELECT id FROM chat WHERE (userID1 = ? AND userID2 = ?) OR (userID1 = ? AND userID2 = ?)",
                    (id, recipient_id, recipient_id, id)
                ).fetchone()
                if chat_exists:
                    return jsonify({'error': 'Chat already exists'}), 400
                else:
                    notification_check = cursor.execute(
                        "SELECT * FROM notification WHERE myid = ? AND from_id = ?", (recipient_id, id)
                    ).fetchone()
                    if notification_check:
                        return jsonify({'error': 'You are already invited', 'chat_id': recipient_id, 'content': invite_input}), 404
                    else:
                        chat_id = str(uuid.uuid4())
                        cursor.execute(
                            "INSERT INTO chat (id, userID1, userID2) VALUES (?, ?, ?)", (chat_id, id, recipient_id)
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

@app.route('/deletenoti', methods=["POST"])
@check_session
def deletenoti():
    id = session.get('id')
    cursor, conn = getDB()
    
    # Ensure the user exists in the database
    cursor.execute("SELECT id FROM user WHERE id = ?", (id,))
    if not cursor.fetchone():        
        return redirect(url_for('login'))  # Redirect if user does not exist

    try:
        data = request.data.decode('utf-8')  
        data_dict = json.loads(data)  

        if 'fromid' in data_dict and 'toid' in data_dict:
            fromid = data_dict['fromid']
            toid = data_dict['toid']

            recipient_info = cursor.execute("SELECT id FROM user WHERE id = ?", (toid,)).fetchone()
            if recipient_info:
                cursor.execute("DELETE FROM notification WHERE myid = ? AND from_id = ?", (id, fromid))
                conn.commit()
            else:
                return jsonify({'error': 'User not found'}), 404
        return jsonify({'success': 'Notification deleted'}), 200
    except Exception as error:
        print(f"ERROR: {error}", flush=True)
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/accept', methods=["POST"])
@check_session
def accept():
    id = session.get('id')
    cursor, conn = getDB()
    
    # Ensure the user exists in the database
    cursor.execute("SELECT id FROM user WHERE id = ?", (id,))
    if not cursor.fetchone():        
        return redirect(url_for('login'))  # Redirect if user does not exist

    try:
        data = request.data.decode('utf-8')  
        data_dict = json.loads(data)

        if 'data' in data_dict:
            senderid = data_dict['data']
            # Search for the user in the database based on email or username
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
                    cursor.execute("INSERT INTO chat (id, userID1, userID2) VALUES (?, ?, ?)", (chat_id, id, recipient_id))
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
    cursor, conn = getDB()

    try:
        post_title = request.form.get('post_title')
        action = request.form.get('action')
        like_unlike = 1 if action == "like" else 0

        blog_and_user_existed = cursor.execute("SELECT * FROM likedBlogs WHERE title = ? AND userID = ?", (post_title, id)).fetchone()

        if blog_and_user_existed:
            cursor.execute("UPDATE likedBlogs SET liked = ? WHERE title = ? AND userID = ?", (like_unlike, post_title, id))
        else:
            cursor.execute("INSERT INTO likedBlogs (title, userID, liked) VALUES (?, ?, ?)", (post_title, id, like_unlike))

        conn.commit()
        return jsonify({"message": "Likes updated successfully"}), 200
    except Exception as error:
        print(f"ERROR: {error}", flush=True)
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/addComment/<string:blog_title>', methods=["POST"])
@check_session
def addComments(blog_title):
    id = session.get('id')
    cursor, conn = getDB()

    try:
        commentContent = request.form.get('content')
        if not commentContent:
            return jsonify({"error": "Comment can't be empty"}), 400

        cursor.execute("INSERT INTO commentsBlog (title, username, comment) VALUES (?, ?, ?)", (blog_title, id, commentContent))
        conn.commit()
        return jsonify({"message": "Comment added successfully"}), 200
    except Exception as error:
        print(f"ERROR: {error}", flush=True)
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/user/<string:user_id>', methods=["GET", "POST"])
@check_session
def viewProfile(user_id):
    id = session.get('id')
    cursor, conn = getDB()

    decoded_id = unquote(user_id)

    try:
        user_info = cursor.execute("SELECT name, username, emailAddr FROM user WHERE id = ?", (decoded_id,)).fetchone()
        if user_info:
            name, username, emailAddr = user_info
            all_blogs = cursor.execute("SELECT title, likes FROM blogPosts WHERE userID = ? AND publish = 1", (decoded_id,)).fetchall()

            if not all_blogs:
                return "No blogs found"
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
    app.run()
