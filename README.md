# Recipe Extractor & Meal Planner

React + FastAPI assignment implementation that accepts a recipe blog URL, scrapes page content with BeautifulSoup, extracts structured recipe data with an LLM prompt, stores the result, and shows saved recipe history.

## Features

- Tab 1: recipe URL input, extraction button, structured recipe result cards.
- Tab 2: saved recipe table with title, cuisine, difficulty, extraction date, and details modal.
- Optional meal planner: select 3-5 saved recipes and generate a combined shopping list.
- Backend scraping with `requests` + `BeautifulSoup`.
- PostgreSQL persistence through SQLAlchemy, matching the assignment requirement.
- Groq or Gemini LLM integration with LangChain dependencies and prompt templates.
- Prompt templates stored in `prompts/` for extraction, nutrition, substitutions, and meal planning.
- Sample tested URLs and example API output stored in `sample_data/`.

## Project Structure

```text
backend/
  app/
    main.py          FastAPI routes
    scraper.py       HTML and JSON-LD scraping
    llm.py           Groq/Gemini prompt call and fallback extraction
    models.py        SQLAlchemy recipe model
    schemas.py       Pydantic request/response schemas
frontend/
  src/
    main.jsx         React app
    styles.css       Minimal responsive UI
prompts/             Prompt templates used for extraction and meal planning
sample_data/         Tested URLs and sample JSON output
screenshots/         Add required UI screenshots before submission
```

## Backend Setup

Create a PostgreSQL database named `deepklarity`, then configure environment variables:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Update `.env`:

```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/deepklarity
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash-lite
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

`.env.example` is the safe template that can be shared with reviewers. `.env` is your local private configuration file where you put real database credentials and API keys. The project ignores `.env` through `.gitignore`, so do not commit real keys.

Run the API:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

PostgreSQL is the required database for assignment submission. A small SQLite fallback exists only so the API can be smoke-tested on a machine before PostgreSQL is installed.

If Gemini free quota is unavailable, use Groq instead. Add `GROQ_API_KEY` to `.env`; the backend prefers Groq when that key exists, then tries Gemini, then falls back to local JSON-LD parsing.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## Deployment

Recommended free deployment for the assignment:

- Frontend: Vercel
- Backend: Vercel FastAPI project
- Database: Neon PostgreSQL

1. Create a free PostgreSQL database on Neon and copy its connection string.
2. Deploy the `backend/` folder as a Vercel project.
3. Add backend environment variables on Vercel:
   - `DATABASE_URL=postgresql://...neon.tech/...?...sslmode=require`
   - `GROQ_API_KEY`
   - `GROQ_MODEL=llama-3.3-70b-versatile`
   - `FRONTEND_ORIGINS=https://your-frontend-domain.vercel.app`
4. Copy the deployed backend URL, for example `https://deepklarity-backend.vercel.app`.
5. Deploy the `frontend/` folder as a second Vercel project.
6. Add this frontend environment variable:
   - `VITE_API_BASE=https://your-backend-domain.vercel.app`
7. Redeploy frontend after setting `VITE_API_BASE`.

The GitHub repository should not include `.env`; use `.env.example` as the safe template.

## API Endpoints

- `GET /health` - service health check.
- `POST /recipes/extract` - scrape, extract, generate, store, and return a recipe.
- `GET /recipes` - saved recipe history.
- `GET /recipes/{recipe_id}` - full recipe details for the modal.
- `POST /meal-plan` - combined shopping list for 3-5 saved recipes.

Example extraction request:

```json
{
  "url": "https://www.allrecipes.com/recipe/23891/grilled-cheese-sandwich/"
}
```

## Testing Checklist

1. Start PostgreSQL and the backend.
2. Start the React frontend.
3. Extract a recipe URL from `sample_data/tested_urls.txt`.
4. Confirm Tab 1 displays title, cuisine, times, ingredients, instructions, nutrition, substitutions, shopping list, and related recipes.
5. Open Tab 2 and confirm the recipe appears in history.
6. Click Details and confirm the modal shows the same structured layout.
7. Extract at least 3 recipes, select them, and generate a meal planner shopping list.

## Assignment Criteria Coverage

- Prompt Design & Optimization: extraction prompt forces a strict JSON object and tells the LLM to stay grounded in scraped text/JSON-LD.
- Extraction Quality: scraper removes noisy tags, reads page text, and uses schema.org Recipe JSON-LD when available.
- Generation Quality: LLM generates nutrition estimates, substitutions, shopping list categories, and related recipes.
- Functionality: `/recipes/extract` scrapes, extracts, stores, and returns the recipe in one end-to-end flow.
- Code Quality: backend is split into scraper, LLM, service, schema, model, and route modules.
- Error Handling: invalid URLs, failed fetches, weak page content, missing records, and invalid meal-plan selections return API errors.
- UI Design: React tabs, structured cards, saved recipe table, and details modal match the required screens.
- Database Accuracy: saved recipes are persisted and retrieved from the database through SQLAlchemy.
- Testing Evidence: `sample_data/` contains tested URLs and an example API output; screenshots should be captured after running locally.

## Screenshots To Submit

Run the app and capture:

- Recipe extraction page after a successful extraction.
- Saved recipes history tab.
- Details modal opened from history.

Place these images in the `screenshots/` folder before final submission.

## Notes

The LLM prompt asks the selected model to return only the assignment JSON shape and to avoid inventing missing facts. The fallback parser uses schema.org Recipe JSON-LD when present so the demo remains usable during development even before adding an API key.
