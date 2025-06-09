# S&P 500 Trading Simulation Dashboard - React Frontend

A modern React-based frontend for analyzing trading simulation performance with interactive charts and detailed drill-down capabilities.

## Features

- **📊 Interactive Dashboard**: Overview of all simulations with line charts showing cumulative returns
- **🔍 Simulation Details**: Click into any simulation to see daily trading data and portfolio performance
- **📰 News Analysis**: Drill down to individual days to see news sentiment analysis and trading decisions
- **📱 Responsive Design**: Optimized for desktop and mobile viewing
- **⚡ Modern Tech Stack**: Built with React, Recharts, and modern JavaScript

## Tech Stack

- **React 18**: Modern React with hooks
- **React Router**: Client-side routing
- **Recharts**: Interactive charting library
- **Axios**: HTTP client for API calls
- **date-fns**: Date manipulation utilities
- **CSS Grid & Flexbox**: Modern responsive layouts

## Prerequisites

- Node.js 16+ 
- npm or yarn package manager
- Python Flask backend (automatically started on port 5001)

## Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

## Development

Start both the React frontend and Flask backend together:
```bash
npm start
```

This will:
- Start the Flask backend on port 5001 (from the parent directory)
- Start the React development server on port 3000
- Automatically proxy API calls from React to Flask
- Enable hot reloading for React development
- Display logs from both servers in the same terminal

Alternative commands:
```bash
# Start both servers (same as npm start)
npm run dev

# Start only the React frontend (requires Flask to be running separately)
npm run start:frontend

# Start only the Flask backend from the parent directory
npm run start:backend
```

Visit http://localhost:3000 to view the application.

**Note**: The first time you run this, make sure you've installed dependencies with `npm install`.

## Building for Production

Build the production bundle:
```bash
npm run build
```

This creates a `build/` directory with optimized production files that the Flask app will serve.

## Project Structure

```
frontend/
├── public/
│   └── index.html          # HTML template
├── src/
│   ├── components/
│   │   ├── Dashboard.js    # Main simulation overview
│   │   ├── Dashboard.css   # Dashboard styles
│   │   ├── Simulation.js   # Individual simulation details
│   │   ├── Simulation.css  # Simulation styles
│   │   ├── Day.js         # Daily trading details
│   │   └── Day.css        # Day styles
│   ├── App.js             # Main app with routing
│   ├── App.css            # Global styles
│   └── index.js           # React entry point
├── package.json           # Dependencies and scripts
└── README.md             # This file
```

## API Integration

The frontend communicates with the Flask backend through these endpoints:

- `GET /api/simulations` - Get all simulations with performance data
- `GET /api/simulation/{id}` - Get detailed daily data for a simulation
- `GET /api/simulation/{id}/day/{date}` - Get news and trading data for a specific day

## Navigation Flow

1. **Dashboard** (`/`) - Shows all simulations with cumulative return charts
2. **Simulation Details** (`/simulation/{id}`) - Shows daily trading data and portfolio performance
3. **Day Details** (`/simulation/{id}/day/{date}`) - Shows news analysis and trading decisions

## Charts and Interactions

- **Line Charts**: Interactive charts using Recharts with hover tooltips
- **Click Navigation**: Click on chart elements to drill down to details
- **Responsive Tables**: Mobile-friendly data tables with proper formatting
- **Currency Formatting**: Proper US dollar formatting throughout
- **Color Coding**: Positive/negative values clearly distinguished

## Customization

### Adding New Chart Types
Add new chart components using Recharts:
```javascript
import { BarChart, Bar, ... } from 'recharts';
```

### Styling
- Modify CSS files for component-specific styles
- Update `App.css` for global styles
- All styles use modern CSS Grid and Flexbox

### API Integration
- API calls are centralized using Axios
- Error handling included for all API endpoints
- Loading states provided for better UX

## Troubleshooting

**Port conflicts**: If port 3000 is in use, React will prompt to use a different port.

**API connection issues**: Ensure Flask backend is running on port 5001 and accessible.

**Build issues**: Clear node_modules and reinstall:
```bash
rm -rf node_modules package-lock.json
npm install
```

## Production Deployment

The Flask app is configured to serve the React build files automatically. After running `npm run build`, the Flask app will serve the optimized React app on the same port.