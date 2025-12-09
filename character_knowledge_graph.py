"""
Character Knowledge Graph Manager
Extracts and manages character information for consistent storytelling
"""

from typing import List, Dict, Optional, Set
from dataclasses import dataclass
import json
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
import re


class CharacterProfile(BaseModel):
    """Complete character profile for consistent generation"""
    name: str = Field(description="Character name")
    alternate_names: List[str] = Field(default=[], description="Other names or titles")
    category: str = Field(description="deity, human, animal, demon, etc.")
    appearance: Dict[str, str] = Field(description="Physical characteristics")
    personality_traits: List[str] = Field(description="Key personality traits")
    powers_abilities: List[str] = Field(default=[], description="Special powers or abilities")
    relationships: Dict[str, List[str]] = Field(default={}, description="Relationships with other characters")
    source_texts: List[str] = Field(description="Books/texts where character appears")
    child_friendly_description: str = Field(description="Simple description for children")
    visual_prompt_template: str = Field(description="Base Stable Diffusion prompt")
    age_variants: Dict[str, str] = Field(default={}, description="Different age representations")


class CharacterKnowledgeGraph:
    """Manage character relationships and consistency"""
    
    def __init__(self, llm_api_key: str, model: str = "gpt-4"):
        self.llm = ChatOpenAI(
            model=model,
            temperature=0.3,
            openai_api_key=llm_api_key
        )
        self.characters: Dict[str, CharacterProfile] = {}
        self.relationships: Dict[str, Set[str]] = {}
    
    def extract_characters_from_text(self, text: str, source_book: str) -> List[Dict]:
        """Extract character mentions from text using LLM"""
        
        template = """Extract all character names mentioned in this text from Indian mythology.
        
TEXT:
{text}

Return a JSON list of characters with:
- name: Character's primary name
- mentions: Number of times mentioned
- context: Brief context of their role in this text

Return ONLY a JSON array, no additional text.
Example: [{"name": "Krishna", "mentions": 5, "context": "protagonist, divine child"}]
"""
        
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm
        
        response = chain.invoke({"text": text[:2000]})
        
        try:
            # Extract JSON from response
            content = response.content
            # Find JSON array in response
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                characters = json.loads(match.group())
                return characters
            return []
        except:
            return []
    
    def create_character_profile(
        self, 
        character_name: str, 
        context_texts: List[str]
    ) -> CharacterProfile:
        """Generate comprehensive character profile"""
        
        template = """Create a detailed character profile for {character_name} from Indian mythology.

Use these text excerpts for context:
{context}

Create a profile that includes:
1. Physical appearance details
2. Personality traits
3. Powers/abilities (if any)
4. Key relationships (family, friends, enemies)
5. A child-friendly description (2-3 sentences)
6. A Stable Diffusion prompt template for consistent image generation

Style Guide for Images:
- Vibrant, colorful, friendly
- Pixar/Disney animation style
- Non-threatening, age-appropriate
- Indian artistic elements
- Consistent across all images

Return a JSON object with this structure:
{{
    "name": "string",
    "alternate_names": ["string"],
    "category": "deity|human|animal|demon",
    "appearance": {{
        "skin_color": "string",
        "clothing": "string",
        "distinctive_features": "string",
        "accessories": "string"
    }},
    "personality_traits": ["string"],
    "powers_abilities": ["string"],
    "relationships": {{
        "family": ["string"],
        "friends": ["string"],
        "enemies": ["string"]
    }},
    "source_texts": ["string"],
    "child_friendly_description": "string",
    "visual_prompt_template": "string",
    "age_variants": {{
        "child": "string - prompt for child version",
        "youth": "string - prompt for young adult",
        "adult": "string - prompt for adult version"
    }}
}}

Return ONLY the JSON object.
"""
        
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm
        
        combined_context = "\n\n".join(context_texts[:3])
        
        response = chain.invoke({
            "character_name": character_name,
            "context": combined_context
        })
        
        # Parse JSON response
        try:
            content = response.content
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                profile_dict = json.loads(match.group())
                profile = CharacterProfile(**profile_dict)
                return profile
        except Exception as e:
            print(f"Error parsing character profile: {e}")
            # Return minimal profile
            return CharacterProfile(
                name=character_name,
                category="unknown",
                appearance={},
                personality_traits=[],
                source_texts=["unknown"],
                child_friendly_description=f"A character from Indian mythology named {character_name}",
                visual_prompt_template=f"{character_name}, Indian mythology character, colorful, friendly, children's book illustration"
            )
    
    def add_character(self, profile: CharacterProfile):
        """Add character to knowledge graph"""
        self.characters[profile.name.lower()] = profile
        
        # Build relationship graph
        for rel_type, names in profile.relationships.items():
            for related_name in names:
                key = f"{profile.name}:{related_name}"
                if key not in self.relationships:
                    self.relationships[key] = set()
                self.relationships[key].add(rel_type)
    
    def get_character(self, name: str) -> Optional[CharacterProfile]:
        """Retrieve character profile"""
        return self.characters.get(name.lower())
    
    def find_related_characters(self, character_name: str) -> Dict[str, List[str]]:
        """Find all characters related to given character"""
        related = {}
        
        for key, rel_types in self.relationships.items():
            if character_name.lower() in key.lower():
                parts = key.split(":")
                other = parts[1] if parts[0].lower() == character_name.lower() else parts[0]
                for rel_type in rel_types:
                    if rel_type not in related:
                        related[rel_type] = []
                    related[rel_type].append(other)
        
        return related
    
    def get_character_image_prompt(
        self,
        character_name: str,
        age_variant: str = "adult",
        scene_context: str = ""
    ) -> str:
        """Generate consistent image prompt for character"""
        
        profile = self.get_character(character_name)
        if not profile:
            return f"{character_name}, Indian mythology, colorful illustration, {scene_context}"
        
        # Use age-specific variant if available
        if age_variant in profile.age_variants:
            base_prompt = profile.age_variants[age_variant]
        else:
            base_prompt = profile.visual_prompt_template
        
        # Add scene context
        if scene_context:
            full_prompt = f"{base_prompt}, {scene_context}"
        else:
            full_prompt = base_prompt
        
        # Add consistent style parameters
        style = "children's book illustration, vibrant colors, friendly, Pixar style, Indian art elements"
        
        return f"{full_prompt}, {style}"
    
    def export_character_library(self, filename: str):
        """Export all characters to JSON file"""
        data = {
            name: profile.model_dump() 
            for name, profile in self.characters.items()
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Exported {len(data)} characters to {filename}")
    
    def import_character_library(self, filename: str):
        """Import characters from JSON file"""
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for name, profile_dict in data.items():
            profile = CharacterProfile(**profile_dict)
            self.add_character(profile)
        
        print(f"✓ Imported {len(data)} characters from {filename}")
    
    def get_statistics(self) -> Dict:
        """Get knowledge graph statistics"""
        return {
            "total_characters": len(self.characters),
            "total_relationships": len(self.relationships),
            "categories": self._count_by_category(),
            "most_connected": self._get_most_connected(top_n=5)
        }
    
    def _count_by_category(self) -> Dict[str, int]:
        """Count characters by category"""
        counts = {}
        for profile in self.characters.values():
            cat = profile.category
            counts[cat] = counts.get(cat, 0) + 1
        return counts
    
    def _get_most_connected(self, top_n: int = 5) -> List[Dict]:
        """Find most connected characters"""
        connection_counts = {}
        
        for key in self.relationships.keys():
            for name in key.split(":"):
                name_lower = name.lower()
                connection_counts[name_lower] = connection_counts.get(name_lower, 0) + 1
        
        sorted_chars = sorted(
            connection_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:top_n]
        
        return [{"name": name, "connections": count} for name, count in sorted_chars]


# Pre-defined character profiles for common characters
COMMON_CHARACTERS = {
    "Krishna": {
        "name": "Krishna",
        "alternate_names": ["Kanha", "Gopala", "Govinda"],
        "category": "deity",
        "appearance": {
            "skin_color": "blue",
            "clothing": "yellow dhoti, peacock feather crown",
            "distinctive_features": "flute, charming smile",
            "accessories": "peacock feather, flute"
        },
        "personality_traits": ["playful", "wise", "mischievous", "compassionate"],
        "powers_abilities": ["divine powers", "wisdom", "charm"],
        "relationships": {
            "family": ["Yashoda (mother)", "Nanda (father)", "Balarama (brother)"],
            "friends": ["Arjuna", "Sudama", "Gopis"],
            "enemies": ["Kansa", "demons"]
        },
        "source_texts": ["Bhagavata Purana", "Mahabharata"],
        "child_friendly_description": "Krishna is a playful blue-skinned boy who loves butter and playing his flute. He's very wise and always helps his friends.",
        "visual_prompt_template": "Krishna, blue-skinned divine child, yellow dhoti, peacock feather in hair, holding flute, cheerful expression",
        "age_variants": {
            "child": "young Krishna, 5-8 years old, chubby cheeks, playful, stealing butter, barefoot",
            "youth": "teenage Krishna, handsome, flute player, dancing with gopis",
            "adult": "adult Krishna, majestic, charioteer, teacher"
        }
    },
    "Hanuman": {
        "name": "Hanuman",
        "alternate_names": ["Bajrangbali", "Maruti", "Pavanputra"],
        "category": "deity",
        "appearance": {
            "skin_color": "golden or orange",
            "clothing": "red dhoti or loincloth",
            "distinctive_features": "monkey face, muscular build, long tail",
            "accessories": "mace (gada), often shown flying"
        },
        "personality_traits": ["brave", "loyal", "strong", "devoted", "humble"],
        "powers_abilities": ["superhuman strength", "ability to fly", "shape-shifting", "immortality"],
        "relationships": {
            "family": ["Anjana (mother)", "Vayu (father)"],
            "friends": ["Rama", "Sita", "Lakshman"],
            "enemies": ["Ravana", "demons"]
        },
        "source_texts": ["Ramayana", "Hanuman Chalisa"],
        "child_friendly_description": "Hanuman is a brave monkey warrior who is very strong and can fly. He's loyal to his friends and always helps those in need.",
        "visual_prompt_template": "Hanuman, monkey deity, golden-orange fur, red dhoti, muscular, friendly face, holding mace",
        "age_variants": {
            "child": "baby Hanuman, cute monkey child, trying to catch the sun, playful",
            "youth": "young Hanuman, learning powers, energetic, brave",
            "adult": "adult Hanuman, mighty warrior, flying, carrying mountain"
        }
    },
    "Ganesha": {
        "name": "Ganesha",
        "alternate_names": ["Ganapati", "Vinayaka", "Lambodara"],
        "category": "deity",
        "appearance": {
            "skin_color": "pink or red",
            "clothing": "yellow or red dhoti, ornate jewelry",
            "distinctive_features": "elephant head, big belly, four arms",
            "accessories": "modak (sweet), lotus, axe, rope"
        },
        "personality_traits": ["wise", "kind", "playful", "intelligent", "obstacle-remover"],
        "powers_abilities": ["removes obstacles", "grants wisdom", "divine powers"],
        "relationships": {
            "family": ["Shiva (father)", "Parvati (mother)", "Kartikeya (brother)"],
            "friends": ["his vehicle - mouse"],
            "enemies": ["none typically"]
        },
        "source_texts": ["Shiva Purana", "Ganesha Purana"],
        "child_friendly_description": "Ganesha is a friendly elephant-headed god who loves sweets. He's very smart and helps remove problems for everyone.",
        "visual_prompt_template": "Ganesha, elephant-headed deity, pink skin, yellow dhoti, holding modak sweet, friendly smile, four arms",
        "age_variants": {
            "child": "baby Ganesha, cute elephant child, playing, eating modaks",
            "youth": "young Ganesha, learning, writing, friendly",
            "adult": "adult Ganesha, majestic, four arms, blessing devotees"
        }
    }
}


# Example usage
if __name__ == "__main__":
    import os
    
    # Initialize knowledge graph
    kg = CharacterKnowledgeGraph(llm_api_key=os.getenv("OPENAI_API_KEY"))
    
    # Add pre-defined characters
    print("Adding pre-defined characters...")
    for char_data in COMMON_CHARACTERS.values():
        profile = CharacterProfile(**char_data)
        kg.add_character(profile)
        print(f"✓ Added {profile.name}")
    
    # Test character retrieval
    print("\n" + "="*60)
    print("CHARACTER PROFILE TEST")
    print("="*60)
    
    krishna = kg.get_character("Krishna")
    if krishna:
        print(f"\nName: {krishna.name}")
        print(f"Category: {krishna.category}")
        print(f"Description: {krishna.child_friendly_description}")
        print(f"\nPersonality: {', '.join(krishna.personality_traits)}")
        print(f"\nVisual Prompt (child):")
        print(kg.get_character_image_prompt("Krishna", age_variant="child"))
    
    # Test relationships
    print("\n" + "="*60)
    print("RELATIONSHIP TEST")
    print("="*60)
    
    related = kg.find_related_characters("Krishna")
    print(f"\nCharacters related to Krishna:")
    for rel_type, names in related.items():
        print(f"  {rel_type}: {', '.join(names)}")
    
    # Statistics
    print("\n" + "="*60)
    print("KNOWLEDGE GRAPH STATISTICS")
    print("="*60)
    
    stats = kg.get_statistics()
    print(f"\nTotal Characters: {stats['total_characters']}")
    print(f"Total Relationships: {stats['total_relationships']}")
    print(f"\nCategories:")
    for cat, count in stats['categories'].items():
        print(f"  {cat}: {count}")
    print(f"\nMost Connected:")
    for char in stats['most_connected']:
        print(f"  {char['name']}: {char['connections']} connections")
    
    # Export character library
    kg.export_character_library("character_library.json")
    
    # Test image prompt generation
    print("\n" + "="*60)
    print("IMAGE PROMPT GENERATION TEST")
    print("="*60)
    
    scenes = [
        ("Krishna", "child", "in a garden, stealing butter from a pot"),
        ("Hanuman", "youth", "flying over ocean, carrying message"),
        ("Ganesha", "child", "sitting, writing with trunk, surrounded by books")
    ]
    
    for char_name, age, context in scenes:
        prompt = kg.get_character_image_prompt(char_name, age, context)
        print(f"\n{char_name} ({age}):")
        print(f"Scene: {context}")
        print(f"Prompt: {prompt[:150]}...")
