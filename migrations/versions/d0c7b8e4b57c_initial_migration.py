"""Initial migration for creating tables for blog and chat system.

Revision ID: <your_revision_id>
Revises: 
Create Date: <timestamp>
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
import uuid
# revision identifiers, used by Alembic.
revision =  '<your_revision_id>'
down_revision = None  # Set previous migration ID if any
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)

    # Create 'user' table with UUID for 'id'
    op.create_table('user',
        sa.Column('id', sa.UUID(), primary_key=True, unique=True, nullable=False, default=uuid.uuid4),
        sa.Column('name', sa.String(20), nullable=True),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('emailAddr', sa.String(150), unique=True, nullable=False),
        sa.Column('password', sa.String(255), nullable=False),
    )

    # Create 'blogPosts' table with UUID for 'userID' and 'title' as unique
    op.create_table('blogPosts',
        sa.Column('id', sa.UUID(), primary_key=True, unique=True, nullable=False, default=uuid.uuid4),
        sa.Column('userID', sa.UUID(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=True),  # UUID
        sa.Column('authorname', sa.String(20), nullable=True),
        sa.Column('title', sa.String(100), unique=True, nullable=False),  # 'title' added as unique
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('imagepath', sa.String(255), nullable=True),
        sa.Column('publish', sa.Boolean(), default=False),
        sa.Column('likes', sa.Integer(), default=0),
    )

    # Create 'commentsBlog' table with UUID for 'userID' and 'blogPostID'
    op.create_table('commentsBlog',
        sa.Column('id', sa.UUID(), primary_key=True, unique=True, nullable=False, default=uuid.uuid4),  # UUID
        sa.Column('blogPostID', sa.UUID(), sa.ForeignKey('blogPosts.id', ondelete='CASCADE'), nullable=False),  # UUID
        sa.Column('username', sa.String(20), nullable=True),
        sa.Column('comment', sa.Text(), nullable=False),
    )

    # Create 'chat' table with UUID for 'userID1' and 'userID2'
    op.create_table('chat',
        sa.Column('id', sa.UUID(), primary_key=True, unique=True, nullable=False, default=uuid.uuid4),
        sa.Column('userID1', sa.UUID(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),  # UUID
        sa.Column('userID2', sa.UUID(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),  # UUID
    )

    # Create 'messages' table with UUID for 'room_id'
    op.create_table('messages',
        sa.Column('id', sa.UUID(), primary_key=True, unique=True, nullable=False, default=uuid.uuid4),
        sa.Column('room_id', sa.UUID(), unique=True, nullable=False),  # UUID
    )

    # Create 'chat_messages' table with UUID for 'room_id' and 'sender_id'
    op.create_table('chat_messages',
        sa.Column('id', sa.UUID(), primary_key=True, unique=True, nullable=False, default=uuid.uuid4),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.TIMESTAMP(), nullable=False),
        sa.Column('sender_id', sa.UUID(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),  # UUID
        sa.Column('sender_username', sa.String(50), nullable=False),
        sa.Column('room_id', sa.UUID(), sa.ForeignKey('messages.room_id', ondelete='CASCADE'), nullable=False),  # UUID
    )

    # Create 'notification' table with UUID for 'myid' and 'from_id'
    op.create_table('notification',
        sa.Column('count', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('myid', sa.UUID(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),  # UUID
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.TIMESTAMP(), nullable=False),
        sa.Column('from_id', sa.UUID(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),  # UUID
        sa.Column('ischat', sa.Boolean(), nullable=True),
    )

    # Create 'likedBlogs' table with UUID for 'userID' and 'title'
    op.create_table('likedBlogs',
        sa.Column('title', sa.String(100), sa.ForeignKey('blogPosts.title', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.Column('userID', sa.UUID(), sa.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True, nullable=False),  # UUID
        sa.Column('liked', sa.Boolean(), nullable=True),
    )

def downgrade():
    conn = op.get_bind()
    inspector = inspect(conn)

    # Drop 'likedBlogs' table if it exists
    if 'likedBlogs' in inspector.get_table_names():
        op.drop_table('likedBlogs')

    # Drop 'notification' table if it exists
    if 'notification' in inspector.get_table_names():
        op.drop_table('notification')

    # Drop 'chat_messages' table if it exists
    if 'chat_messages' in inspector.get_table_names():
        op.drop_table('chat_messages')

    # Drop 'messages' table if it exists
    if 'messages' in inspector.get_table_names():
        op.drop_table('messages')

    # Drop 'chat' table if it exists
    if 'chat' in inspector.get_table_names():
        op.drop_table('chat')

    # Drop 'commentsBlog' table if it exists
    if 'commentsBlog' in inspector.get_table_names():
        op.drop_table('commentsBlog')

    # Drop 'blogPosts' table if it exists
    if 'blogPosts' in inspector.get_table_names():
        op.drop_table('blogPosts')

    # Drop 'user' table if it exists
    if 'user' in inspector.get_table_names():
        op.drop_table('user')
