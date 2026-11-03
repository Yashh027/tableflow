# TableFlow

Restaurant ordering and management platform.

## Stack

- Frontend: Next.js, React, TypeScript, Tailwind CSS
- Backend: FastAPI, SQLAlchemy, Alembic
- Database: PostgreSQL
- Real-time communication: WebSockets

## Local development

### Backend

1. Create and activate a Python virtual environment.
2. Install dependencies:

   pip install -r requirements.txt

3. Configure `backend/.env` with DATABASE_URL and JWT_SECRET_KEY.
4. Apply migrations:

   alembic upgrade head

5. Start the API:

   uvicorn app.main:app --reload

### Frontend

1. Open the frontend directory.
2. Install dependencies:

   npm install

3. Configure `.env.local` with:

   NEXT_PUBLIC_API_URL=http://localhost:8000

4. Start:

   npm run dev

## Docker deployment

1. Copy `.env.example` to `.env`.
2. Replace the sample database password and JWT secret with strong random values.
3. Set CORS_ORIGINS to the actual frontend origin.
4. Set NEXT_PUBLIC_API_URL to the actual publicly reachable backend URL.
5. Build and start:

   docker compose up --build -d

6. Inspect services:

   docker compose ps

7. Inspect logs:

   docker compose logs --tail=100

The backend container applies Alembic migrations before starting Uvicorn.

## Local URLs

- Frontend: http://localhost:3000
- API: http://localhost:8000
- API documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Important deployment notes

- Do not commit `.env` files or database backups.
- Configure HTTPS through a reverse proxy before public deployment.
- Restrict database access to the application network.
- Back up PostgreSQL and test restoration.
- Configure production CORS origins.
- Online payment integration is deferred and must not be treated as operational.
- This Compose configuration is a deployment foundation, not a complete production security configuration.
