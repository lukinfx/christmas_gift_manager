import streamlit as st
import json
import os
import ssl
import certifi
import httpx
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Disable SSL warnings for development
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
warnings.filterwarnings('ignore', category=DeprecationWarning)

# Monkey patch httpx to disable SSL verification for development
# This is needed because supabase-py doesn't expose SSL configuration
original_client_init = httpx.Client.__init__

def patched_client_init(self, *args, **kwargs):
    kwargs['verify'] = False
    original_client_init(self, *args, **kwargs)

httpx.Client.__init__ = patched_client_init

# Initialize Supabase client
@st.cache_resource
def init_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        st.error("Please set SUPABASE_URL and SUPABASE_KEY in .env file")
        st.stop()
    
    return create_client(
        supabase_url=url,
        supabase_key=key
    )

supabase = init_supabase()

# Load users from JSON
@st.cache_data
def load_users():
    with open('users.json', 'r') as f:
        return json.load(f)['users']

# Authentication
def authenticate(username, password):
    users = load_users()
    for user in users:
        if user['username'] == username and user['password'] == password:
            return user
    return None

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user' not in st.session_state:
    st.session_state.user = None

# Database functions
def get_all_lists():
    """Get all gift lists"""
    result = supabase.table('gift_lists').select('*').order('created_at', desc=True).execute()
    return result.data

def get_gifts_for_list(list_id, current_user):
    """Get gifts for a specific list, filtered by visibility rules"""
    result = supabase.table('gifts').select('*').eq('list_id', list_id).order('created_at', desc=False).execute()
    gifts = result.data
    
    # Get the list to check recipients
    list_result = supabase.table('gift_lists').select('*').eq('id', list_id).execute()
    if not list_result.data:
        return []
    
    gift_list = list_result.data[0]
    recipients = gift_list.get('recipients', [])
    
    # If user is in recipients, only show gifts they added
    if current_user in recipients:
        return [g for g in gifts if g['added_by'] == current_user]
    
    # If user is not in recipients, show all gifts
    return gifts

def create_gift_list(name, recipients, created_by):
    """Create a new gift list"""
    data = {
        'name': name,
        'recipients': recipients,
        'created_by': created_by,
        'created_at': datetime.now().isoformat()
    }
    result = supabase.table('gift_lists').insert(data).execute()
    return result.data

def add_gift_to_list(list_id, gift_name, description, added_by):
    """Add a gift to a list"""
    data = {
        'list_id': list_id,
        'name': gift_name,
        'description': description,
        'added_by': added_by,
        'status': 'available',
        'created_at': datetime.now().isoformat()
    }
    result = supabase.table('gifts').insert(data).execute()
    return result.data

def update_gift_status(gift_id, status, user):
    """Update gift status"""
    data = {'status': status}
    if status in ['want_to_buy', 'want_to_buy_shared']:
        data['interested_buyer'] = user
    elif status == 'bought':
        data['bought_by'] = user
        data['bought_at'] = datetime.now().isoformat()
    
    result = supabase.table('gifts').update(data).eq('id', gift_id).execute()
    return result.data

def add_comment_to_gift(gift_id, comment, user):
    """Add a comment to a gift"""
    data = {
        'gift_id': gift_id,
        'comment': comment,
        'username': user,
        'created_at': datetime.now().isoformat()
    }
    result = supabase.table('gift_comments').insert(data).execute()
    return result.data

def get_comments_for_gift(gift_id):
    """Get all comments for a gift"""
    result = supabase.table('gift_comments').select('*').eq('gift_id', gift_id).order('created_at', desc=False).execute()
    return result.data

# Login page
def login_page():
    st.title("� Christmas Gift Manager")
    st.subheader("Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            user = authenticate(username, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Invalid username or password")

# Main app
def main_app():
    st.title(f"🎄 Christmas Gift Manager - Welcome {st.session_state.user['display_name']}!")
    
    # Sidebar
    with st.sidebar:
        st.write(f"Logged in as: **{st.session_state.user['display_name']}**")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()
        
        st.divider()
        st.subheader("Create New Gift List")
        
        with st.form("create_list_form"):
            list_name = st.text_input("List Name")
            
            # Get all users for recipient selection
            all_users = load_users()
            user_options = [u['username'] for u in all_users]
            recipients = st.multiselect("Recipients", user_options)
            
            if st.form_submit_button("Create List"):
                if list_name and recipients:
                    create_gift_list(list_name, recipients, st.session_state.user['username'])
                    st.success("List created!")
                    st.rerun()
                else:
                    st.error("Please fill all fields")
    
    # Main content
    lists = get_all_lists()
    
    if not lists:
        st.info("No gift lists yet. Create one using the sidebar!")
        return
    
    # Display all lists
    for gift_list in lists:
        with st.expander(f"🎁 {gift_list['name']} (Recipients: {', '.join(gift_list['recipients'])})", expanded=False):
            current_user = st.session_state.user['username']
            recipients = gift_list.get('recipients', [])
            is_recipient = current_user in recipients
            
            # Show info about visibility
            if is_recipient:
                st.info(f"ℹ️ You're a recipient! You can add gifts you wish to receive, but you'll only see your own gifts.")
            else:
                st.success(f"✅ You can add gifts for the recipients and see all gifts to mark their status.")
            
            # Add gift section - everyone can add gifts
            with st.form(f"add_gift_{gift_list['id']}"):
                st.write("**Add a Gift**")
                col1, col2 = st.columns([2, 1])
                with col1:
                    gift_name = st.text_input("Gift Name", key=f"gift_name_{gift_list['id']}")
                with col2:
                    gift_desc = st.text_input("Description (optional)", key=f"gift_desc_{gift_list['id']}")
                
                if st.form_submit_button("Add Gift"):
                    if gift_name:
                        add_gift_to_list(gift_list['id'], gift_name, gift_desc, current_user)
                        st.success("Gift added!")
                        st.rerun()
                    else:
                        st.error("Please enter a gift name")
            
            # Display gifts
            gifts = get_gifts_for_list(gift_list['id'], current_user)
            
            if not gifts:
                st.write("No gifts in this list yet.")
            else:
                for gift in gifts:
                    with st.container():
                        st.divider()
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.markdown(f"### {gift['name']}")
                            if gift.get('description'):
                                st.write(f"*{gift['description']}*")
                            st.caption(f"Added by: {gift['added_by']}")
                        
                        with col2:
                            # Status badge (only visible to non-recipients)
                            if not is_recipient:
                                status = gift.get('status', 'available')
                                if status == 'available':
                                    st.success("Available")
                                elif status == 'want_to_buy':
                                    st.warning(f"Reserved by {gift.get('interested_buyer', 'someone')}")
                                elif status == 'want_to_buy_shared':
                                    st.info(f"Shared buy by {gift.get('interested_buyer', 'someone')}")
                                elif status == 'bought':
                                    st.error(f"Bought by {gift.get('bought_by', 'someone')}")
                        
                        # Actions (only for non-recipients)
                        if not is_recipient:
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button("Want to Buy", key=f"buy_{gift['id']}", use_container_width=True):
                                    update_gift_status(gift['id'], 'want_to_buy', current_user)
                                    st.rerun()
                            with col2:
                                if st.button("Buy Shared", key=f"shared_{gift['id']}", use_container_width=True):
                                    update_gift_status(gift['id'], 'want_to_buy_shared', current_user)
                                    st.rerun()
                            with col3:
                                if st.button("Mark Bought", key=f"bought_{gift['id']}", use_container_width=True):
                                    update_gift_status(gift['id'], 'bought', current_user)
                                    st.rerun()
                        
                        # Comments section (only visible to non-recipients)
                        if not is_recipient:
                            st.markdown("**Comments:**")
                            comments = get_comments_for_gift(gift['id'])
                            
                            if comments:
                                for comment in comments:
                                    st.text(f"{comment['username']} ({comment['created_at'][:10]}): {comment['comment']}")
                            
                            # Add comment
                            with st.form(f"comment_{gift['id']}"):
                                new_comment = st.text_input("Add a comment", key=f"new_comment_{gift['id']}")
                                if st.form_submit_button("Post Comment"):
                                    if new_comment:
                                        add_comment_to_gift(gift['id'], new_comment, current_user)
                                        st.success("Comment added!")
                                        st.rerun()

# Main execution
if st.session_state.logged_in:
    main_app()
else:
    login_page()
