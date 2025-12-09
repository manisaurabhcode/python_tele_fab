# Complete Implementation Guide
## Indian Mythology Story Generation Pipeline

This guide walks you through implementing a fully automated content pipeline from books to videos.

---

## 📋 Overview

**What You're Building:**
1. Vector database of mythology texts (Redis)
2. Character knowledge graph for consistency
3. LLM-powered story adaptation system
4. Automated image generation
5. Voice synthesis and video creation

**Your Advantages:**
- ✅ Python expert
- ✅ LangChain knowledge
- ✅ Embedding experience
- ✅ Knowledge graph expertise

---

## 🚀 Phase 1: Foundation (Week 1-2)

### Step 1.1: Environment Setup

```bash
# Create project directory
mkdir mythology-pipeline
cd mythology-pipeline
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**requirements.txt:**
```
langchain==0.1.0
langchain-openai==0.0.2
openai==1.7.0
redis==5.0.1
numpy==1.24.3
requests==2.31.0
python-dotenv==1.0.0
pydantic==2.5.0
```

### Step 1.2: Redis Setup

```bash
# Docker (easiest)
docker run -d --name redis-stack -p 6379:6379 -p 8001:8001 redis/redis-stack:latest

# Verify
redis-cli ping  # Should return PONG
```

### Step 1.3: Configuration

Create `.env`:
```bash
OPENAI_API_KEY=your_key_here
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Step 1.4: Test Basic Pipeline

```python
from mythology_pipeline import MythologyPipeline, Config
import os

config = Config(openai_api_key=os.getenv("OPENAI_API_KEY"))
pipeline = MythologyPipeline(config)

# Run with 1 book first
test_books = [
    {
        "title": "The Panchatantra",
        "url": "https://www.gutenberg.org/files/25545/25545-0.txt",
        "category": "fables",
        "age_appropriate": True,
        "priority": 1
    }
]

pipeline.run_pipeline(test_books)
```

**Expected Cost: ~$0.05** for embeddings
**Time: 5-10 minutes**

---

## 📚 Phase 2: Content Ingestion (Week 2-3)

### Step 2.1: Download All Priority Books

Run the main pipeline:
```python
from mythology_pipeline import MythologyPipeline, Config, BOOK_CATALOG
import os

config = Config(openai_api_key=os.getenv("OPENAI_API_KEY"))
pipeline = MythologyPipeline(config)

# All priority 1 books (most important)
priority_books = [b for b in BOOK_CATALOG if b["priority"] == 1]
pipeline.run_pipeline(priority_books)

# Check results
stats = pipeline.get_stats()
print(f"Documents indexed: {stats['total_documents']}")
```

**Expected Cost: ~$0.20-0.30** for embeddings
**Time: 30-45 minutes**
**Storage: ~500MB in Redis**

### Step 2.2: Test Search Quality

```python
# Test various queries
test_queries = [
    "stories about honesty and truth",
    "tales with animal characters",
    "Krishna as a young boy",
    "brave heroes fighting demons"
]

for query in test_queries:
    results = pipeline.search_similar_stories(query, top_k=3)
    print(f"\nQuery: {query}")
    for r in results:
        print(f"  - {r['book']} (score: {r['score']:.3f})")
```

---

## 🎭 Phase 3: Character System (Week 3-4)

### Step 3.1: Build Character Library

```python
from character_knowledge_graph import CharacterKnowledgeGraph, COMMON_CHARACTERS
from character_knowledge_graph import CharacterProfile
import os

# Initialize
kg = CharacterKnowledgeGraph(llm_api_key=os.getenv("OPENAI_API_KEY"))

# Add pre-defined characters
for char_data in COMMON_CHARACTERS.values():
    profile = CharacterProfile(**char_data)
    kg.add_character(profile)

# Export for reuse
kg.export_character_library("character_library.json")
```

### Step 3.2: Extract Additional Characters

```python
# Find stories about specific characters
character_names = ["Rama", "Sita", "Arjuna", "Draupadi"]

for char_name in character_names:
    # Search for character in texts
    results = pipeline.search_similar_stories(
        f"stories about {char_name}",
        top_k=5
    )
    
    # Extract context
    contexts = [r['text'] for r in results]
    
    # Create profile
    profile = kg.create_character_profile(char_name, contexts)
    kg.add_character(profile)
    
    print(f"✓ Added {char_name}")

# Save updated library
kg.export_character_library("character_library.json")
```

**Expected Cost: ~$0.50-1.00** (GPT-4 for character profiles)
**Time: 20-30 minutes**

---

## ✍️ Phase 4: Story Generation (Week 4-5)

### Step 4.1: Generate Test Stories

```python
from story_generator import StoryGenerator, STORY_THEMES
from mythology_pipeline import MythologyPipeline, Config
import os

# Initialize
config = Config(openai_api_key=os.getenv("OPENAI_API_KEY"))
pipeline = MythologyPipeline(config)
generator = StoryGenerator(pipeline, model="gpt-4")

# Generate first story
story = generator.create_story_from_theme(
    theme="Krishna stealing butter",
    age_range="5-8 years"
)

# Save in multiple formats
generator.save_story(story, "story_1.json", format="json")
generator.save_story(story, "story_1.md", format="markdown")
generator.save_story(story, "story_1.txt", format="script")

print(f"✓ Generated: {story.title}")
print(f"  Characters: {len(story.characters)}")
print(f"  Scenes: {len(story.scenes)}")
```

**Expected Cost per story: ~$0.20-0.40** (GPT-4)
**Time per story: 30-60 seconds**

### Step 4.2: Batch Generate Stories

```python
# Generate 10 stories
themes = STORY_THEMES[:10]

stories = generator.generate_batch_stories(
    themes=themes,
    age_range="5-8 years"
)

# Save all
for i, story in enumerate(stories, 1):
    generator.save_story(story, f"stories/story_{i:02d}.json")

print(f"✓ Generated {len(stories)} stories")
```

**Expected Cost: ~$2-4** for 10 stories
**Time: 10-15 minutes**

---

## 🎨 Phase 5: Image Generation (Week 5-6)

### Step 5.1: Setup Image Generation

```python
import replicate
import os

# Using Stable Diffusion via Replicate
os.environ["REPLICATE_API_TOKEN"] = "your_token_here"

def generate_character_image(character_profile, age_variant="child"):
    """Generate character image"""
    from character_knowledge_graph import CharacterKnowledgeGraph
    
    kg = CharacterKnowledgeGraph(llm_api_key=os.getenv("OPENAI_API_KEY"))
    kg.import_character_library("character_library.json")
    
    prompt = kg.get_character_image_prompt(
        character_profile.name,
        age_variant=age_variant
    )
    
    output = replicate.run(
        "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
        input={
            "prompt": prompt,
            "negative_prompt": "scary, violent, dark, ugly, distorted",
            "width": 1024,
            "height": 1024
        }
    )
    
    return output[0]  # URL to image

# Test with Krishna
from character_knowledge_graph import COMMON_CHARACTERS, CharacterProfile

krishna = CharacterProfile(**COMMON_CHARACTERS["Krishna"])
image_url = generate_character_image(krishna, age_variant="child")
print(f"Image URL: {image_url}")
```

**Cost per image: ~$0.0023**
**Time per image: 5-10 seconds**

### Step 5.2: Generate Story Images

```python
import json
from pathlib import Path

def generate_story_images(story_json_path):
    """Generate all images for a story"""
    
    with open(story_json_path) as f:
        story_data = json.load(f)
    
    images = {
        "characters": {},
        "scenes": {}
    }
    
    # Generate character images
    for char in story_data["characters"]:
        print(f"Generating image for {char['name']}...")
        prompt = char["visual_prompt"]
        image_url = generate_image(prompt)
        images["characters"][char["name"]] = image_url
    
    # Generate scene images
    for scene in story_data["scenes"]:
        print(f"Generating scene {scene['scene_number']}...")
        prompt = scene["visual_prompt"]
        image_url = generate_image(prompt)
        images["scenes"][scene["scene_number"]] = image_url
    
    # Save image manifest
    output_path = Path(story_json_path).stem + "_images.json"
    with open(output_path, 'w') as f:
        json.dump(images, f, indent=2)
    
    return images

def generate_image(prompt):
    """Generic image generation"""
    output = replicate.run(
        "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
        input={"prompt": prompt + ", children's illustration, vibrant"}
    )
    return output[0]

# Generate images for all stories
story_files = Path("stories").glob("story_*.json")
for story_file in story_files:
    print(f"\nProcessing {story_file}...")
    generate_story_images(story_file)
```

**Cost per story: ~$0.05-0.15** (5-10 images)
**Time per story: 1-2 minutes**

---

## 🎙️ Phase 6: Voice & Video (Week 6-7)

### Step 6.1: Setup Voice Generation

```python
from elevenlabs import generate, set_api_key, voices
import os

set_api_key(os.getenv("ELEVENLABS_API_KEY"))

# List available voices
available_voices = voices()
print("Available voices:")
for voice in available_voices:
    print(f"  - {voice.name}")

def generate_narration(text, output_file, voice_name="Bella"):
    """Generate voice narration"""
    audio = generate(
        text=text,
        voice=voice_name,
        model="eleven_monolingual_v1"
    )
    
    with open(output_file, 'wb') as f:
        f.write(audio)
    
    print(f"✓ Saved audio to {output_file}")

# Test
generate_narration(
    "Once upon a time in ancient India...",
    "test_narration.mp3"
)
```

### Step 6.2: Create Video from Story

```python
from moviepy.editor import *
import requests
from io import BytesIO

def create_story_video(story_json, images_json, output_file):
    """Create video from story components"""
    
    # Load data
    with open(story_json) as f:
        story = json.load(f)
    with open(images_json) as f:
        images = json.load(f)
    
    clips = []
    
    # Create clip for each scene
    for scene in story["scenes"]:
        scene_num = scene["scene_number"]
        duration = scene["duration_seconds"]
        
        # Download image
        img_url = images["scenes"][scene_num]
        response = requests.get(img_url)
        img = ImageClip(BytesIO(response.content).read())
        
        # Set duration
        img = img.set_duration(duration)
        
        # Add zoom effect (Ken Burns)
        img = img.resize(lambda t: 1 + 0.05*t)
        
        clips.append(img)
    
    # Concatenate clips
    video = concatenate_videoclips(clips, method="compose")
    
    # Generate narration
    narration_file = "temp_narration.mp3"
    generate_narration(story["narration"], narration_file)
    
    # Add audio
    audio = AudioFileClip(narration_file)
    video = video.set_audio(audio)
    
    # Add background music (optional)
    # bgm = AudioFileClip("background_music.mp3").volumex(0.2)
    # final_audio = CompositeAudioClip([audio, bgm])
    # video = video.set_audio(final_audio)
    
    # Export
    video.write_videofile(
        output_file,
        fps=24,
        codec='libx264',
        audio_codec='aac'
    )
    
    print(f"✓ Video saved to {output_file}")

# Create video for first story
create_story_video(
    "stories/story_01.json",
    "stories/story_01_images.json",
    "videos/story_01.mp4"
)
```

**Cost per video:**
- Voice: ~$0.05-0.15 (ElevenLabs)
- Images: ~$0.10 (already generated)
- **Total: ~$0.15-0.25 per video**

**Time per video: 3-5 minutes**

---

## 📊 Phase 7: Automation & Scaling (Week 7-8)

### Step 7.1: Create End-to-End Pipeline

```python
class ContentPipeline:
    """Complete automation pipeline"""
    
    def __init__(self, config):
        self.story_pipeline = MythologyPipeline(config)
        self.story_generator = StoryGenerator(self.story_pipeline)
        self.character_kg = CharacterKnowledgeGraph(config.openai_api_key)
        self.character_kg.import_character_library("character_library.json")
    
    def generate_complete_story(self, theme, output_dir):
        """Generate story + images + video"""
        
        print(f"🎬 Creating content for: {theme}")
        
        # 1. Generate story
        print("  [1/4] Generating story...")
        story = self.story_generator.create_story_from_theme(theme)
        story_file = f"{output_dir}/story.json"
        self.story_generator.save_story(story, story_file)
        
        # 2. Generate images
        print("  [2/4] Generating images...")
        images = generate_story_images(story_file)
        
        # 3. Generate narration
        print("  [3/4] Generating narration...")
        audio_file = f"{output_dir}/narration.mp3"
        generate_narration(story.narration, audio_file)
        
        # 4. Create video
        print("  [4/4] Creating video...")
        video_file = f"{output_dir}/video.mp4"
        create_story_video(
            story_file,
            f"{output_dir}/story_images.json",
            video_file
        )
        
        print(f"✅ Complete! Video: {video_file}")
        
        return {
            "story": story_file,
            "video": video_file,
            "audio": audio_file
        }

# Run pipeline
pipeline = ContentPipeline(config)

themes = [
    "Krishna stealing butter",
    "Hanuman trying to eat the sun",
    "Ganesha writing the Mahabharata"
]

for i, theme in enumerate(themes, 1):
    output_dir = f"output/story_{i:02d}"
    os.makedirs(output_dir, exist_ok=True)
    pipeline.generate_complete_story(theme, output_dir)
```

### Step 7.2: Batch Processing Script

```python
# batch_generate.py
import argparse
from pathlib import Path

def batch_generate(themes_file, output_dir, max_stories=None):
    """Generate multiple stories in batch"""
    
    # Load themes
    with open(themes_file) as f:
        themes = [line.strip() for line in f if line.strip()]
    
    if max_stories:
        themes = themes[:max_stories]
    
    # Setup pipeline
    config = Config(openai_api_key=os.getenv("OPENAI_API_KEY"))
    pipeline = ContentPipeline(config)
    
    # Process each theme
    results = []
    for i, theme in enumerate(themes, 1):
        try:
            story_dir = Path(output_dir) / f"story_{i:03d}"
            story_dir.mkdir(parents=True, exist_ok=True)
            
            result = pipeline.generate_complete_story(theme, str(story_dir))
            results.append({"theme": theme, "status": "success", **result})
            
        except Exception as e:
            print(f"❌ Error with '{theme}': {e}")
            results.append({"theme": theme, "status": "failed", "error": str(e)})
    
    # Save results manifest
    with open(Path(output_dir) / "manifest.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Batch complete: {len([r for r in results if r['status']=='success'])}/{len(themes)} succeeded")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("themes_file", help="File with themes (one per line)")
    parser.add_argument("--output", default="output", help="Output directory")
    parser.add_argument("--max", type=int, help="Maximum number of stories")
    
    args = parser.parse_args()
    batch_generate(args.themes_file, args.output, args.max)
```

Usage:
```bash
# Create themes file
echo "Krishna stealing butter
Hanuman's childhood adventures
Ganesha and the moon" > themes.txt

# Run batch generation
python batch_generate.py themes.txt --output videos/ --max 10
```

---

## 💰 Cost Summary

### Monthly Costs for 30 Videos:

| Service | Cost |
|---------|------|
| OpenAI API (stories) | $8-12 |
| ElevenLabs (voice) | $22 |
| Replicate (images) | $4-6 |
| Redis hosting | FREE (local) |
| **Total** | **$34-40/month** |

### Per Video Breakdown:
- Story generation: $0.30
- Images (8-10): $0.15
- Voice narration: $0.10
- **Total per video: ~$0.55**

---

## 🎯 Success Metrics

**Week 8 Goals:**
- ✅ 20+ stories in vector DB
- ✅ 15+ character profiles
- ✅ 10 complete videos generated
- ✅ <5 minutes per video generation
- ✅ Consistent visual style

---

## 🔄 Next Steps

1. **Optimize costs**: Use GPT-3.5 for drafts, GPT-4 for polish
2. **Add caching**: Store frequently used prompts
3. **Quality control**: Add manual review step
4. **Upload automation**: Auto-upload to YouTube
5. **Analytics**: Track which stories perform best

---

## 🐛 Common Issues & Solutions

**Issue: Redis connection refused**
```bash
docker start redis-stack
redis-cli ping
```

**Issue: OpenAI rate limits**
```python
from tenacity import retry, wait_exponential

@retry(wait=wait_exponential(min=1, max=60))
def generate_with_retry():
    return llm.generate(prompt)
```

**Issue: Image generation fails**
- Check Replicate API token
- Verify prompt isn't too complex
- Add negative prompts to avoid bad outputs

**Issue: Video encoding errors**
```bash
# Install ffmpeg
brew install ffmpeg  # macOS
sudo apt install ffmpeg  # Linux
```

---

## 📈 Scaling Beyond MVP

**To 100+ videos/month:**
1. Switch to dedicated Redis instance
2. Use S3 for asset storage
3. Add Celery for async processing
4. Implement proper logging/monitoring
5. Add CDN for video delivery

Your Python + LangChain + Knowledge Graph expertise makes you perfectly positioned to build this! Start with Phase 1 today.
