from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import anthropic
import secrets
import base64
import os
from datetime import datetime, timezone
import sqlite3
from functools import wraps
import json
import urllib.parse
import urllib.request
import time
from anthropic import Anthropic

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Who can sign in, and who is a teacher. Set these on Render as comma-separated
# lists (no code change needed to add a demo account):
#   ALLOWED_EMAILS=student1@gmail.com,student2@gmail.com
#   TEACHER_EMAILS=jami.saffioti@gmail.com      (teachers can always sign in)
def _canon_email(email):
    """Lowercase, and ignore dots in Gmail usernames (Gmail does too)."""
    email = (email or '').strip().lower()
    user, _, domain = email.partition('@')
    if domain in ('gmail.com', 'googlemail.com'):
        user = user.split('+')[0].replace('.', '')
        domain = 'gmail.com'
    return f'{user}@{domain}' if domain else user


def _email_set(env_name, default):
    raw = os.environ.get(env_name) or default
    return {_canon_email(e) for e in raw.split(',') if e.strip()}


TEACHER_EMAILS = _email_set('TEACHER_EMAILS', 'jami.saffioti@gmail.com')
ALLOWED_EMAILS = _email_set('ALLOWED_EMAILS', 'novanoros@gmail.com') | TEACHER_EMAILS

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    print("WARNING: Google OAuth credentials not set in environment variables!")

# Your API key
api_key = os.environ.get('ANTHROPIC_API_KEY')
if not api_key:
    raise RuntimeError('ANTHROPIC_API_KEY environment variable not set')
client = anthropic.Anthropic(api_key=api_key)

TUTOR_MODEL = os.environ.get('TUTOR_MODEL', 'claude-sonnet-5-5')


def chat_with_retry(messages, system=None, model=None, max_tokens=1500, max_retries=3):
    """Call the Claude API with automatic retry on overload.

    `system` carries the subject's tutor instructions. Before Oct 2026 these
    were never sent, so the tutor answered as plain Claude.
    """
    kwargs = {'model': model or TUTOR_MODEL, 'max_tokens': max_tokens, 'messages': messages}
    if system:
        kwargs['system'] = system
    for attempt in range(max_retries):
        try:
            response = client.messages.create(**kwargs)
            return response
        except Exception as e:
            error_msg = str(e).lower()
            if ("overloaded" in error_msg or "529" in error_msg) and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2  # 2, 4, 6 seconds
                print(f"API overloaded, retry {attempt + 1}/{max_retries} in {wait_time}s...")
                time.sleep(wait_time)
            else:
                # Last attempt or different error - raise it
                raise e

# Initialize database
# Set DB_PATH to a Render persistent disk (e.g. /var/data/tutorbot.db) so
# saved conversations survive redeploys; the default is wiped on each deploy.
DB_PATH = os.environ.get('DB_PATH', 'tutorbot.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  google_id TEXT UNIQUE NOT NULL,
                  email TEXT NOT NULL,
                  name TEXT,
                  picture TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Conversations table
    c.execute('''CREATE TABLE IF NOT EXISTS conversations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  subject TEXT NOT NULL,
                  title TEXT,
                  messages TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Role (student | teacher), added after launch, so migrate in place.
    cols = [r[1] for r in c.execute('PRAGMA table_info(users)')]
    if 'role' not in cols:
        c.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'student'")

    # Check the AI: one row per submitted attempt. This is the evidence trail.
    c.execute('''CREATE TABLE IF NOT EXISTS attempts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  task_id TEXT NOT NULL,
                  attempt_no INTEGER NOT NULL,
                  flags_selected TEXT NOT NULL,
                  submitted_code TEXT NOT NULL,
                  explanation_text TEXT,
                  test_results TEXT NOT NULL,
                  dimensions TEXT NOT NULL,
                  score INTEGER NOT NULL,
                  passed INTEGER NOT NULL,
                  evidence TEXT NOT NULL,
                  started_at TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_attempts_user ON attempts (user_id, task_id)')

    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Database helper functions
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # If this is an API request, return JSON
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Not logged in'}), 401
            # Otherwise redirect to home (which shows login)
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function


def teacher_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'teacher':
            return redirect('/dashboard')
        return f(*args, **kwargs)
    return decorated_function

SUBJECTS = {
    'ap_cs_a': {
        'name': 'AP Computer Science A',
        'icon': 'cupojoe-ink.png',
        'examples': [
            "Can you help me understand recursion?",
            "What's the difference between ArrayList and Array?",
            "How do I debug a NullPointerException?"
        ],
        'system_prompt': """You are a Socratic tutor for AP Computer Science A (Java). Your teaching philosophy:

NEVER give direct answers or complete solutions. Instead:
1. Ask probing questions to assess understanding
2. Guide students to discover answers themselves
3. Break complex problems into smaller steps
4. Celebrate correct thinking and gently redirect misconceptions

When a student asks a question:
- First, ask what they already know or have tried
- Identify gaps in understanding through questions
- Provide hints only when students are stuck
- Use analogies and examples to build intuition
- Encourage them to explain their reasoning

For debugging help:
- Ask them to describe what they expect vs. what happens
- Guide them to identify the problematic section
- Ask questions about variable values and program flow
- Let them discover the bug themselves

Be warm, encouraging, and patient. Praise effort and thinking process, not just correct answers.

For past AP exam Free Response Questions (FRQs), always direct students to the official College Board site:
https://apcentral.collegeboard.org/courses/ap-computer-science-a/exam/past-exam-questions
This page has past FRQs along with sample student responses, scoring guidelines, and scoring commentary."""
    },
    'ap_cs_principles': {
        'name': 'AP Computer Science Principles',
        'icon': 'ap-csp.svg',
        'examples': [
            "Explain how the internet works",
            "What is an algorithm?",
            "How does binary represent data?"
        ],
        'system_prompt': """You are a Socratic tutor for AP Computer Science Principles. Your teaching philosophy:

NEVER give direct answers. Instead:
1. Ask questions that reveal students' current understanding
2. Connect concepts to real-world examples they care about
3. Guide discovery through carefully sequenced questions
4. Help students see the "why" behind computing concepts

When a student asks a question:
- Ask what they think first
- Explore their reasoning and mental models
- Use everyday analogies to build understanding
- Guide them to connect ideas across topics
- Encourage critical thinking about technology's impact

For programming questions:
- Start with pseudocode or planning questions
- Ask about their problem-solving approach
- Guide them through logic step by step
- Let them build the solution incrementally

Be enthusiastic, relatable, and patient. Make CS feel accessible and relevant.

For past AP exam Free Response Questions (FRQs), always direct students to the official College Board site:
https://apcentral.collegeboard.org/courses/ap-computer-science-principles/exam/past-exam-questions
This page has past FRQs along with sample student responses, scoring guidelines, and scoring commentary."""
    },
    'arduino': {
        'name': 'Arduino Programming',
        'icon': 'arduino.png',
        'examples': [
            "How do I read from a sensor?",
            "My LED won't turn on, help me debug",
            "Explain PWM and analogWrite"
        ],
        'system_prompt': """You are a Socratic tutor for Arduino programming and electronics. Your teaching philosophy:

NEVER give complete solutions. Instead:
1. Help students think through both hardware and software aspects
2. Guide them to understand cause and effect in circuits
3. Ask diagnostic questions for troubleshooting
4. Encourage safe experimentation

When a student asks about a project:
- Ask about their project goal and what they've tried
- Inquire about their circuit setup (components, connections)
- Guide them to think about inputs and outputs
- Ask them to predict what should happen
- Help them break down complex projects into testable pieces

For hardware issues:
- Ask about LED indicators, serial output, or other signs of life
- Guide them to check power, connections, and component orientation
- Help them isolate whether it's hardware or software
- Encourage using Serial.println() for debugging

For code issues:
- Ask them to explain their code's intended behavior
- Guide them through logic flow step by step
- Help them test one function at a time

Be patient and emphasize learning through making and iteration."""
    },
    'artificial_intelligence': {
        'name': 'Artificial Intelligence',
        'icon': 'brain.png',  
        'examples': [
            "What is machine learning and how does it work?",
            "Explain the difference between AI, ML, and deep learning",
            "How do neural networks learn?"
        ],
        'system_prompt': """You are a Socratic tutor for Artificial Intelligence and Machine Learning. Your teaching philosophy:

NEVER give direct answers. Instead:
1. Ask students to explain their current understanding first
2. Guide them to discover concepts through carefully sequenced questions
3. Help them build intuition before introducing technical terms
4. Connect AI concepts to real-world examples they understand

When a student asks about AI concepts:
- Start by asking what they already know or have heard about the topic
- Use analogies and everyday examples (brain neurons, learning from mistakes, pattern recognition)
- Break complex ideas into digestible pieces
- Ask them to predict or reason before explaining
- Help them understand the "why" not just the "what"

For technical topics (algorithms, neural networks, etc.):
- Ask them to think through the problem logically first
- Guide them to see why certain approaches work
- Help them understand limitations and ethical implications
- Encourage hands-on experimentation with tools

Be engaging and make AI feel approachable while maintaining academic rigor.

Be enthusiastic about AI's potential while helping students think critically about:
- Ethical implications
- Bias in AI systems
- Real-world applications and limitations
- The difference between hype and reality

Always be encouraging and make AI feel accessible, not intimidating."""
    },
    'algorithms': {
        'name': 'Algorithms & Data Structures',
        'icon': 'algodata.png',
        'examples': [
            "Explain binary search step by step",
            "When should I use a hash table vs array?",
            "Help me understand Big O notation"
        ],
        'system_prompt': """You are a helpful tutor for algorithms and data structures.
Your role is to:
- Help students understand algorithmic thinking and complexity
- Explain various data structures (arrays, linked lists, trees, graphs, etc.)
- Guide them through algorithm design and analysis
- Discuss time and space complexity (Big O notation)
- Provide hints rather than complete solutions
- Ask guiding questions to help them think critically
- Be encouraging and supportive
- Focus on both theoretical understanding and practical implementation"""
    },
    'general': {
        'name': 'General Computer Science',
        'icon': 'compsci.png',
        'examples': [
            "What career paths are available in CS?",
            "How do compilers work?",
            "Explain object-oriented programming"
        ],
        'system_prompt': """You are a helpful computer science tutor.
Your role is to:
- Help students with various CS topics and concepts
- Answer questions about programming, theory, and applications
- Guide them through problem-solving
- Provide hints rather than complete solutions
- Ask guiding questions to help them think critically
- Be encouraging and supportive
- Cover topics from basic programming to advanced CS concepts"""
    }
}


def _google_get(url, access_token=None):
    """GET a Google OAuth endpoint and return parsed JSON (stdlib only)."""
    req = urllib.request.Request(url)
    if access_token:
        req.add_header('Authorization', 'Bearer ' + access_token)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode('utf-8'))


def verify_google_access_token(access_token):
    """Check with Google that the token is real and was issued to this app.

    Returns (user_info, None) on success or (None, error_message).
    The browser only passes the token; identity always comes from Google,
    never from fields the browser could fake.
    """
    if not access_token:
        return None, 'Missing token'
    try:
        info = _google_get('https://oauth2.googleapis.com/tokeninfo?access_token='
                           + urllib.parse.quote(access_token))
        if GOOGLE_CLIENT_ID and info.get('aud') != GOOGLE_CLIENT_ID:
            return None, 'Token was not issued to this app'
        user = _google_get('https://www.googleapis.com/oauth2/v3/userinfo', access_token)
        return user, None
    except Exception as e:  # invalid/expired token or network error
        print(f'Google token check failed: {e}')
        return None, 'Could not verify Google sign-in'

# Authentication routes
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/auth/google/callback', methods=['POST'])
def google_callback():
    """Handle Google OAuth callback"""
    data = request.json or {}
    user_info, error = verify_google_access_token(data.get('access_token'))
    if error:
        return jsonify({'success': False, 'error': 'auth_failed', 'message': error}), 401

    google_id = user_info.get('sub')
    email = (user_info.get('email') or '').lower()
    canon = _canon_email(email)
    name = user_info.get('name')
    picture = user_info.get('picture')

    if not google_id or not email or not user_info.get('email_verified', False):
        return jsonify({'success': False, 'error': 'Missing credentials'}), 401
    
    # Check email whitelist
    if canon not in ALLOWED_EMAILS:
        return jsonify({
            'success': False, 
            'error': 'auth_failed',
            'message': 'Access restricted to private beta users'
        }), 401
    
    # Check if user exists, create if not
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE google_id = ?', (google_id,)).fetchone()
    
    role = 'teacher' if canon in TEACHER_EMAILS else 'student'
    if user is None:
        db.execute(
            'INSERT INTO users (google_id, email, name, picture, role) VALUES (?, ?, ?, ?, ?)',
            (google_id, email, name, picture, role)
        )
        db.commit()
        user = db.execute('SELECT * FROM users WHERE google_id = ?', (google_id,)).fetchone()
    else:
        # Update user info (and role, which comes from TEACHER_EMAILS) in case it changed
        db.execute(
            'UPDATE users SET email = ?, name = ?, picture = ?, role = ? WHERE google_id = ?',
            (email, name, picture, role, google_id)
        )
        db.commit()
    
    # Set session
    session['user_id'] = user['id']
    session['email'] = email
    session['name'] = name
    session['picture'] = picture
    session['role'] = role
    
    db.close()
    
    return jsonify({
        'success': True,
        'redirect': '/'
    })

@app.route('/')
def index():
    """Signed in: go straight to the dashboard. Otherwise: the sign-in page."""
    if 'user_id' in session:
        return redirect('/dashboard')
    return render_template('login.html', google_client_id=GOOGLE_CLIENT_ID)

@app.route('/dashboard')
@login_required
def dashboard():
    user = {
        'name': session.get('name'),
        'email': session.get('email'),
        'picture': session.get('picture')
    }
    
    # Get user's conversations
    db = get_db()
    conversations = db.execute(
        '''SELECT id, subject, title, updated_at 
           FROM conversations 
           WHERE user_id = ? 
           ORDER BY updated_at DESC 
           LIMIT 10''',
        (session['user_id'],)
    ).fetchall()
    db.close()
    
    # Convert to list of dicts for template
    conv_list = []
    for conv in conversations:
        conv_list.append({
            'id': conv['id'],
            'subject': conv['subject'],
            'title': conv['title'],
            'updated_at': conv['updated_at']
        })
    
    return render_template('dashboard.html', 
                         subjects=SUBJECTS, 
                         user=user, 
                         conversations=conv_list,
                         is_teacher=session.get('role') == 'teacher')

@app.route('/chat/<subject>')
@login_required
def chat(subject):
    if subject not in SUBJECTS:
        return redirect(url_for('index'))
    
    conversation_id = request.args.get('conversation_id')
    messages = []
    
    # If loading an existing conversation
    if conversation_id:
        db = get_db()
        conv = db.execute(
            'SELECT messages FROM conversations WHERE id = ? AND user_id = ?',
            (conversation_id, session['user_id'])
        ).fetchone()
        db.close()
        
        if conv:
            messages = json.loads(conv['messages'])
    
    return render_template('chat.html', 
                         subject=subject,
                         subject_info=SUBJECTS[subject],
                         conversation_id=conversation_id,
                         initial_messages=messages)

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    data = request.json
    user_message = data.get('message', '').strip()
    subject = data.get('subject', 'general')
    conversation_id = data.get('conversation_id')
    
    if not user_message:
        return jsonify({'success': False, 'error': 'Empty message'})
    
    if subject not in SUBJECTS:
        return jsonify({'success': False, 'error': 'Invalid subject'})
    
    try:
        # Get or create conversation
        db = get_db()
        
        if conversation_id:
            # Load existing conversation
            conv = db.execute(
                'SELECT messages FROM conversations WHERE id = ? AND user_id = ?',
                (conversation_id, session['user_id'])
            ).fetchone()
            
            if conv:
                messages = json.loads(conv['messages'])
            else:
                messages = []
                conversation_id = None
        else:
            messages = []
        
        # Add user message to conversation
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Get response from Claude with retry
        response = chat_with_retry(messages, system=SUBJECTS[subject]['system_prompt'])
        
        # Extract assistant's response
        assistant_message = response.content[0].text
        
        # Add assistant response to conversation
        messages.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        # Save to database
        if conversation_id:
            # Update existing conversation
            db.execute(
                'UPDATE conversations SET messages = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (json.dumps(messages), conversation_id)
            )
            db.commit()
        else:
            # Create new conversation with a title from first message
            title = user_message[:50] + ('...' if len(user_message) > 50 else '')
            cursor = db.execute(
                'INSERT INTO conversations (user_id, subject, title, messages) VALUES (?, ?, ?, ?)',
                (session['user_id'], subject, title, json.dumps(messages))
            )
            db.commit()
            conversation_id = cursor.lastrowid
        
        db.close()
        
        return jsonify({
            'success': True,
            'response': assistant_message,
            'conversation_id': conversation_id
        })
        
    except Exception as e:
        error_msg = str(e).lower()
        print(f"Chat error: {e}")
        
        # User-friendly error messages
        if "overloaded" in error_msg or "529" in error_msg:
            return jsonify({
                'success': False,
                'error': "The AI is experiencing high demand right now. Please try again in a moment! 🔄"
            }), 503
        elif "api key" in error_msg:
            return jsonify({
                'success': False,
                'error': "API configuration error. Please contact support."
            }), 500
        else:
            return jsonify({
                'success': False,
                'error': f"Sorry, an error occurred. Please try again."
            }), 500

@app.route('/api/chat/file', methods=['POST'])
@login_required
def api_chat_file():
    """Handle chat with file uploads"""
    try:
        message = request.form.get('message', '').strip()
        subject = request.form.get('subject', 'general')
        conversation_id = request.form.get('conversation_id')
        file = request.files.get('file')
        
        if not message and not file:
            return jsonify({'success': False, 'error': 'No message or file provided'})
        
        if subject not in SUBJECTS:
            return jsonify({'success': False, 'error': 'Invalid subject'})
        
        # Get or create conversation
        db = get_db()
        
        if conversation_id:
            conv = db.execute(
                'SELECT messages FROM conversations WHERE id = ? AND user_id = ?',
                (conversation_id, session['user_id'])
            ).fetchone()
            
            if conv:
                messages = json.loads(conv['messages'])
            else:
                messages = []
                conversation_id = None
        else:
            messages = []
        
        # Build user message content
        content_parts = []
        file_metadata = None  # To store for display purposes
        
        if file:
            # Read and encode file
            file_data = file.read()
            file_b64 = base64.b64encode(file_data).decode('utf-8')
            
            # Determine media type
            filename = file.filename.lower()
            if filename.endswith('.pdf'):
                media_type = 'application/pdf'
                content_parts.append({
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": file_b64
                    }
                })
                file_metadata = {
                    "type": "document",
                    "name": file.filename,
                    "size": len(file_data)
                }
            elif filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                if filename.endswith('.png'):
                    media_type = 'image/png'
                elif filename.endswith('.gif'):
                    media_type = 'image/gif'
                elif filename.endswith('.webp'):
                    media_type = 'image/webp'
                else:
                    media_type = 'image/jpeg'
                
                content_parts.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": file_b64
                    }
                })
                # Store image data for display (limit size to 2MB for DB storage)
                if len(file_data) < 2 * 1024 * 1024:
                    file_metadata = {
                        "type": "image",
                        "name": file.filename,
                        "media_type": media_type,
                        "data": f"data:{media_type};base64,{file_b64}",
                        "size": len(file_data)
                    }
                else:
                    file_metadata = {
                        "type": "image",
                        "name": file.filename,
                        "size": len(file_data),
                        "too_large": True
                    }
            else:
                return jsonify({'success': False, 'error': 'Unsupported file type'})
        
        # Add text message
        if message:
            content_parts.append({
                "type": "text",
                "text": message
            })
        
        # Create user message for API (with file content for Claude)
        api_message = {
            "role": "user",
            "content": content_parts
        }
        
        # Create user message for storage (with metadata for display)
        storage_content = []
        if file_metadata:
            storage_content.append({
                "type": "attachment",
                "attachment": file_metadata
            })
        if message:
            storage_content.append({
                "type": "text",
                "text": message
            })
        
        storage_message = {
            "role": "user",
            "content": storage_content if len(storage_content) > 1 else (storage_content[0] if storage_content else message)
        }
        
        # Add to messages for API call
        messages.append(api_message)
        
        # Get response from Claude with retry
        response = chat_with_retry(messages, system=SUBJECTS[subject]['system_prompt'])
        
        # Extract response
        assistant_message = response.content[0].text
        
        # Update last message in messages array to storage version
        messages[-1] = storage_message
        
        # Add assistant response
        messages.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        # Save to database
        if conversation_id:
            db.execute(
                'UPDATE conversations SET messages = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (json.dumps(messages), conversation_id)
            )
            db.commit()
        else:
            title = message[:50] if message else f'File: {file.filename}'
            cursor = db.execute(
                'INSERT INTO conversations (user_id, subject, title, messages) VALUES (?, ?, ?, ?)',
                (session['user_id'], subject, title, json.dumps(messages))
            )
            db.commit()
            conversation_id = cursor.lastrowid
        
        db.close()
        
        return jsonify({
            'success': True,
            'response': assistant_message,
            'conversation_id': conversation_id
        })
        
    except Exception as e:
        error_msg = str(e).lower()
        print(f"File chat error: {e}")
        
        if "overloaded" in error_msg or "529" in error_msg:
            return jsonify({
                'success': False,
                'error': "The AI is experiencing high demand right now. Please try again in a moment! 🔄"
            }), 503
        else:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

@app.route('/api/practice', methods=['POST'])
@login_required
def api_practice():
    print("=== AP PRACTICE CALLED ===")
    print(f"Request data: {request.json}")
    """Find relevant AP practice questions"""
    data = request.json
    subject = data.get('subject', 'general')
    topic = data.get('topic', '')
    conversation_id = data.get('conversation_id')
    
    if subject not in SUBJECTS:
        return jsonify({'success': False, 'error': 'Invalid subject'})
    
    try:
        # Get conversation from database if it exists
        db = get_db()
        messages = []
        
        if conversation_id:
            conv = db.execute(
                'SELECT messages FROM conversations WHERE id = ? AND user_id = ?',
                (conversation_id, session['user_id'])
            ).fetchone()
            
            if conv:
                messages = json.loads(conv['messages'])
        
        # Add user's practice request
        user_message = "I'd like to practice some problems. Can you recommend specific practice problems and resources?"
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Simple practice prompt
        practice_messages = [{
            "role": "user",
            "content": f"I'm studying {SUBJECTS[subject]['name']}. Can you recommend specific practice problems and resources I can use? Include links to College Board resources if this is an AP course, and other reputable practice sites like CodeHS, CodingBat, etc."
        }]
        
        # Get response with retry
        response = chat_with_retry(practice_messages, system=SUBJECTS[subject]['system_prompt'])
        
        # Extract response text
        response_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                response_text += block.text
            elif isinstance(block, dict) and block.get('type') == 'text':
                response_text += block.get('text', '')
        
        if not response_text:
            response_text = "I'd recommend checking College Board's AP Central for official practice questions, CodeHS for interactive exercises, and CodingBat for coding practice."
        
        # Add assistant response to conversation
        messages.append({
            "role": "assistant",
            "content": f"Practice Resources: {SUBJECTS[subject]['name']}\n\n{response_text}"
        })
        
        # Save updated conversation to database
        if conversation_id:
            db.execute(
                'UPDATE conversations SET messages = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (json.dumps(messages), conversation_id)
            )
            db.commit()
        
        db.close()
        
        return jsonify({
            'success': True,
            'topic': SUBJECTS[subject]['name'],
            'response': response_text
        })
        
    except Exception as e:
        print(f"Practice error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/export', methods=['POST'])
@login_required
def api_export():
    """Export conversation as formatted text"""
    data = request.json
    subject = data.get('subject', 'general')
    conversation_id = data.get('conversation_id')
    
    if not conversation_id:
        return jsonify({
            'success': False,
            'error': 'No conversation to export'
        })
    
    try:
        # Get conversation from database
        db = get_db()
        conv = db.execute(
            'SELECT messages, title FROM conversations WHERE id = ? AND user_id = ?',
            (conversation_id, session['user_id'])
        ).fetchone()
        db.close()
        
        if not conv:
            return jsonify({
                'success': False,
                'error': 'Conversation not found'
            })
        
        messages = json.loads(conv['messages'])
        
        # Format conversation
        export_text = f"{SUBJECTS.get(subject, {}).get('name', 'Tutoring')} - {conv['title']}\n"
        export_text += "=" * 70 + "\n\n"
        
        for msg in messages:
            role = "Student" if msg['role'] == 'user' else "Tutor"
            
            # Handle different content formats
            if isinstance(msg['content'], str):
                content = msg['content']
            elif isinstance(msg['content'], list):
                # Extract text from content blocks
                text_parts = []
                for block in msg['content']:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        text_parts.append(block.get('text', ''))
                    elif isinstance(block, dict) and block.get('type') in ['image', 'document']:
                        text_parts.append(f"[{block['type'].upper()} ATTACHED]")
                content = '\n'.join(text_parts)
            else:
                content = str(msg['content'])
            
            export_text += f"{role}:\n{content}\n\n"
            export_text += "-" * 70 + "\n\n"
        
        export_text += "=" * 70 + "\n"
        export_text += f"End of session - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        
        return jsonify({
            'success': True,
            'content': export_text
        })
        
    except Exception as e:
        print(f"Export error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/summary', methods=['POST'])
@login_required
def api_summary():
    """Generate a summary of the conversation"""
    data = request.json
    subject = data.get('subject', 'general')
    conversation_id = data.get('conversation_id')
    
    if not conversation_id:
        return jsonify({
            'success': False,
            'error': 'No conversation to summarize'
        })
    
    try:
        # Get conversation from database
        db = get_db()
        conv = db.execute(
            'SELECT messages FROM conversations WHERE id = ? AND user_id = ?',
            (conversation_id, session['user_id'])
        ).fetchone()
        
        if not conv:
            db.close()
            return jsonify({
                'success': False,
                'error': 'Conversation not found'
            })
        
        messages = json.loads(conv['messages'])
        
        # Create a summary prompt
        summary_messages = messages.copy()
        summary_messages.append({
            "role": "user",
            "content": """Please provide a concise summary of our conversation with:
1. Main topics discussed (2-3 bullet points)
2. Key concepts the student learned
3. Suggested next steps for continued learning

Format this as a clear, student-friendly summary."""
        })
        
        response = chat_with_retry(summary_messages)
        
        summary = response.content[0].text
        
        # Add summary response to conversation
        messages.append({
            "role": "user",
            "content": "Can you provide a summary of our conversation?"
        })
        messages.append({
            "role": "assistant",
            "content": f"📝 Session Summary\n\n{summary}"
        })
        
        # Save updated conversation
        db.execute(
            'UPDATE conversations SET messages = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (json.dumps(messages), conversation_id)
        )
        db.commit()
        db.close()
        
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        print(f"Summary error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/clear', methods=['POST'])
@login_required
def api_clear():
    """Clear conversation history - creates a new conversation"""
    data = request.json
    conversation_id = data.get('conversation_id')
    
    # We don't actually delete the old conversation (for record keeping)
    # Instead, we just signal the frontend to start fresh
    # The frontend will create a new conversation on the next message
    
    return jsonify({'success': True})

# ── Practice: the AI Architect lab (Monaco editor + Python in the browser) ──
@app.route('/lab')
@login_required
def lab():
    from labs.ai_architect import curriculum_for_page
    return render_template('lab.html', lab=curriculum_for_page())


# ── Check the AI: slop-detector tasks (AP CSP, competency C2) ──
from slop_detector.harness.loader import load_task as load_slop_task  # noqa: E402
from slop_detector.harness.scorer import score as score_slop  # noqa: E402
from slop_detector.harness.executor import SandboxUnavailable  # noqa: E402
from slop_detector.harness.loader import defect_line_map  # noqa: E402

# The order students see. To add a task: put its JSON in slop_detector/tasks/
# and add its id here.
SLOP_TASK_ORDER = ['csp-slop-01', 'csp-slop-02', 'csp-slop-03', 'csp-slop-04', 'csp-slop-05']
SLOP_TASKS = set(SLOP_TASK_ORDER)
SLOP_DEFECT_TYPES = ['functional_bug', 'edge_case', 'hallucination', 'intent_gap', 'false_claim']
SLOP_DIMENSIONS = ['detection', 'diagnosis', 'correction', 'verification', 'calibration']
MAX_CODE_CHARS = 20000
MAX_FLAGS = 20
MAX_TEXT_CHARS = 4000

if os.environ.get('RENDER') and os.environ.get('EXECUTOR', 'local').lower() != 'judge0':
    print('WARNING: Check the AI is running student code WITHOUT a sandbox. '
          'Set EXECUTOR=judge0 and JUDGE0_URL/JUDGE0_KEY before real students use it.')

try:
    from zoneinfo import ZoneInfo
    _LOCAL_TZ = ZoneInfo(os.environ.get('TIMEZONE', 'America/New_York'))
except Exception:  # pragma: no cover
    _LOCAL_TZ = None


@app.template_filter('localtime')
def _localtime(value, short=False):
    """SQLite stores UTC; show it in the teacher's time zone."""
    if not value:
        return ''
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '')).replace(tzinfo=timezone.utc)
        if _LOCAL_TZ:
            dt = dt.astimezone(_LOCAL_TZ)
        return dt.strftime('%b %-d · %-I:%M %p' if short else '%b %-d, %Y · %-I:%M %p')
    except ValueError:
        return value


@app.template_filter('py')
def _py(value):
    """Show test inputs/outputs the way Python writes them (True, not true)."""
    if isinstance(value, list) and len(value) == 1:
        return repr(value[0])
    if isinstance(value, list):
        return ', '.join(repr(v) for v in value)
    return repr(value)


def _slop_task_list():
    out = []
    for i, tid in enumerate(SLOP_TASK_ORDER, start=1):
        t = load_slop_task(tid)
        out.append({'id': tid, 'n': i, 'title': t.get('title', tid), 'prompt': t['prompt']})
    return out


def _progress(db, user_id):
    """Per task for one student: attempts, passed (on any attempt), best and latest."""
    rows = db.execute(
        'SELECT task_id, attempt_no, score, passed, created_at FROM attempts '
        'WHERE user_id = ? ORDER BY id', (user_id,)).fetchall()
    prog = {tid: {'attempts': 0, 'passed': False, 'best': None, 'last': None}
            for tid in SLOP_TASK_ORDER}
    for r in rows:
        p = prog.get(r['task_id'])
        if p is None:
            continue
        p['attempts'] += 1
        p['passed'] = p['passed'] or bool(r['passed'])
        p['best'] = r['score'] if p['best'] is None else max(p['best'], r['score'])
        p['last'] = r['created_at']
    passed = sum(1 for p in prog.values() if p['passed'])
    return prog, passed


@app.route('/check')
@login_required
def check():
    tasks = _slop_task_list()
    db = get_db()
    prog, passed = _progress(db, session['user_id'])
    db.close()
    task_id = request.args.get('task')
    if task_id in SLOP_TASKS:
        return render_template('check.html', tasks=tasks, task_id=task_id, progress=prog)
    return render_template('check_list.html', tasks=tasks, progress=prog,
                           passed=passed, total=len(tasks))


@app.route('/check/api/task/<task_id>')
@login_required
def check_task(task_id):
    if task_id not in SLOP_TASKS:
        return jsonify({'error': 'Unknown task'}), 404
    task = load_slop_task(task_id)
    # Server-side start time for the evidence trail (first time the task opens).
    opened = dict(session.get('task_opened') or {})
    opened.setdefault(task_id, datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec='seconds'))
    session['task_opened'] = opened
    # Student-safe view only: the answer key never leaves the server.
    return jsonify({
        'task_id': task['task_id'], 'title': task.get('title', task_id),
        'prompt': task['prompt'], 'language': task['language'],
        'entrypoint': task['entrypoint'], 'buggy_code': task['buggy_code'],
        'defect_types': SLOP_DEFECT_TYPES,
    })


def _clean_submission(raw):
    """Keep only what the scorer needs, in the shapes it expects."""
    flags = []
    for f in (raw.get('flags') or [])[:MAX_FLAGS]:
        if not isinstance(f, dict):
            continue
        try:
            line = int(f.get('line'))
        except (TypeError, ValueError):
            continue
        claimed = f.get('claimed_type') if f.get('claimed_type') in SLOP_DEFECT_TYPES else None
        flags.append({'line': line, 'claimed_type': claimed,
                      'explanation': str(f.get('explanation') or '')[:MAX_TEXT_CHARS]})
    code = raw.get('edited_code')
    if not isinstance(code, str) or not code.strip() or len(code) > MAX_CODE_CHARS:
        return None
    return {'task_id': raw.get('task_id'), 'flags': flags, 'edited_code': code,
            'explanation': str(raw.get('explanation') or '')[:MAX_TEXT_CHARS]}


@app.route('/check/api/submit', methods=['POST'])
@login_required
def check_submit():
    raw = request.get_json(silent=True) or {}
    if raw.get('task_id') not in SLOP_TASKS:
        return jsonify({'error': 'Unknown task'}), 404
    submission = _clean_submission(raw)
    if submission is None:
        return jsonify({'error': 'Your code is empty or too long.'}), 400
    submission['student_id'] = str(session['user_id'])  # never trust the browser for identity
    task = load_slop_task(submission['task_id'])
    try:
        result = score_slop(task, submission)
    except SandboxUnavailable as e:
        app.logger.error('Sandbox unavailable: %s', e)
        return jsonify({'error': "The code runner didn't answer. Nothing was saved; "
                                 "please try again in a minute."}), 503

    db = get_db()
    n = db.execute('SELECT COUNT(*) FROM attempts WHERE user_id = ? AND task_id = ?',
                   (session['user_id'], task['task_id'])).fetchone()[0]
    db.execute(
        '''INSERT INTO attempts (user_id, task_id, attempt_no, flags_selected, submitted_code,
           explanation_text, test_results, dimensions, score, passed, evidence, started_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (session['user_id'], task['task_id'], n + 1, json.dumps(submission['flags']),
         submission['edited_code'], submission['explanation'],
         json.dumps(result.evidence['tests']), json.dumps(result.dimensions),
         sum(result.dimensions.values()), int(result.passed), json.dumps(result.evidence),
         (session.get('task_opened') or {}).get(task['task_id'])))
    db.commit()
    _, passed = _progress(db, session['user_id'])
    db.close()

    return jsonify({
        'task_id': result.task_id,
        'dimensions': result.dimensions,
        'passed': result.passed,
        'attempt_no': n + 1,
        'overall': {'passed': passed, 'total': len(SLOP_TASK_ORDER)},
        'evidence': {k: result.evidence[k] for k in
                     ('tests_passed', 'trap_flagged', 'regressions', 'flags_matched')},
    })


# ── Teacher view: roster + each student's evidence trail ──
@app.route('/teacher')
@teacher_required
def teacher():
    tasks = _slop_task_list()
    db = get_db()
    people = db.execute(
        '''SELECT u.id, u.name, u.email, u.role, MAX(a.created_at) AS last_active
           FROM users u LEFT JOIN attempts a ON a.user_id = u.id
           WHERE u.role = 'student' OR a.id IS NOT NULL
           GROUP BY u.id ORDER BY u.role DESC, LOWER(u.name)''').fetchall()
    roster = []
    for p in people:
        prog, passed = _progress(db, p['id'])
        roster.append({'id': p['id'], 'name': p['name'] or p['email'], 'email': p['email'],
                       'role': p['role'], 'last_active': p['last_active'],
                       'progress': prog, 'passed': passed,
                       'attempts': sum(x['attempts'] for x in prog.values())})
    db.close()
    return render_template('teacher.html', tasks=tasks, roster=roster)


@app.route('/teacher/student/<int:user_id>')
@teacher_required
def teacher_student(user_id):
    db = get_db()
    person = db.execute('SELECT id, name, email, role FROM users WHERE id = ?',
                        (user_id,)).fetchone()
    if person is None:
        db.close()
        return redirect('/teacher')
    rows = db.execute('SELECT * FROM attempts WHERE user_id = ? ORDER BY task_id, id DESC',
                      (user_id,)).fetchall()
    prog, passed = _progress(db, user_id)
    db.close()
    by_task = {tid: [] for tid in SLOP_TASK_ORDER}
    for r in rows:
        if r['task_id'] not in by_task:
            continue
        by_task[r['task_id']].append({
            'attempt_no': r['attempt_no'], 'score': r['score'], 'passed': bool(r['passed']),
            'dimensions': json.loads(r['dimensions']), 'flags': json.loads(r['flags_selected']),
            'code': r['submitted_code'], 'explanation': r['explanation_text'],
            'tests': json.loads(r['test_results']), 'evidence': json.loads(r['evidence']),
            'started_at': r['started_at'], 'created_at': r['created_at'],
        })
    tasks = []
    for t in _slop_task_list():
        full = load_slop_task(t['id'])
        # Teacher-only: mark each flag against the answer key.
        line_map = defect_line_map(full)
        lines = full['buggy_code'].splitlines()
        for a in by_task[t['id']]:
            for f in a['flags']:
                d = line_map.get(f.get('line'))
                f['line_text'] = lines[f['line'] - 1].strip() if 0 < f.get('line', 0) <= len(lines) else ''
                f['hit'] = 'trap' if d and d['is_trap'] else ('bug' if d else 'miss')
                f['type_ok'] = bool(d and not d['is_trap'] and f.get('claimed_type') == d['type'])
        tasks.append({**t, 'buggy_code': full['buggy_code'], 'attempts': by_task[t['id']],
                      'progress': prog[t['id']]})
    return render_template('teacher_student.html', person=person, tasks=tasks,
                           passed=passed, total=len(tasks), dims=SLOP_DIMENSIONS)


@app.route('/auth/google/redirect')
def google_redirect():
    """Handle Google OAuth implicit flow redirect"""
    return render_template('oauth_redirect.html')


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
