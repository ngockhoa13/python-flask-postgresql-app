"""Initial migration for creating tables for blog and chat system.

Revision ID: <your_revision_id>
Revises: 
Create Date: <timestamp>
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 7e6556f5dc0c
down_revision = None  # Set previous migration ID if any
branch_labels = None
depends_on = None

def upgrade():
    # Create 'user' table
    op.create_table('user',
        sa.Column('id', sa.String(36), primary_key=True, unique=True, nullable=False),
        sa.Column('name', sa.String(20), nullable=True),
        sa.Column('username', sa.String(20), nullable=False),
        sa.Column('emailAddr', sa.String(150), unique=True, nullable=False),
        sa.Column('password', sa.String(60), nullable=False),
    )

    # Create 'blogPosts' table with 'title' as unique
    op.create_table('blogPosts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('userID', sa.String(36), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('authorname', sa.String(20), nullable=True),
        sa.Column('title', sa.String(100), unique=True, nullable=False),  # 'title' added as unique
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('imagepath', sa.String(255), nullable=True),
        sa.Column('publish', sa.Boolean(), default=False),
        sa.Column('likes', sa.Integer(), default=0),
    )

    # Create 'commentsBlog' table
    op.create_table('commentsBlog',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('title', sa.Integer(), sa.ForeignKey('blogPosts.id'), nullable=False),
        sa.Column('username', sa.String(20), nullable=True),
        sa.Column('comment', sa.Text(), nullable=False),
    )

    # Create 'chat' table
    op.create_table('chat',
        sa.Column('id', sa.String(36), primary_key=True, unique=True, nullable=False),
        sa.Column('userID1', sa.String(36), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('userID2', sa.String(36), sa.ForeignKey('user.id'), nullable=False),
    )

    # Create 'messages' table with unique constraint on 'room_id'
    op.create_table('messages',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('room_id', sa.String(50), unique=True, nullable=False),
    )

    # Create 'chat_messages' table with foreign key reference to 'messages.room_id'
    op.create_table('chat_messages',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.TIMESTAMP(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('sender_username', sa.String(50), nullable=False),
        sa.Column('room_id', sa.String(50), sa.ForeignKey('messages.room_id'), nullable=False),
    )

    # Create 'notification' table
    op.create_table('notification',
        sa.Column('count', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('myid', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.TIMESTAMP(), nullable=False),
        sa.Column('from_id', sa.String(50), nullable=False),
        sa.Column('ischat', sa.Boolean(), nullable=True),
    )

    # Create 'likedBlogs' table
    op.create_table('likedBlogs',
        sa.Column('title', sa.String(100), sa.ForeignKey('blogPosts.title', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.Column('userID', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True, nullable=False),
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
