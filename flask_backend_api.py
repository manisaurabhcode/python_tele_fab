"""
Flask Backend API for Mythology Story Generator
Connects Vue.js frontend to Python pipeline
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
from datetime import datetime
from pathlib import Path

# Import your existing modules
from mythology_pipeline import MythologyPipeline, Config, BOOK_CATALOG
from story_generator import StoryGenerator, STORY_THEMES
from character_knowledge_graph import CharacterKnowledgeGraph, COMMON_CHARACTERS, CharacterProfile

app = Flask(__name__, static_folder='static')
CORS(app)

# Initialize components
config = Config(
    redis_host=os.getenv('REDIS_HOST', 'localhost'),
    redis_port=int(os.getenv('REDIS_PORT', 6379)),
    openai_api_key=os.getenv('OPENAI_API_KEY')
)

pipeline = MythologyPipeline(config)
story_generator = StoryGenerator(pipeline, model="gpt-4")
character_kg = CharacterKnowledgeGraph(llm_api_key=config.openai_api_key)

# Data directories
STORIES_DIR = Path("generated_stories")
IMAGES_DIR = Path("generated_images")
STORIES_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

# Activity log
activity_log = []

def log_activity(activity_type, title, description):
    """Log activity for frontend display"""
    activity_log.insert(0, {
        'id': len(activity_log),
        'type': activity_type,
        'title': title,
        'description': description,
        'time': datetime.now().strftime('%H:%M'),
        'icon': {
            'story': '✨',
            'book': '📚',
            'character': '🎭',
            'search': '🔍'
        }.get(activity_type, '📋')
    })
    
    # Keep only last 50 activities
    if len(activity_log) > 50:
        activity_log.pop()


# ============================================================================
# API Routes
# ============================================================================

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('static', 'index.html')


@app.route('/api/stats')
def get_stats():
    """Get database statistics"""
    try:
        db_stats = pipeline.get_stats()
        kg_stats = character_kg.get_statistics()
        
        # Count generated stories
        story_files = list(STORIES_DIR.glob('*.json'))
        
        return jsonify({
            'total_documents': db_stats.get('total_documents', 0),
            'books_indexed': len(BOOK_CATALOG),
            'total_characters': kg_stats.get('total_characters', 0),
            'generated_stories': len(story_files),
            'storage_mb': sum(f.stat().st_size for f in STORIES_DIR.glob('*')) // (1024 * 1024)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stories/generate', methods=['POST'])
def generate_story():
    """Generate a new story"""
    try:
        data = request.json
        theme = data.get('theme')
        category = data.get('category')
        age_range = data.get('age_range', '5-8 years')
        target_duration = data.get('target_duration', 300)
        
        if not theme:
            return jsonify({'error': 'Theme is required'}), 400
        
        # Generate story
        story = story_generator.create_story_from_theme(
            theme=theme,
            category=category,
            age_range=age_range
        )
        
        # Save story
        story_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        story_file = STORIES_DIR / f"story_{story_id}.json"
        
        story_dict = story.model_dump()
        story_dict['id'] = story_id
        story_dict['created_at'] = datetime.now().isoformat()
        story_dict['theme'] = theme
        
        with open(story_file, 'w', encoding='utf-8') as f:
            json.dump(story_dict, f, indent=2, ensure_ascii=False)
        
        # Log activity
        log_activity('story', f'Generated: {story.title}', f'Theme: {theme}')
        
        return jsonify(story_dict)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stories')
def get_stories():
    """Get all generated stories"""
    try:
        stories = []
        
        for story_file in STORIES_DIR.glob('story_*.json'):
            with open(story_file, 'r', encoding='utf-8') as f:
                story = json.load(f)
                
                # Add emoji based on category
                emoji_map = {
                    'epic': '⚔️',
                    'fables': '🦁',
                    'folk_tales': '🎪'
                }
                story['emoji'] = emoji_map.get(story.get('category', ''), '📖')
                
                # Add tags
                story['tags'] = [story.get('category', 'story'), story.get('age_range', '')]
                
                stories.append(story)
        
        # Sort by created_at (newest first)
        stories.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return jsonify(stories)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stories/<story_id>')
def get_story(story_id):
    """Get a specific story"""
    try:
        story_file = STORIES_DIR / f"story_{story_id}.json"
        
        if not story_file.exists():
            return jsonify({'error': 'Story not found'}), 404
        
        with open(story_file, 'r', encoding='utf-8') as f:
            story = json.load(f)
        
        return jsonify(story)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/search')
def search_books():
    """Search mythology texts"""
    try:
        query = request.args.get('query')
        category = request.args.get('category')
        top_k = int(request.args.get('top_k', 10))
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Search using pipeline
        results = pipeline.search_similar_stories(
            query=query,
            top_k=top_k,
            category=category if category else None
        )
        
        # Log activity
        log_activity('search', f'Searched: {query}', f'Found {len(results)} results')
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/characters')
def get_characters():
    """Get all characters"""
    try:
        characters = []
        
        # Load character library
        character_file = Path('character_library.json')
        if character_file.exists():
            with open(character_file, 'r', encoding='utf-8') as f:
                char_data = json.load(f)
                
            for name, profile in char_data.items():
                # Count stories featuring this character
                story_count = 0
                for story_file in STORIES_DIR.glob('story_*.json'):
                    with open(story_file, 'r', encoding='utf-8') as f:
                        story = json.load(f)
                        if any(c['name'].lower() == name.lower() for c in story.get('characters', [])):
                            story_count += 1
                
                # Add emoji
                emoji_map = {
                    'Krishna': '🦚',
                    'Hanuman': '🐒',
                    'Ganesha': '🐘',
                    'Rama': '🏹',
                    'Sita': '👸'
                }
                
                characters.append({
                    'name': profile['name'],
                    'category': profile['category'],
                    'child_friendly_description': profile['child_friendly_description'],
                    'personality_traits': profile['personality_traits'][:4],
                    'stories_count': story_count,
                    'emoji': emoji_map.get(profile['name'], '👤')
                })
        else:
            # Use default characters
            for char_data in COMMON_CHARACTERS.values():
                characters.append({
                    'name': char_data['name'],
                    'category': char_data['category'],
                    'child_friendly_description': char_data['child_friendly_description'],
                    'personality_traits': char_data['personality_traits'][:4],
                    'stories_count': 0,
                    'emoji': {'Krishna': '🦚', 'Hanuman': '🐒', 'Ganesha': '🐘'}.get(char_data['name'], '👤')
                })
        
        return jsonify(characters)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/characters/<character_name>')
def get_character(character_name):
    """Get a specific character"""
    try:
        character = character_kg.get_character(character_name)
        
        if not character:
            return jsonify({'error': 'Character not found'}), 404
        
        return jsonify(character.model_dump())
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/books/available')
def get_available_books():
    """Get list of available books for ingestion"""
    try:
        # Check which books are already indexed
        # This is a simplified check - you'd want to track this properly
        indexed_books = set()
        
        books = []
        for book in BOOK_CATALOG:
            books.append({
                'title': book['title'],
                'url': book['url'],
                'category': book['category'],
                'priority': book['priority'],
                'indexed': book['title'] in indexed_books,
                'selected': False
            })
        
        return jsonify(books)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/books/ingest', methods=['POST'])
def ingest_books():
    """Ingest selected books into the database"""
    try:
        data = request.json
        books = data.get('books', [])
        
        if not books:
            return jsonify({'error': 'No books provided'}), 400
        
        # Run ingestion pipeline
        pipeline.run_pipeline(books)
        
        # Log activity
        log_activity('book', f'Ingested {len(books)} books', 'Pipeline completed successfully')
        
        return jsonify({'success': True, 'books_ingested': len(books)})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/activity')
def get_activity():
    """Get recent activity log"""
    return jsonify(activity_log[:20])  # Return last 20 activities


@app.route('/api/usage')
def get_usage():
    """Get API usage statistics (mock data for now)"""
    # In production, you'd track this from actual API calls
    return jsonify({
        'embeddings': 2.45,
        'gpt4': 8.67,
        'images': 1.23
    })


@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        # Check Redis connection
        pipeline.redis_client.ping()
        
        return jsonify({
            'status': 'healthy',
            'redis': 'connected',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    # Load character library if exists
    char_lib_file = Path('character_library.json')
    if char_lib_file.exists():
        try:
            character_kg.import_character_library(str(char_lib_file))
            print(f"✓ Loaded {len(character_kg.characters)} characters")
        except Exception as e:
            print(f"Warning: Could not load character library: {e}")
    else:
        # Initialize with common characters
        for char_data in COMMON_CHARACTERS.values():
            profile = CharacterProfile(**char_data)
            character_kg.add_character(profile)
        
        # Save character library
        character_kg.export_character_library(str(char_lib_file))
        print(f"✓ Created character library with {len(character_kg.characters)} characters")
    
    print("\n" + "="*60)
    print("🎬 Mythology Story Generator - API Server")
    print("="*60)
    print(f"Server starting on http://localhost:5000")
    print(f"API endpoints available at http://localhost:5000/api/")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
