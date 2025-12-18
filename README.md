# NYC 311 Analytics – Local Installation

Quick guide to bring up the FastAPI backend (LangGraph agent) and the Next.js frontend that consume it.

## Prerequisites
- Python 3.11+ with `pip`
- Node.js 20+ (ships with a recent `npm`)
- A DeepSeek API key and base URL for the LangChain agent

## Backend (FastAPI + LangGraph)
1. **Add the NYC 311 dataset**: Place the `311_Service_Requests_from_2010_to_Present.csv` file directly in the `backend/` folder. This is required for the application to work.
2. From `backend/`, create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create `.env` in `backend/` with at least:
   ```bash
   DEEPSEEK_API_KEY=sk-your-key
   DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
   ```
   Add any other secrets (e.g., OpenAI keys) the tools rely on.
5. Launch the API:
   ```bash
   uvicorn app:app --reload --port 8000
   ```

## Frontend (Next.js)
1. From `frontend/`, install packages:
   ```bash
   npm install
   ```
2. Copy `.env.example` to `.env.local` if needed (or create a fresh file) and set the backend URL, e.g.:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```
3. Start the dev server:
   ```bash
   npm run dev
   ```
   The app defaults to `http://localhost:3000`.

## Running Both Together
- Keep the backend running on port `8000` and the frontend on `3000`.
- If ports differ, update `NEXT_PUBLIC_API_URL` accordingly and restart the frontend dev server.
- For production builds, use `npm run build && npm run start` (frontend) and a process manager such as `uvicorn app:app --host 0.0.0.0 --port 8000` or gunicorn (backend).

You’re set—open the frontend, submit a query, and the agent will process it against the NYC 311 dataset in `backend/311_Service_Requests_from_2010_to_Present.csv`.***
