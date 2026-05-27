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

## Deploying on Vercel

You can deploy this repo as either one Vercel project or two:

1. If the frontend and FastAPI backend are deployed together in the same Vercel project, leave `BACKEND_URL` unset. The frontend will call `/api/*` on the same domain and Vercel will serve the Python functions from the root `api/` folder.
2. If the frontend is deployed separately from the backend, set `BACKEND_URL` in the frontend project to the backend's public URL. The Next.js rewrites will proxy `/api/*` to that backend.

For the backend project, make sure the Vercel project includes the root `api/requirements.txt` file so the Python dependencies are installed during build.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
