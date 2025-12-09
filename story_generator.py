"""
Story Generator Module
Extracts and adapts stories for children using LLMs and Redis vector search
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import json
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from mythology_pipeline import MythologyPipeline, Config


# Output models
class Character(BaseModel):
    name: str = Field(description="Character name")
    role: str = Field(description="Role in story (protagonist, antagonist, helper, etc.)")
    description: str = Field(description="Brief character description")
    visual_prompt: str = Field(description="Stable Diffusion prompt for character image")


class Scene(BaseModel):
    scene_number: int = Field(description="Scene sequence number")
    location: str = Field(description="Where the scene takes place")
    description: str = Field(description="What happens in this scene")
    characters: List[str] = Field(description="Characters present in this scene")
    visual_prompt: str = Field(description="Stable Diffusion prompt for scene image")
    duration_seconds: int = Field(description="Estimated duration in seconds")


class Story(BaseModel):
    title: str = Field(description="Story title")
    age_range: str = Field(description="Target age range (e.g., '5-8 years')")
    summary: str = Field(description="2-3 sentence story summary")
    moral: str = Field(description="Moral or lesson of the story")
    characters: List[Character] = Field(description="List of main characters")
    scenes: List[Scene] = Field(description="List of scenes")
    narration: str = Field(description="Complete narration script for voiceover")
    total_duration: int = Field(description="Total video duration in seconds")
    source_book: str = Field(description="Original source book")


class StoryGenerator:
    """Generate child-friendly stories from mythology texts"""
    
    def __init__(self, pipeline: MythologyPipeline, model: str = "gpt-4"):
        self.pipeline = pipeline
        self.llm = ChatOpenAI(
            model=model,
            temperature=0.7,
            openai_api_key=pipeline.config.openai_api_key
        )
        self.story_parser = PydanticOutputParser(pydantic_object=Story)
    
    def find_stories(
        self, 
        theme: str, 
        category: Optional[str] = None,
        num_sources: int = 5
    ) -> List[Dict]:
        """Find relevant story sources from vector DB"""
        results = self.pipeline.search_similar_stories(
            query=theme,
            top_k=num_sources,
            category=category
        )
        return results
    
    def adapt_for_children(
        self,
        source_text: str,
        age_range: str = "5-8 years",
        target_duration: int = 300  # 5 minutes in seconds
    ) -> Story:
        """Adapt mythology text into child-friendly story"""
        
        # Create prompt template
        template = """You are an expert children's story writer specializing in Indian mythology.
        
Your task is to adapt the following mythological text into an engaging, age-appropriate story for children.

SOURCE TEXT:
{source_text}

REQUIREMENTS:
- Target age: {age_range}
- Target duration: {target_duration} seconds (~{target_minutes} minutes)
- Keep it simple, engaging, and age-appropriate
- Focus on positive values and clear moral lessons
- Avoid violence, fear, or complex philosophical concepts
- Use simple dialogue and vivid descriptions
- Break down into 4-6 scenes for visual storytelling
- Each scene should be 30-60 seconds

For each character, create a detailed visual description suitable for image generation.
For each scene, create a Stable Diffusion prompt for illustration.

Use vibrant, colorful, friendly imagery - think Pixar/Disney animation style.

{format_instructions}

IMPORTANT: Return ONLY the JSON object, no additional text or markdown.
"""
        
        prompt = ChatPromptTemplate.from_template(template)
        
        chain = prompt | self.llm
        
        response = chain.invoke({
            "source_text": source_text[:3000],  # Limit context
            "age_range": age_range,
            "target_duration": target_duration,
            "target_minutes": target_duration // 60,
            "format_instructions": self.story_parser.get_format_instructions()
        })
        
        # Parse response
        story = self.story_parser.parse(response.content)
        return story
    
    def create_story_from_theme(
        self,
        theme: str,
        category: Optional[str] = None,
        age_range: str = "5-8 years"
    ) -> Story:
        """End-to-end story creation from theme"""
        
        print(f"🔍 Finding stories about: '{theme}'...")
        
        # Find relevant sources
        sources = self.find_stories(theme, category, num_sources=3)
        
        if not sources:
            raise ValueError(f"No stories found for theme: {theme}")
        
        print(f"✓ Found {len(sources)} relevant sources")
        print(f"📖 Using: {sources[0]['book']}")
        
        # Combine top sources for context
        combined_text = "\n\n".join([s['text'] for s in sources[:2]])
        
        print(f"✍️  Adapting story for children...")
        
        # Generate story
        story = self.adapt_for_children(
            source_text=combined_text,
            age_range=age_range
        )
        
        # Add source information
        story.source_book = sources[0]['book']
        
        print(f"✓ Story created: '{story.title}'")
        print(f"   - {len(story.characters)} characters")
        print(f"   - {len(story.scenes)} scenes")
        print(f"   - {story.total_duration}s duration")
        
        return story
    
    def generate_batch_stories(
        self,
        themes: List[str],
        category: Optional[str] = None,
        age_range: str = "5-8 years"
    ) -> List[Story]:
        """Generate multiple stories from theme list"""
        stories = []
        
        for i, theme in enumerate(themes, 1):
            print(f"\n{'='*60}")
            print(f"Story {i}/{len(themes)}: {theme}")
            print('='*60)
            
            try:
                story = self.create_story_from_theme(theme, category, age_range)
                stories.append(story)
            except Exception as e:
                print(f"✗ Error generating story: {e}")
                continue
        
        return stories
    
    def export_story(self, story: Story, format: str = "json") -> str:
        """Export story in various formats"""
        
        if format == "json":
            return story.model_dump_json(indent=2)
        
        elif format == "markdown":
            md = f"# {story.title}\n\n"
            md += f"**Age Range:** {story.age_range}\n\n"
            md += f"**Summary:** {story.summary}\n\n"
            md += f"**Moral:** {story.moral}\n\n"
            
            md += f"## Characters\n\n"
            for char in story.characters:
                md += f"- **{char.name}** ({char.role}): {char.description}\n"
            
            md += f"\n## Story\n\n"
            for scene in story.scenes:
                md += f"### Scene {scene.scene_number}: {scene.location}\n\n"
                md += f"{scene.description}\n\n"
            
            md += f"## Narration\n\n{story.narration}\n"
            
            return md
        
        elif format == "script":
            script = f"TITLE: {story.title}\n"
            script += f"DURATION: {story.total_duration}s\n"
            script += f"="*60 + "\n\n"
            
            for scene in story.scenes:
                script += f"SCENE {scene.scene_number} - {scene.location.upper()}\n"
                script += f"Duration: {scene.duration_seconds}s\n"
                script += f"Characters: {', '.join(scene.characters)}\n\n"
                script += f"{scene.description}\n\n"
                script += f"Visual: {scene.visual_prompt}\n\n"
                script += "-"*60 + "\n\n"
            
            script += "NARRATION:\n"
            script += "="*60 + "\n"
            script += story.narration
            
            return script
        
        else:
            raise ValueError(f"Unknown format: {format}")
    
    def save_story(self, story: Story, filename: str, format: str = "json"):
        """Save story to file"""
        content = self.export_story(story, format)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ Story saved to: {filename}")


# Example story themes for generation
STORY_THEMES = [
    "Krishna stealing butter as a child",
    "Young Hanuman trying to eat the sun",
    "Ganesha and the moon story",
    "The clever monkey king",
    "A wise minister solves a problem",
    "The honest woodcutter and the golden axe",
    "The lion and the clever rabbit",
    "The story of truth and honesty",
    "How the elephant got his trunk",
    "The magical peacock feather"
]


# Example usage
if __name__ == "__main__":
    import os
    from mythology_pipeline import Config
    
    # Initialize
    config = Config(openai_api_key=os.getenv("OPENAI_API_KEY"))
    pipeline = MythologyPipeline(config)
    generator = StoryGenerator(pipeline, model="gpt-4")
    
    # Test single story generation
    print("="*60)
    print("TESTING STORY GENERATION")
    print("="*60)
    
    # Generate a test story
    story = generator.create_story_from_theme(
        theme="Krishna stealing butter",
        age_range="5-8 years"
    )
    
    # Print story details
    print("\n" + "="*60)
    print("GENERATED STORY")
    print("="*60)
    
    print(f"\nTitle: {story.title}")
    print(f"Age Range: {story.age_range}")
    print(f"Duration: {story.total_duration}s")
    print(f"\nSummary: {story.summary}")
    print(f"\nMoral: {story.moral}")
    
    print(f"\nCharacters:")
    for char in story.characters:
        print(f"  - {char.name} ({char.role})")
    
    print(f"\nScenes:")
    for scene in story.scenes:
        print(f"  Scene {scene.scene_number}: {scene.location} ({scene.duration_seconds}s)")
    
    # Save in different formats
    generator.save_story(story, "story_output.json", format="json")
    generator.save_story(story, "story_output.md", format="markdown")
    generator.save_story(story, "story_output.txt", format="script")
    
    print("\n" + "="*60)
    print("BATCH GENERATION TEST")
    print("="*60)
    
    # Generate multiple stories (commented out to avoid high API costs in demo)
    # stories = generator.generate_batch_stories(
    #     themes=STORY_THEMES[:3],  # First 3 themes
    #     age_range="5-8 years"
    # )
    # 
    # print(f"\n✓ Generated {len(stories)} stories")
    # 
    # # Save all stories
    # for i, story in enumerate(stories, 1):
    #     generator.save_story(story, f"story_{i}.json", format="json")
