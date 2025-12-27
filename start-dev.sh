#!/bin/bash

echo "🚀 Starting VisMatrix Development Environment..."
echo ""

# Check if we're in the right directory
if [ ! -d "frontend" ] || [ ! -d "progress_tracker" ]; then
    echo "❌ Error: Please run this script from the vismatrix root directory"
    exit 1
fi

# Start Django backend in background
echo "📦 Starting Django backend on port 8000..."
cd progress_tracker
python manage.py runserver > ../django.log 2>&1 &
DJANGO_PID=$!
cd ..

# Wait a bit for Django to start
sleep 3

# Start Next.js frontend in background
echo "⚛️  Starting Next.js frontend on port 3000..."
cd frontend
npm run dev > ../nextjs.log 2>&1 &
NEXTJS_PID=$!
cd ..

echo ""
echo "✅ Development servers started!"
echo ""
echo "📱 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000/api/"
echo "👨‍💼 Django Admin: http://localhost:8000/admin/"
echo ""
echo "📋 Logs:"
echo "   Django: tail -f django.log"
echo "   Next.js: tail -f nextjs.log"
echo ""
echo "🛑 To stop servers:"
echo "   kill $DJANGO_PID $NEXTJS_PID"
echo "   Or press Ctrl+C and run: pkill -f 'manage.py runserver' && pkill -f 'next-server'"
echo ""

# Wait for user interrupt
trap "echo ''; echo '🛑 Shutting down servers...'; kill $DJANGO_PID $NEXTJS_PID 2>/dev/null; exit 0" INT

echo "Press Ctrl+C to stop all servers..."
wait
