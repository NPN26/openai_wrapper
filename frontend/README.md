This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

Run the FastAPI backend on port 8000:

```bash
cd ../backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

Then run the Next.js frontend on port 3000:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

Requests to `/api/*` are proxied to `http://localhost:8000` by default. To use a different backend URL, set `BACKEND_URL` before starting the frontend:

```bash
BACKEND_URL=http://localhost:8000 npm run dev
```

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

Deploy the repo as a single Vercel project from the repository root.

Use these settings:

1. Framework Preset: `Next.js`
2. Root Directory: `.`
3. Install Command: `cd frontend && npm install`
4. Build Command: `cd frontend && npm run build`
5. Environment Variables: add `DATABASE_URL` and any OpenAI / LangSmith / Postgres variables you use in production

The Next.js app lives in `frontend/`, and the FastAPI app is exposed from `api/index.py` as a Python serverless entrypoint. In local development, `/api/*` proxies to `http://127.0.0.1:8000` by default, or to `BACKEND_URL` if you set one.
