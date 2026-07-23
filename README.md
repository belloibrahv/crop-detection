# AgroScan NG - Crop Disease Detection System

A web-based crop disease detection system for smallholder farmers in Nigeria, built with React, Flask, and TensorFlow.

## Project Structure

```
agroscan-ng/
├── frontend/              # React + Vite PWA
├── api/                   # Flask backend API
├── inference/             # FastAPI model serving
├── ml/                    # Model training scripts
├── docker-compose.yml     # Local development stack
└── README.md
```

## Local Development

### Prerequisites

- Docker & Docker Compose

### Getting Started

1. Clone the repository
2. Run the stack:
   ```bash
   docker-compose up --build
   ```
3. Seed the database (in a new terminal):
   ```bash
   docker-compose exec api python seed.py
   ```
4. Access the app:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:5000
   - Inference service: http://localhost:8501

## Deployment

This project is configured for deployment to Render:

1. Push to GitHub
2. Create three Web Services on Render:
   - `agroscan-inference`: Docker context `./inference`
   - `agroscan-api`: Docker context `./api`
   - `agroscan-frontend`: Docker context `./frontend` or Static Site
3. Create a PostgreSQL database on Render
4. Set environment variables:
   - API: `DATABASE_URL`, `INFERENCE_URL`, `JWT_SECRET`

## Tech Stack

- **Frontend**: React, TypeScript, Vite, Tailwind CSS, React Query, PWA
- **Backend**: Flask, SQLAlchemy, PostgreSQL
- **ML**: TensorFlow, FastAPI
- **DevOps**: Docker, Docker Compose, GitHub Actions, Render
