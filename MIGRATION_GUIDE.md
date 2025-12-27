# Migration to Next.js Frontend

This guide outlines the migration from Django templates to Next.js + React + Tailwind CSS + shadcn/ui.

## 🎯 What's Been Done

### ✅ Frontend Setup (Completed)
- **Next.js 14+** with App Router
- **TypeScript** for type safety
- **Tailwind CSS v4** for styling
- **shadcn/ui** component library
- **API client** with typed endpoints
- **TypeScript interfaces** for all data models

### ✅ Backend API (Completed)
- **Django REST Framework** installed and configured
- **CORS** configured for Next.js frontend (localhost:3000)
- **Session-based authentication** (compatible with existing Django auth)
- **API endpoints** for:
  - Authentication (login, logout, current user)
  - Dashboard data
  - Tasks (CRUD + complete)
  - Daily logs (CRUD)
  - Categories (CRUD)
  - Plans (CRUD)
  - Friends and friend requests
  - Users list

### ✅ Initial Pages Created
- Landing page
- Login page
- Dashboard page (with stats and lists)

## 🚀 Next Steps

### 1. Start the Development Servers

#### Django Backend:
```bash
cd /Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix/progress_tracker
python manage.py runserver
```

#### Next.js Frontend:
```bash
cd /Users/vishwashbatra/data/code/djangoapps/vismatrixv2/vismatrix/frontend
npm run dev
```

The frontend will be available at http://localhost:3000
The backend API will be available at http://localhost:8000

### 2. Complete Remaining Pages

You still need to create these pages in Next.js:

- [ ] `/tasks` - Task list and management
- [ ] `/tasks/[id]` - Task detail/edit
- [ ] `/logs` - Daily logs list
- [ ] `/logs/new` - Create new log
- [ ] `/analytics` - Analytics dashboard with charts
- [ ] `/categories` - Category management
- [ ] `/plans` - Plans list
- [ ] `/plans/[id]` - Plan detail with DAG visualization
- [ ] `/friends` - Friends list
- [ ] `/friends/requests` - Friend requests
- [ ] `/users` - User search
- [ ] `/profile` - User profile
- [ ] `/signup` - Registration page
- [ ] `/messages` - Messaging (if keeping this feature)

### 3. Add Missing Components

Create reusable components:
- Navigation component (shared across pages)
- Task card component
- Log card component
- Category selector
- Date picker
- Charts for analytics (use recharts or chart.js)
- Loading skeletons
- Error boundaries

### 4. Implement Authentication Flow

- Add authentication context/provider
- Protected route wrapper
- Redirect logic for unauthenticated users
- Token refresh mechanism (if switching to JWT)
- Remember me functionality

### 5. Add Advanced Features

- [ ] Real-time updates (WebSockets)
- [ ] Offline support (PWA)
- [ ] Dark mode toggle
- [ ] Mobile responsiveness
- [ ] Notifications system
- [ ] Search functionality
- [ ] Filtering and sorting
- [ ] Pagination
- [ ] Export data features

### 6. Testing

- Unit tests for components
- Integration tests for API calls
- E2E tests with Playwright or Cypress
- Accessibility testing

### 7. Deployment Preparation

- Environment variables configuration
- Build optimization
- API endpoint configuration for production
- CORS settings for production domain
- Static file serving
- Database migrations
- SSL/HTTPS setup

## 📁 Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js app router pages
│   │   ├── layout.tsx         # Root layout
│   │   ├── page.tsx           # Landing page
│   │   ├── login/page.tsx     # Login page
│   │   ├── dashboard/page.tsx # Dashboard
│   │   └── ...                # More pages to create
│   ├── components/
│   │   └── ui/                # shadcn/ui components
│   ├── lib/
│   │   ├── api.ts             # API client
│   │   └── utils.ts           # Utility functions
│   └── types/
│       └── index.ts           # TypeScript interfaces
└── package.json

progress_tracker/
├── tracker/
│   ├── api_views.py           # REST API views
│   ├── api_urls.py            # API URL configuration
│   ├── serializers.py         # DRF serializers
│   ├── views.py               # Traditional Django views (can be deprecated)
│   └── ...
└── progress_tracker/
    └── settings.py            # Updated with DRF + CORS
```

## 🔧 Configuration Files

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend (settings.py)
- REST Framework configured
- CORS headers enabled for localhost:3000
- Session authentication enabled
- Token authentication available

## 📝 API Endpoints

All API endpoints are prefixed with `/api/`:

### Authentication
- `POST /api/auth/login/` - Login
- `POST /api/auth/logout/` - Logout
- `GET /api/auth/user/` - Get current user

### Dashboard
- `GET /api/dashboard/` - Get dashboard data

### Tasks
- `GET /api/tasks/` - List tasks
- `POST /api/tasks/` - Create task
- `GET /api/tasks/{id}/` - Get task
- `PUT /api/tasks/{id}/` - Update task
- `DELETE /api/tasks/{id}/` - Delete task
- `POST /api/tasks/{id}/complete/` - Mark complete

### Daily Logs
- `GET /api/logs/` - List logs
- `POST /api/logs/` - Create log
- `GET /api/logs/{id}/` - Get log
- `PUT /api/logs/{id}/` - Update log
- `DELETE /api/logs/{id}/` - Delete log

### Categories
- `GET /api/categories/` - List categories
- `POST /api/categories/` - Create category
- `PUT /api/categories/{id}/` - Update category
- `DELETE /api/categories/{id}/` - Delete category

### Plans
- `GET /api/plans/` - List plans
- `POST /api/plans/` - Create plan
- `GET /api/plans/{id}/` - Get plan with nodes
- `PUT /api/plans/{id}/` - Update plan
- `DELETE /api/plans/{id}/` - Delete plan

### Friends
- `GET /api/users/` - List all users
- `GET /api/friends/` - List friends
- `POST /api/users/{id}/send_request/` - Send friend request
- `GET /api/friends/requests/` - Get friend requests
- `POST /api/friends/requests/{id}/accept/` - Accept request
- `POST /api/friends/requests/{id}/reject/` - Reject request
- `POST /api/friends/{id}/remove/` - Remove friend

## 🎨 Styling Guidelines

Using Tailwind CSS with shadcn/ui:

```tsx
// Example component structure
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export default function MyComponent() {
  return (
    <Card className="p-6">
      <h2 className="text-2xl font-bold mb-4">Title</h2>
      <Button>Click me</Button>
    </Card>
  );
}
```

## 🔐 Authentication Pattern

```tsx
// In your pages
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function ProtectedPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      await api.getCurrentUser();
      setIsLoading(false);
    } catch (error) {
      router.push('/login');
    }
  };

  if (isLoading) return <div>Loading...</div>;

  return <div>Protected content</div>;
}
```

## 📚 Recommended Libraries

- **Forms**: react-hook-form + zod
- **Charts**: recharts or chart.js
- **Date picker**: react-day-picker
- **Drag & drop**: dnd-kit
- **Icons**: lucide-react (already included with shadcn)
- **State management**: Zustand or React Context
- **Data fetching**: TanStack Query (React Query)

## 🐛 Troubleshooting

### CORS Issues
If you see CORS errors, make sure:
1. Django is running on port 8000
2. Next.js is running on port 3000
3. `django-cors-headers` is installed
4. CORS settings in Django settings.py are correct

### Session Authentication Not Working
- Ensure `credentials: 'include'` is set in fetch requests
- Check that cookies are being set correctly
- Verify CSRF token handling

### Hot Reload Not Working
- Restart the Next.js dev server
- Clear .next folder: `rm -rf .next`

## 🚢 Production Deployment

### Option 1: Same Domain (Recommended)
Use a reverse proxy (nginx) to serve both Django and Next.js under the same domain:
- `yourdomain.com/` → Next.js
- `yourdomain.com/api/` → Django API
- `yourdomain.com/admin/` → Django Admin

### Option 2: Separate Domains
- Frontend: Vercel/Netlify
- Backend: Traditional hosting (AWS, DigitalOcean, etc.)
- Update CORS settings for production domain

## 📖 Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [shadcn/ui Components](https://ui.shadcn.com/)
- [Tailwind CSS](https://tailwindcss.com/)
- [TypeScript](https://www.typescriptlang.org/)

---

## 🎉 Getting Started Now

1. Open two terminal windows
2. Start Django: `cd progress_tracker && python manage.py runserver`
3. Start Next.js: `cd frontend && npm run dev`
4. Visit http://localhost:3000
5. Test the login flow and dashboard

**Happy coding!** 🚀
