from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import validates
from sqlalchemy.orm import relationship  # Thêm dòng này
from app import db


class User(db.Model):
    __tablename__ = 'user'
    
    id = Column(String(36), primary_key=True, unique=True, nullable=False)
    name = Column(String(20))
    username = Column(String(20), nullable=False)
    emailAddr = Column(String(150), unique=True, nullable=False)
    password = Column(String(60), nullable=False)
    
    blog_posts = relationship("BlogPost", back_populates="user")
    liked_blogs = relationship("LikedBlog", back_populates="user")

    def __str__(self):
        return self.username

# Định nghĩa bảng BlogPost
class BlogPost(db.Model):
    __tablename__ = 'blogPosts'
    
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    userID = Column(String(36), ForeignKey("user.id"))
    authorname = Column(String(20))
    title = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    imagepath = Column(String(255))
    publish = Column(Boolean, default=False)
    likes = Column(Integer, default=0)
    
    user = relationship("User", back_populates="blog_posts")
    comments = relationship("Comment", back_populates="blog_post")
    liked_blogs = relationship("LikedBlog", back_populates="blog_post")

    def __str__(self):
        return self.title

# Định nghĩa bảng Comment
class Comment(db.Model):
    __tablename__ = 'commentsBlog'
    
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    title = Column(String(100), ForeignKey("blogPosts.title"), nullable=False)
    username = Column(String(20))
    comment = Column(Text, nullable=False)
    
    blog_post = relationship("BlogPost", back_populates="comments")

    def __str__(self):
        return f"{self.username}: {self.comment}"

# Định nghĩa bảng Chat
class Chat(db.Model):
    __tablename__ = 'chat'
    
    id = Column(String(36), primary_key=True, unique=True, nullable=False)
    userID1 = Column(String(36), ForeignKey("user.id"), nullable=False)
    userID2 = Column(String(36), ForeignKey("user.id"), nullable=False)

    def __str__(self):
        return f"Chat between {self.userID1} and {self.userID2}"

# Định nghĩa bảng Message
class Message(db.Model):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(String(50), ForeignKey("chat.id"), nullable=False)

    def __str__(self):
        return f"Message in chat room {self.room_id}"

# Định nghĩa bảng ChatMessage
class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP, nullable=False)
    sender_id = Column(Integer, nullable=False)
    sender_username = Column(String(50), nullable=False)
    room_id = Column(String(50), ForeignKey("messages.room_id"), nullable=False)

    def __str__(self):
        return f"{self.sender_username}: {self.content}"

# Định nghĩa bảng Notification
class Notification(db.Model):
    __tablename__ = 'notification'
    
    count = Column(Integer, primary_key=True, autoincrement=True)
    myid = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP, nullable=False)
    from_id = Column(String(50), nullable=False)
    ischat = Column(Boolean)

    def __str__(self):
        return f"Notification for user {self.myid}: {self.content}"

# Định nghĩa bảng LikedBlog
class LikedBlog(db.Model):
    __tablename__ = 'likedBlogs'
    
    title = Column(String(100), ForeignKey("blogPosts.title", ondelete="CASCADE"), primary_key=True, nullable=False)
    userID = Column(String(36), ForeignKey("user.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    liked = Column(Boolean)
    
    blog_post = relationship("BlogPost", back_populates="liked_blogs")
    user = relationship("User", back_populates="liked_blogs")

    def __str__(self):
        return f"User {self.userID} liked blog {self.title}"

# Hàm khởi tạo database (nếu cần thiết, thông qua SQLAlchemy)
def init_db():
    db.create_all()
