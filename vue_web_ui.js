// Vue.js Web UI for Mythology Story Generator
// Single File Component Structure

// ============================================================================
// Main App Component (App.vue)
// ============================================================================

const App = {
  template: `
    <div id="app" class="min-h-screen bg-gradient-to-br from-orange-50 to-purple-50">
      <!-- Header -->
      <header class="bg-white shadow-md border-b-4 border-orange-500">
        <div class="container mx-auto px-6 py-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-3">
              <div class="text-4xl">📚</div>
              <div>
                <h1 class="text-2xl font-bold text-orange-600">Mythology Story Studio</h1>
                <p class="text-sm text-gray-600">AI-Powered Indian Mythology for Kids</p>
              </div>
            </div>
            <div class="flex items-center space-x-4">
              <div class="text-sm text-gray-600">
                <span class="font-semibold">{{ stats.totalStories }}</span> stories
              </div>
              <div class="text-sm text-gray-600">
                <span class="font-semibold">{{ stats.totalCharacters }}</span> characters
              </div>
            </div>
          </div>
        </div>
      </header>

      <!-- Main Content -->
      <div class="container mx-auto px-6 py-8">
        <!-- Navigation Tabs -->
        <div class="bg-white rounded-lg shadow-md mb-6">
          <div class="flex border-b">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              @click="activeTab = tab.id"
              :class="[
                'px-6 py-3 font-medium transition-colors',
                activeTab === tab.id
                  ? 'text-orange-600 border-b-2 border-orange-600'
                  : 'text-gray-600 hover:text-orange-500'
              ]"
            >
              {{ tab.icon }} {{ tab.name }}
            </button>
          </div>
        </div>

        <!-- Tab Content -->
        <transition name="fade" mode="out-in">
          <component :is="currentTabComponent" :key="activeTab"></component>
        </transition>
      </div>
    </div>
  `,
  
  data() {
    return {
      activeTab: 'generate',
      tabs: [
        { id: 'generate', name: 'Generate Story', icon: '✨' },
        { id: 'library', name: 'Story Library', icon: '📖' },
        { id: 'characters', name: 'Characters', icon: '🎭' },
        { id: 'search', name: 'Search Books', icon: '🔍' },
        { id: 'pipeline', name: 'Pipeline Status', icon: '⚙️' }
      ],
      stats: {
        totalStories: 0,
        totalCharacters: 0
      }
    };
  },
  
  computed: {
    currentTabComponent() {
      return this.activeTab + '-tab';
    }
  },
  
  async mounted() {
    await this.loadStats();
  },
  
  methods: {
    async loadStats() {
      try {
        const response = await fetch('/api/stats');
        this.stats = await response.json();
      } catch (error) {
        console.error('Error loading stats:', error);
      }
    }
  }
};

// ============================================================================
// Generate Story Tab Component
// ============================================================================

const GenerateTab = {
  template: `
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Input Section -->
      <div class="bg-white rounded-lg shadow-md p-6">
        <h2 class="text-xl font-bold text-gray-800 mb-4">🎨 Create New Story</h2>
        
        <!-- Theme Input -->
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Story Theme or Topic
          </label>
          <textarea
            v-model="theme"
            rows="3"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
            placeholder="E.g., Krishna stealing butter, Hanuman's childhood adventures..."
          ></textarea>
        </div>

        <!-- Quick Theme Suggestions -->
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Quick Suggestions
          </label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="suggestion in themeSuggestions"
              :key="suggestion"
              @click="theme = suggestion"
              class="px-3 py-1 text-sm bg-orange-100 text-orange-700 rounded-full hover:bg-orange-200 transition-colors"
            >
              {{ suggestion }}
            </button>
          </div>
        </div>

        <!-- Category Filter -->
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Category
          </label>
          <select
            v-model="category"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500"
          >
            <option value="">All Categories</option>
            <option value="epic">Epic (Ramayana, Mahabharata)</option>
            <option value="fables">Fables (Panchatantra)</option>
            <option value="folk_tales">Folk Tales</option>
          </select>
        </div>

        <!-- Age Range -->
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Target Age Range
          </label>
          <select
            v-model="ageRange"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500"
          >
            <option value="3-5 years">3-5 years (Preschool)</option>
            <option value="5-8 years">5-8 years (Early Elementary)</option>
            <option value="8-12 years">8-12 years (Middle Elementary)</option>
          </select>
        </div>

        <!-- Duration -->
        <div class="mb-6">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Story Duration: {{ duration }} seconds ({{ Math.floor(duration/60) }} min)
          </label>
          <input
            v-model="duration"
            type="range"
            min="180"
            max="600"
            step="30"
            class="w-full"
          />
        </div>

        <!-- Generate Button -->
        <button
          @click="generateStory"
          :disabled="!theme || isGenerating"
          class="w-full bg-gradient-to-r from-orange-500 to-purple-600 text-white font-bold py-3 px-6 rounded-lg hover:from-orange-600 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span v-if="!isGenerating">✨ Generate Story</span>
          <span v-else>
            <svg class="inline-block animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Generating...
          </span>
        </button>

        <!-- Progress -->
        <div v-if="progress.length > 0" class="mt-4 space-y-2">
          <div
            v-for="(step, index) in progress"
            :key="index"
            class="flex items-center text-sm"
          >
            <span v-if="step.status === 'complete'" class="text-green-600 mr-2">✓</span>
            <span v-else-if="step.status === 'loading'" class="text-orange-600 mr-2">⏳</span>
            <span v-else class="text-gray-400 mr-2">○</span>
            <span :class="step.status === 'complete' ? 'text-green-600' : 'text-gray-600'">
              {{ step.text }}
            </span>
          </div>
        </div>
      </div>

      <!-- Preview Section -->
      <div class="bg-white rounded-lg shadow-md p-6">
        <h2 class="text-xl font-bold text-gray-800 mb-4">👁️ Preview</h2>
        
        <div v-if="!generatedStory" class="text-center py-12 text-gray-400">
          <div class="text-6xl mb-4">📖</div>
          <p>Your generated story will appear here</p>
        </div>

        <div v-else class="space-y-4">
          <!-- Story Title -->
          <div class="border-b pb-4">
            <h3 class="text-2xl font-bold text-orange-600 mb-2">
              {{ generatedStory.title }}
            </h3>
            <div class="flex items-center space-x-4 text-sm text-gray-600">
              <span>🎯 {{ generatedStory.age_range }}</span>
              <span>⏱️ {{ generatedStory.total_duration }}s</span>
              <span>🎬 {{ generatedStory.scenes.length }} scenes</span>
            </div>
          </div>

          <!-- Summary -->
          <div>
            <h4 class="font-semibold text-gray-700 mb-2">Summary</h4>
            <p class="text-gray-600">{{ generatedStory.summary }}</p>
          </div>

          <!-- Moral -->
          <div class="bg-purple-50 p-4 rounded-lg">
            <h4 class="font-semibold text-purple-700 mb-2">💡 Moral Lesson</h4>
            <p class="text-purple-600">{{ generatedStory.moral }}</p>
          </div>

          <!-- Characters -->
          <div>
            <h4 class="font-semibold text-gray-700 mb-2">Characters</h4>
            <div class="flex flex-wrap gap-2">
              <div
                v-for="char in generatedStory.characters"
                :key="char.name"
                class="flex items-center space-x-2 bg-orange-50 px-3 py-2 rounded-lg"
              >
                <div class="text-2xl">👤</div>
                <div class="text-sm">
                  <div class="font-medium text-gray-800">{{ char.name }}</div>
                  <div class="text-gray-600">{{ char.role }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Scenes Preview -->
          <div>
            <h4 class="font-semibold text-gray-700 mb-2">Scenes</h4>
            <div class="space-y-2">
              <div
                v-for="scene in generatedStory.scenes"
                :key="scene.scene_number"
                class="border-l-4 border-orange-400 pl-3 py-2"
              >
                <div class="font-medium text-gray-800">
                  Scene {{ scene.scene_number }}: {{ scene.location }}
                </div>
                <div class="text-sm text-gray-600">
                  {{ scene.description.substring(0, 100) }}...
                </div>
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex space-x-3 pt-4">
            <button
              @click="viewFullStory"
              class="flex-1 bg-orange-500 text-white py-2 px-4 rounded-lg hover:bg-orange-600 transition-colors"
            >
              📄 View Full Story
            </button>
            <button
              @click="generateImages"
              class="flex-1 bg-purple-500 text-white py-2 px-4 rounded-lg hover:bg-purple-600 transition-colors"
            >
              🎨 Generate Images
            </button>
          </div>
        </div>
      </div>
    </div>
  `,
  
  data() {
    return {
      theme: '',
      category: '',
      ageRange: '5-8 years',
      duration: 300,
      isGenerating: false,
      generatedStory: null,
      progress: [],
      themeSuggestions: [
        'Krishna stealing butter',
        'Young Hanuman and the sun',
        'Ganesha and the moon',
        'The clever rabbit and the lion',
        'The honest woodcutter',
        'Rama and Sita\'s friendship'
      ]
    };
  },
  
  methods: {
    async generateStory() {
      this.isGenerating = true;
      this.progress = [
        { text: 'Searching mythology texts...', status: 'loading' },
        { text: 'Extracting relevant stories...', status: 'pending' },
        { text: 'Adapting for children...', status: 'pending' },
        { text: 'Creating character profiles...', status: 'pending' },
        { text: 'Generating scenes...', status: 'pending' },
        { text: 'Finalizing story...', status: 'pending' }
      ];

      try {
        // Simulate progress updates
        for (let i = 0; i < this.progress.length; i++) {
          this.progress[i].status = 'loading';
          await new Promise(resolve => setTimeout(resolve, 800));
          this.progress[i].status = 'complete';
        }

        // API call to generate story
        const response = await fetch('/api/stories/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            theme: this.theme,
            category: this.category || null,
            age_range: this.ageRange,
            target_duration: this.duration
          })
        });

        this.generatedStory = await response.json();
      } catch (error) {
        console.error('Error generating story:', error);
        alert('Error generating story. Please try again.');
      } finally {
        this.isGenerating = false;
      }
    },
    
    viewFullStory() {
      // Navigate to full story view or open modal
      this.$emit('view-story', this.generatedStory);
    },
    
    generateImages() {
      // Navigate to image generation
      this.$emit('generate-images', this.generatedStory);
    }
  }
};

// ============================================================================
// Story Library Tab Component
// ============================================================================

const LibraryTab = {
  template: `
    <div>
      <!-- Filters -->
      <div class="bg-white rounded-lg shadow-md p-4 mb-6">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search stories..."
            class="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500"
          />
          <select
            v-model="filterCategory"
            class="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500"
          >
            <option value="">All Categories</option>
            <option value="epic">Epic</option>
            <option value="fables">Fables</option>
            <option value="folk_tales">Folk Tales</option>
          </select>
          <select
            v-model="filterAge"
            class="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500"
          >
            <option value="">All Ages</option>
            <option value="3-5">3-5 years</option>
            <option value="5-8">5-8 years</option>
            <option value="8-12">8-12 years</option>
          </select>
          <select
            v-model="sortBy"
            class="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500"
          >
            <option value="recent">Most Recent</option>
            <option value="popular">Most Popular</option>
            <option value="title">Title A-Z</option>
          </select>
        </div>
      </div>

      <!-- Story Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div
          v-for="story in filteredStories"
          :key="story.id"
          class="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-xl transition-shadow cursor-pointer"
          @click="selectStory(story)"
        >
          <!-- Thumbnail -->
          <div class="h-48 bg-gradient-to-br from-orange-200 to-purple-200 flex items-center justify-center">
            <div class="text-6xl">{{ story.emoji }}</div>
          </div>
          
          <!-- Content -->
          <div class="p-4">
            <h3 class="text-lg font-bold text-gray-800 mb-2">{{ story.title }}</h3>
            <p class="text-sm text-gray-600 mb-3 line-clamp-2">{{ story.summary }}</p>
            
            <div class="flex items-center justify-between text-xs text-gray-500">
              <span>🎯 {{ story.age_range }}</span>
              <span>⏱️ {{ Math.floor(story.total_duration/60) }}m</span>
              <span>🎬 {{ story.scenes.length }} scenes</span>
            </div>
            
            <div class="mt-3 flex space-x-2">
              <span
                v-for="tag in story.tags"
                :key="tag"
                class="px-2 py-1 text-xs bg-orange-100 text-orange-700 rounded-full"
              >
                {{ tag }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="filteredStories.length === 0" class="text-center py-12">
        <div class="text-6xl mb-4">📚</div>
        <p class="text-gray-500">No stories found. Try adjusting your filters.</p>
      </div>
    </div>
  `,
  
  data() {
    return {
      stories: [],
      searchQuery: '',
      filterCategory: '',
      filterAge: '',
      sortBy: 'recent'
    };
  },
  
  computed: {
    filteredStories() {
      let filtered = this.stories;
      
      if (this.searchQuery) {
        filtered = filtered.filter(s =>
          s.title.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
          s.summary.toLowerCase().includes(this.searchQuery.toLowerCase())
        );
      }
      
      if (this.filterCategory) {
        filtered = filtered.filter(s => s.category === this.filterCategory);
      }
      
      if (this.filterAge) {
        filtered = filtered.filter(s => s.age_range.includes(this.filterAge));
      }
      
      return filtered;
    }
  },
  
  async mounted() {
    await this.loadStories();
  },
  
  methods: {
    async loadStories() {
      try {
        const response = await fetch('/api/stories');
        this.stories = await response.json();
      } catch (error) {
        console.error('Error loading stories:', error);
      }
    },
    
    selectStory(story) {
      this.$emit('select-story', story);
    }
  }
};

// ============================================================================
// Characters Tab Component
// ============================================================================

const CharactersTab = {
  template: `
    <div>
      <!-- Character Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div
          v-for="character in characters"
          :key="character.name"
          class="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-xl transition-shadow"
        >
          <!-- Character Avatar -->
          <div class="h-64 bg-gradient-to-br from-yellow-200 to-orange-300 flex items-center justify-center">
            <div class="text-8xl">{{ character.emoji }}</div>
          </div>
          
          <!-- Character Info -->
          <div class="p-6">
            <div class="flex items-start justify-between mb-3">
              <div>
                <h3 class="text-xl font-bold text-gray-800">{{ character.name }}</h3>
                <p class="text-sm text-gray-500">{{ character.category }}</p>
              </div>
              <span class="px-3 py-1 text-xs bg-purple-100 text-purple-700 rounded-full">
                {{ character.stories_count }} stories
              </span>
            </div>
            
            <p class="text-sm text-gray-600 mb-4">
              {{ character.child_friendly_description }}
            </p>
            
            <!-- Traits -->
            <div class="mb-4">
              <h4 class="text-xs font-semibold text-gray-700 mb-2">Personality</h4>
              <div class="flex flex-wrap gap-1">
                <span
                  v-for="trait in character.personality_traits"
                  :key="trait"
                  class="px-2 py-1 text-xs bg-orange-50 text-orange-700 rounded"
                >
                  {{ trait }}
                </span>
              </div>
            </div>
            
            <!-- Actions -->
            <div class="flex space-x-2">
              <button
                @click="viewCharacter(character)"
                class="flex-1 bg-orange-500 text-white text-sm py-2 px-3 rounded hover:bg-orange-600 transition-colors"
              >
                View Details
              </button>
              <button
                @click="findStories(character)"
                class="flex-1 bg-purple-500 text-white text-sm py-2 px-3 rounded hover:bg-purple-600 transition-colors"
              >
                Find Stories
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Add Character Button -->
      <div class="mt-6 text-center">
        <button
          @click="addCharacter"
          class="bg-gradient-to-r from-orange-500 to-purple-600 text-white font-bold py-3 px-8 rounded-lg hover:from-orange-600 hover:to-purple-700 transition-all"
        >
          ➕ Add New Character
        </button>
      </div>
    </div>
  `,
  
  data() {
    return {
      characters: []
    };
  },
  
  async mounted() {
    await this.loadCharacters();
  },
  
  methods: {
    async loadCharacters() {
      try {
        const response = await fetch('/api/characters');
        this.characters = await response.json();
      } catch (error) {
        console.error('Error loading characters:', error);
      }
    },
    
    viewCharacter(character) {
      this.$emit('view-character', character);
    },
    
    findStories(character) {
      this.$emit('find-stories', character.name);
    },
    
    addCharacter() {
      this.$emit('add-character');
    }
  }
};

// ============================================================================
// Search Tab Component
// ============================================================================

const SearchTab = {
  template: `
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Search Panel -->
      <div class="lg:col-span-1">
        <div class="bg-white rounded-lg shadow-md p-6 sticky top-6">
          <h2 class="text-xl font-bold text-gray-800 mb-4">🔍 Search Books</h2>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Search Query
            </label>
            <input
              v-model="query"
              type="text"
              placeholder="E.g., stories about bravery..."
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500"
              @keyup.enter="search"
            />
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Filter by Category
            </label>
            <select
              v-model="category"
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500"
            >
              <option value="">All Categories</option>
              <option value="epic">Epic</option>
              <option value="fables">Fables</option>
              <option value="folk_tales">Folk Tales</option>
            </select>
          </div>
          
          <div class="mb-6">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Number of Results: {{ topK }}
            </label>
            <input
              v-model="topK"
              type="range"
              min="3"
              max="20"
              class="w-full"
            />
          </div>
          
          <button
            @click="search"
            :disabled="!query || isSearching"
            class="w-full bg-orange-500 text-white font-bold py-2 px-4 rounded-lg hover:bg-orange-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="!isSearching">Search</span>
            <span v-else>Searching...</span>
          </button>
        </div>
      </div>
      
      <!-- Results Panel -->
      <div class="lg:col-span-2">
        <div class="bg-white rounded-lg shadow-md p-6">
          <h2 class="text-xl font-bold text-gray-800 mb-4">
            Results
            <span v-if="results.length > 0" class="text-sm font-normal text-gray-500">
              ({{ results.length }} found)
            </span>
          </h2>
          
          <div v-if="results.length === 0 && !isSearching" class="text-center py-12 text-gray-400">
            <div class="text-6xl mb-4">🔍</div>
            <p>Enter a search query to find relevant stories</p>
          </div>
          
          <div v-if="isSearching" class="text-center py-12">
            <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
            <p class="mt-4 text-gray-600">Searching mythology texts...</p>
          </div>
          
          <div v-else class="space-y-4">
            <div
              v-for="(result, index) in results"
              :key="index"
              class="border-l-4 border-orange-400 pl-4 py-3 hover:bg-orange-50 transition-colors rounded"
            >
              <div class="flex items-start justify-between mb-2">
                <div>
                  <h3 class="font-semibold text-gray-800">{{ result.title }}</h3>
                  <p class="text-sm text-gray-500">{{ result.book }}</p>
                </div>
                <span class="px-2 py-1 text-xs bg-green-100 text-green-700 rounded">
                  {{ (result.score * 100).toFixed(1) }}% match
                </span>
              </div>
              
              <p class="text-sm text-gray-700 mb-3">
                {{ result.text.substring(0, 300) }}...
              </p>
              
              <button
                @click="useForStory(result)"
                class="text-sm text-orange-600 hover:text-orange-700 font-medium"
              >
                ✨ Use for Story Generation →
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  
  data() {
    return {
      query: '',
      category: '',
      topK: 10,
      isSearching: false,
      results: []
    };
  },
  
  methods: {
    async search() {
      if (!this.query) return;
      
      this.isSearching = true;
      
      try {
        const params = new URLSearchParams({
          query: this.query,
          top_k: this.topK
        });
        
        if (this.category) {
          params.append('category', this.category);
        }
        
        const response = await fetch(`/api/search?${params}`);
        this.results = await response.json();
      } catch (error) {
        console.error('Error searching:', error);
        alert('Error performing search. Please try again.');
      } finally {
        this.isSearching = false;
      }
    },
    
    useForStory(result) {
      this.$emit('use-for-story', result);
    }
  }
};

// ============================================================================
// Pipeline Status Tab Component
// ============================================================================

const PipelineTab = {
  template: `
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">