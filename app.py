from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import anthropic
import secrets
import base64
import os
from datetime import datetime
import sqlite3
from functools import wraps
import json
import time
from anthropic import Anthropic

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Email whitelist for private beta
ALLOWED_EMAILS = {
    'jami.saffioti@gmail.com',
    'nova.noros@gmail.com',
}

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

def chat_with_retry(messages, model="claude-sonnet-4-20250514", max_tokens=1000, max_retries=3):
    """Call Anthropic API with automatic retry on overload"""
    for attempt in range(max_retries):
        try:
            response = client.messages.create(  # ← FIXED: was calling itself
                model=model,
                max_tokens=max_tokens,
                messages=messages
            )
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
def init_db():
    conn = sqlite3.connect('tutorbot.db')
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
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Database helper functions
def get_db():
    conn = sqlite3.connect('tutorbot.db')
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

SUBJECTS = {
    'ap_cs_a': {
        'name': 'AP Computer Science A',
        'icon': 'cupojoe.png',
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

Be warm, encouraging, and patient. Praise effort and thinking process, not just correct answers."""
    },
    'ap_cs_principles': {
        'name': 'AP Computer Science Principles',
        'icon': 'pysnake.png',
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

Be enthusiastic, relatable, and patient. Make CS feel accessible and relevant."""
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

# Authentication routes
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/auth/google/callback', methods=['POST'])
def google_callback():
    """Handle Google OAuth callback"""
    data = request.json
    
    google_id = data.get('google_id')
    email = data.get('email')
    name = data.get('name')
    picture = data.get('picture')
    
    if not google_id or not email:
        return jsonify({'success': False, 'error': 'Missing credentials'})
    
    # Check email whitelist
    if email not in ALLOWED_EMAILS:
        return jsonify({
            'success': False, 
            'error': 'auth_failed',
            'message': 'Access restricted to private beta users'
        }), 401
    
    # Check if user exists, create if not
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE google_id = ?', (google_id,)).fetchone()
    
    if user is None:
        db.execute(
            'INSERT INTO users (google_id, email, name, picture) VALUES (?, ?, ?, ?)',
            (google_id, email, name, picture)
        )
        db.commit()
        user = db.execute('SELECT * FROM users WHERE google_id = ?', (google_id,)).fetchone()
    else:
        # Update user info in case it changed
        db.execute(
            'UPDATE users SET email = ?, name = ?, picture = ? WHERE google_id = ?',
            (email, name, picture, google_id)
        )
        db.commit()
    
    # Set session
    session['user_id'] = user['id']
    session['email'] = email
    session['name'] = name
    session['picture'] = picture
    
    db.close()
    
    return jsonify({
        'success': True,
        'redirect': '/'
    })

@app.route('/')
def index():
    """Render the login page or subject selection based on login status"""
    if 'user_id' in session:
        user = {
            'name': session.get('name'),
            'email': session.get('email'),
            'picture': session.get('picture')
        }
        return render_template('index.html', subjects=SUBJECTS, user=user)
    return render_template('login.html')

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
                         conversations=conv_list)

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
        response = chat_with_retry(messages)
        
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
        response = chat_with_retry(messages)
        
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
        response = chat_with_retry(practice_messages)
        
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

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
@app.route('/auth/google/redirect')
def google_redirect():
    """Handle Google OAuth implicit flow redirect"""
    return render_template('oauth_redirect.html')

