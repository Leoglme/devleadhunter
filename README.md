# devleadhunter

**Personal prospect research tool for freelance web developers**

A comprehensive full-stack application for finding and managing business prospects without websites. Built with modern technologies to help freelance developers find and contact potential clients efficiently.

## 🚀 Features

- 🔐 **Authentication** - Secure login and signup system
- 🔍 **Smart Prospect Search** - Search for prospects by category, city, and source
- 📧 **Email Campaigns** - Create and manage bulk email campaigns
- 👤 **Profile Management** - Manage user profile and preferences
- 📱 **Responsive Design** - Works seamlessly on mobile and desktop
- 🌙 **Dark Theme** - Beautiful GitHub-inspired dark theme

## 🏗️ Architecture

This project is split into two main parts:

```
.
├── client/          # Nuxt.js 4 frontend
└── server/          # FastAPI backend
```

### Frontend (`client/`)

- **Framework**: Nuxt.js 4
- **Language**: TypeScript (strict mode)
- **State Management**: Pinia
- **Styling**: TailwindCSS
- **Icons**: Font Awesome

### Backend (`server/`)

- **Framework**: FastAPI
- **Language**: Python 3.11+
- **Scrapers**: Playwright-based web scrapers
- **Sources**: Google, Pages Jaunes

## 📦 Prerequisites

- **Node.js** 18+ (for frontend)
- **Python** 3.11+ (for backend)
- **npm** or **pnpm** (for frontend)
- **pip** (for backend)
- **Playwright** (for web scraping)

## 🛠️ Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd devleadhunter
```

### 2. Install Frontend Dependencies

```bash
cd client
npm install
```

### 3. Install Backend Dependencies

```bash
cd ../server
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 4. Configure Environment

Create a `.env` file in the `client/` directory:

```env
API_BASE_URL=http://localhost:8000
```

Create a `.env` file in the `server/` directory (optional):

```env
# See server/core/config.py for default values
```

## 🚦 Getting Started

### Start the Backend Server

```bash
cd server
python main.py
```

The API will be available at `http://localhost:8000`

API Documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Start the Frontend Development Server

```bash
cd client
npm run dev
```

The application will be available at `http://localhost:3000`

### Access the Application

Open your browser and navigate to:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000

## 📖 API Endpoints

### Health Check
- `GET /api/v1/health` - Check API health status

### Prospects
- `GET /api/v1/prospects` - List all prospects
- `GET /api/v1/prospects/{id}` - Get prospect by ID
- `POST /api/v1/prospects/search` - Search for prospects
- `POST /api/v1/prospects` - Create new prospect
- `PUT /api/v1/prospects/{id}` - Update prospect
- `DELETE /api/v1/prospects/{id}` - Delete prospect

## 🧩 Project Structure

### Frontend Structure

```
client/
├── assets/          # Global styles and Tailwind
├── components/      # Reusable UI components
├── composables/     # Reusable composables
├── layouts/         # Layout components
├── middleware/      # Route middleware
├── pages/           # Application pages
├── services/        # API services
├── stores/          # Pinia stores
└── types/           # TypeScript types
```

### Backend Structure

```
server/
├── api/             # API routes
│   └── v1/          # API version 1
├── core/            # Core configuration
├── models/          # Pydantic models
├── services/        # Business logic
├── scrappers/       # Web scrapers
└── main.py          # Application entry point
```

## 🧪 Development

### Frontend Development

```bash
cd client

# Development mode
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Backend Development

```bash
cd server

# Development mode (with auto-reload)
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 🎯 How to Use

1. **Sign Up / Login**: Create an account or login to access the dashboard
2. **Search Prospects**: Use the search form to find prospects by category, city, and source
3. **View Results**: Browse the prospects table with details and confidence scores
4. **Create Campaigns**: Select prospects and create email campaigns
5. **Send Emails**: Send bulk emails to your selected prospects

## 🔧 Technologies Used

### Frontend
- [Nuxt.js 4](https://nuxt.com/) - Vue.js framework
- [TypeScript](https://www.typescriptlang.org/) - Type safety
- [Pinia](https://pinia.vuejs.org/) - State management
- [TailwindCSS](https://tailwindcss.com/) - Utility-first CSS
- [Font Awesome](https://fontawesome.com/) - Icons

### Backend
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation
- [Playwright](https://playwright.dev/) - Browser automation
- [Uvicorn](https://www.uvicorn.org/) - ASGI server

## 📝 Contributing

When contributing to this project:

1. Follow the existing code structure and conventions
2. Add proper type annotations and JSDoc/docstrings
3. Write meaningful commit messages
4. Test your changes thoroughly
5. Update documentation as needed

## 📄 License

MIT

---

Built with ❤️ for freelance developers

