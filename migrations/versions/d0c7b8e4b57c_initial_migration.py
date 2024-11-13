"""Initial migration for creating tables for blog and chat system.

Revision ID: <your_revision_id>
Revises: 
Create Date: <timestamp>
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '<your_revision_id>'
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

    # Create 'blogPosts' table
    op.create_table('blogPosts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('userID', sa.String(36), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('authorname', sa.String(20), nullable=True),
        sa.Column('title', sa.String(100), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('imagepath', sa.String(255), nullable=True),
        sa.Column('publish', sa.Boolean(), server_default=sa.text('FALSE')),
        sa.Column('likes', sa.Integer(), server_default=sa.text('0')),
    )

    # Create 'commentsBlog' table with renamed column `post_id`
    op.create_table('commentsBlog',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('post_id', sa.Integer(), sa.ForeignKey('blogPosts.id'), nullable=False),
        sa.Column('username', sa.String(20), nullable=True),
        sa.Column('comment', sa.Text(), nullable=False),
    )

    # Create 'chat' table
    op.create_table('chat',
        sa.Column('id', sa.String(36), primary_key=True, unique=True, nullable=False),
        sa.Column('userID1', sa.String(36), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('userID2', sa.String(36), sa.ForeignKey('user.id'), nullable=False),
    )

    # Create 'messages' table
    op.create_table('messages',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('room_id', sa.String(50), sa.ForeignKey('chat.id'), nullable=False),
    )

    # Create 'chat_messages' table
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
    # Drop 'likedBlogs' table
    op.drop_table('likedBlogs')

    # Drop 'notification' table
    op.drop_table('notification')

    # Drop 'chat_messages' table
    op.drop_table('chat_messages')

    # Drop 'messages' table
    op.drop_table('messages')

    # Drop 'chat' table
    op.drop_table('chat')

    # Drop 'commentsBlog' table
    op.drop_table('commentsBlog')

    # Drop 'blogPosts' table
    op.drop_table('blogPosts')

    # Drop 'user' table
    op.drop_table('user')
