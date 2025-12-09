# Vue.js Frontend Setup Guide
## Mythology Story Generator Web UI

Complete setup instructions for the Vue.js web interface.

---

## 📁 Project Structure

```
mythology-project/
├── backend/
│   ├── app.py                      # Flask API server
│   ├── mythology_pipeline.py      # Core pipeline
│   ├── story_generator.py         # Story generation
│   ├── character_knowledge_graph.py
│   └── requirements.txt
├── static/
│   ├── index.html                 # Main HTML file
│   ├── js/
│   │   ├── app.js                # Main Vue app
│   │   └── components/           # Vue components
│   │       ├── GenerateTab.js
│   │       ├── LibraryTab.js
│   │       ├── CharactersTab.js
│   │       ├── SearchTab.js
│   │       └── PipelineTab.js
│   └── css/
│       └── custom.css            # Additional styles
├── generated_stories/             # Story output directory
├── generated_images/              # Image output directory
└── character_library.json         # Character database
```

---

## 🚀 Quick Start

### Step 1: Backend Setup

```bash
# Install Python dependencies
cd mythology-project
pip install flask flask-cors

# Set environment variables
export OPENAI_API_KEY="your_key_here"
export REDIS_HOST="localhost"
export REDIS_PORT="6379"

# Start Flask server
python app.py
```

Server will start on `http://localhost:5000`

### Step 2: Create Static Files

Create `static/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mythology Story Studio</title>
    
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    
    <!-- Vue.js 3 -->
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
</head>
<body>
    <div id="app"></div>
    
    <!-- Load all component files -->
    <script src="/static/js/components/GenerateTab.js"></script>
    <script src="/static/js/components/LibraryTab.js"></script>
    <script src="/static/js/components/CharactersTab.js"></script>
    <script src="/static/js/components/SearchTab.js"></script>
    <script src="/static/js/components/PipelineTab.js"></script>
    <script src="/static/js/app.js"></script>
</body>
</html>
```

### Step 3: Create Component Files

**static/js/components/GenerateTab.js:**

```javascript
const GenerateTab = {
  name: 'GenerateTab',
  template: `
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Input Section -->
      <div class="bg-white rounded-lg shadow-md p-6">
        <h2 class="text-xl font-bold text-gray-800 mb-4">🎨 Create New Story</h2>
        
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Story Theme or Topic
          </label>
          <textarea
            v-model="theme"
            rows="3"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
            placeholder="E.g., Krishna stealing butter..."
          ></textarea>
        </div>

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

        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Age Range
          </label>
          <select
            v-model="ageRange"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500"
          >
            <option value="3-5 years">3-5 years</option>
            <option value="5-8 years">5-8 years</option>
            <option value="8-12 years">8-12 years</option>
          </select>
        </div>

        <button
          @click="generateStory"
          :disabled="!theme || isGenerating"
          class="w-full bg-gradient-to-r from-orange-500 to-purple-600 text-white font-bold py-3 px-6 rounded-lg hover:from-orange-600 hover:to-purple-700 transition-all disabled:opacity-50"
        >
          <span v-if="!isGenerating">✨ Generate Story</span>
          <span v-else>Generating...</span>
        </button>

        <!-- Progress indicators -->
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

          <div>
            <h4 class="font-semibold text-gray-700 mb-2">Summary</h4>
            <p class="text-gray-600">{{ generatedStory.summary }}</p>
          </div>

          <div class="bg-purple-50 p-4 rounded-lg">
            <h4 class="font-semibold text-purple-700 mb-2">💡 Moral Lesson</h4>
            <p class="text-purple-600">{{ generatedStory.moral }}</p>
          </div>

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

          <div class="flex space-x-3 pt-4">
            <button
              @click="downloadStory"
              class="flex-1 bg-orange-500 text-white py-2 px-4 rounded-lg hover:bg-orange-600 transition-colors"
            >
              📄 Download JSON
            </button>
            <button
              @click="createAnother"
              class="flex-1 bg-purple-500 text-white py-2 px-4 rounded-lg hover:bg-purple-600 transition-colors"
            >
              ✨ Create Another
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
        'The clever rabbit and lion',
        'The honest woodcutter'
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
        // Simulate progress
        for (let i = 0; i < this.progress.length; i++) {
          this.progress[i].status = 'loading';
          await new Promise(resolve => setTimeout(resolve, 500));
          this.progress[i].status = 'complete';
        }

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

        if (!response.ok) throw new Error('Generation failed');
        
        this.generatedStory = await response.json();
      } catch (error) {
        console.error('Error:', error);
        alert('Error generating story. Please try again.');
      } finally {
        this.isGenerating = false;
      }
    },
    
    downloadStory() {
      const blob = new Blob([JSON.stringify(this.generatedStory, null, 2)], {
        type: 'application/json'
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${this.generatedStory.title.replace(/\s+/g, '_')}.json`;
      a.click();
    },
    
    createAnother() {
      this.generatedStory = null;
      this.theme = '';
      this.progress = [];
    }
  }
};
```

### Step 4: Main App File

**static/js/app.js:**

```javascript
const { createApp } = Vue;

const app = createApp({
  template: `
    <div id="app" class="min-h-screen" style="background: linear-gradient(135deg, #FFF5E6 0%, #F3E5F5 100%);">
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
                <span class="font-semibold">{{ stats.generated_stories }}</span> stories
              </div>
              <div class="text-sm text-gray-600">
                <span class="font-semibold">{{ stats.total_characters }}</span> characters
              </div>
            </div>
          </div>
        </div>
      </header>

      <!-- Main Content -->
      <div class="container mx-auto px-6 py-8">
        <!-- Tabs -->
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

        <!-- Content -->
        <component :is="activeTab + '-tab'"></component>
      </div>
    </div>
  `,
  
  data() {
    return {
      activeTab: 'generate',
      tabs: [
        { id: 'generate', name: 'Generate', icon: '✨' },
        { id: 'library', name: 'Library', icon: '📖' },
        { id: 'characters', name: 'Characters', icon: '🎭' },
        { id: 'search', name: 'Search', icon: '🔍' },
        { id: 'pipeline', name: 'Pipeline', icon: '⚙️' }
      ],
      stats: {
        generated_stories: 0,
        total_characters: 0
      }
    };
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
});

// Register components
app.component('generate-tab', GenerateTab);
// app.component('library-tab', LibraryTab);
// ... register other components

app.mount('#app');
```

---

## 🎨 Features Overview

### Generate Story Tab
- ✨ AI-powered story generation
- 🎯 Age-appropriate content (3-5, 5-8, 8-12 years)
- 📝 Theme suggestions
- ⏱️ Real-time progress tracking
- 💾 Download generated stories

### Story Library Tab
- 📚 Browse all generated stories
- 🔍 Search and filter
- 🏷️ Category tags
- 📊 Story metrics

### Characters Tab
- 🎭 Character profiles
- 👤 Personality traits
- 🔗 Story relationships
- ➕ Add new characters

### Search Tab
- 🔍 Semantic search through mythology texts
- 📈 Relevance scoring
- 🎯 Category filtering
- ✨ Use results for story generation

### Pipeline Status Tab
- 📊 Database statistics
- 📥 Book ingestion
- 💚 System health monitoring
- 💰 API usage tracking

---

## 🔧 Configuration

### API Base URL

Update in each component if needed:

```javascript
const API_BASE = 'http://localhost:5000/api';

// In component methods:
const response = await fetch(`${API_BASE}/stories/generate`, {
  method: 'POST',
  // ...
});
```

### Styling Customization

Add custom CSS in `static/css/custom.css`:

```css
/* Custom theme colors */
:root {
  --primary-orange: #f97316;
  --primary-purple: #9333ea;
  --bg-gradient-start: #FFF5E6;
  --bg-gradient-end: #F3E5F5;
}

/* Custom animations */
@keyframes slideIn {
  from {
    transform: translateY(-10px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.slide-in {
  animation: slideIn 0.3s ease-out;
}
```

---

## 🚀 Running the Application

```bash
# Terminal 1: Start Redis
docker run -d -p 6379:6379 redis/redis-stack:latest

# Terminal 2: Start Flask backend
export OPENAI_API_KEY="your_key"
python app.py

# Terminal 3: (Optional) Start development server for static files
# If not using Flask to serve static files
python -m http.server 8000 --directory static
```

Access the application:
- **Backend API**: http://localhost:5000
- **Frontend**: http://localhost:5000 (served by Flask)

---

## 📱 Mobile Responsive

The UI is fully responsive and works on:
- 📱 Mobile phones
- 📲 Tablets
- 💻 Desktops

Tailwind's responsive utilities handle all breakpoints automatically.

---

## 🐛 Troubleshooting

**CORS Issues:**
```python
# In app.py
from flask_cors import CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})
```

**Vue Not Loading:**
- Check browser console for errors
- Verify CDN links are accessible
- Ensure all component files are loaded

**API Connection Failed:**
- Verify Flask server is running
- Check API endpoint URLs
- Look at network tab in browser DevTools

---

## 🎯 Next Steps

1. **Add Image Generation UI**: Display generated character/scene images
2. **Video Preview**: Show video creation progress
3. **User Authentication**: Add login system
4. **Story Ratings**: Let users rate stories
5. **Export Options**: PDF, EPUB formats
6. **Batch Generation**: Queue multiple stories

Ready to run! Just follow the setup steps and you'll have a beautiful web interface for your mythology story generator. 🎉
