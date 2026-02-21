# Reserve Frontend

Modern Next.js 14 frontend for the Reserve restaurant reservation system.

## Features

- **Public Side**: Elegant reservation booking with URL-friendly branch slugs
- **Admin Dashboard**: Complete reservation management system
- **Authentication**: JWT-based auth with automatic token refresh
- **Responsive Design**: Mobile-first, fully responsive UI
- **Type Safety**: Full TypeScript implementation

## Tech Stack

- Next.js 14 (App Router)
- React 18
- TypeScript
- Tailwind CSS
- Axios
- React Hook Form
- Zod
- react-hot-toast

## Getting Started

### Prerequisites

- Node.js 20+
- npm or yarn

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

### Build

```bash
npm run build
npm start
```

### Docker

The frontend is included in the root `docker-compose.yml`. To run with Docker:

```bash
# From project root
docker-compose up frontend
```

Or build the frontend image:

```bash
cd frontend
docker build -t reserve-frontend .
docker run -p 3000:3000 reserve-frontend
```

## Environment Variables

Create a `.env.local` file:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Deploying (e.g. Render)

If the frontend is deployed but the browser shows `ERR_CONNECTION_REFUSED` to `localhost:8000`, the app was built with the default API URL. Set **`NEXT_PUBLIC_API_URL`** on the frontend service to your backend’s public URL (e.g. `https://your-api.onrender.com`), then **redeploy** so the build picks it up. The Dockerfile declares it as a build arg so the Next.js build bakes it in. Use the URL with no trailing slash. Use "Clear build cache & deploy" if you already had the var but still saw localhost:8000.

## Project Structure

```
frontend/
├── app/                    # Next.js app directory
│   ├── (public)/          # Public routes
│   ├── admin/             # Admin routes
│   └── layout.tsx         # Root layout
├── components/            # React components
│   ├── ui/               # Reusable UI components
│   └── ...               # Feature components
├── lib/                   # Utilities and configs
│   ├── api.ts            # API client
│   ├── auth-context.tsx  # Auth context
│   ├── types.ts          # TypeScript types
│   └── utils.ts          # Utility functions
└── public/               # Static assets
```

## API Integration

The frontend communicates with the backend API at `http://localhost:8000`. All API calls are handled through the centralized API client in `lib/api.ts` with automatic JWT token management.

## Authentication

Admin authentication uses JWT tokens stored in localStorage. Tokens are automatically refreshed before expiration. Protected routes are wrapped with the `ProtectedRoute` component.
