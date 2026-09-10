# Demo Deployment

VERIFAI is deployed as two services:

- **Frontend:** Vercel, using the `frontend/` directory.
- **API and database:** Render, using `render.yaml` and `backend/Dockerfile`.

## 1. Deploy the API on Render

1. Push this repository to GitHub.
2. In Render, choose **New > Blueprint** and select the repository.
3. Render detects `render.yaml` and creates `verifai-api` plus `verifai-db`.
4. Copy the deployed API URL and verify `https://YOUR-API.onrender.com/api/v1/health/`.

The first deployment can take several minutes because the OCR and face-analysis dependencies are large. Free web services sleep when idle, so the first request after inactivity may be slow. Uploaded files use temporary disk storage on the free plan.

## 2. Deploy the frontend on Vercel

1. In Vercel, choose **Add New > Project** and select the repository.
2. Set **Root Directory** to `frontend`.
3. Add the environment variable `VITE_API_URL` with the Render API URL, without a trailing slash.
4. Deploy with the default Vite settings.

The final Vercel URL is the demo link for the PPT. Keep the Render API URL available as a backup health-check link.

## CLI alternative

From `frontend/`:

```powershell
npx vercel --prod
```

When prompted, set `VITE_API_URL` to the Render API URL in the Vercel project settings and redeploy.