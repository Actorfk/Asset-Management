# Asset Management System

A Vue.js + Flask + SQLite asset management system with Huawei's "One-Point-Red" design style.

## Features

### Left Sidebar Menu
- **Dashboard**: System overview with asset statistics
- **Computers**: Manage computer equipment
- **Devices**: Manage other devices (printers, projectors, etc.)
- **Users**: Manage system users
- **Settings**: System configuration and theme settings

### Key Features
1. **Authentication**: Secure login system with session management
2. **Asset Statistics**: Real-time computer and device counts
3. **Asset Management**: Add, edit, delete asset information
4. **User Management**: Manage users and asset assignments
5. **Status Tracking**: Track asset status (Active, Maintenance, Retired)
6. **Theme Design**: Huawei-style red theme design

## Tech Stack

### Frontend
- Vue.js 3
- Vue Router 4
- Responsive design

### Backend
- Python Flask
- SQLAlchemy ORM
- SQLite database
- RESTful API
- Session-based authentication

## Quick Start

### Option 1: Using Startup Script (Recommended)
1. Run `start.bat`
2. Select option to initialize sample data (first run)
3. Wait for services to start
4. Visit http://localhost:8080

### Option 2: Manual Start

#### Start Backend Service
```bash
cd backend
pip install -r requirements.txt
python app.py
```

#### Start Frontend Service
```bash
cd frontend
python -m http.server 8080
```

## Access URLs

- **Frontend**: http://localhost:8080
- **Backend API**: http://localhost:5000

## Default Credentials

- **Admin Account**: 
  - Username: `admin`
  - Password: `admin`

- **Sample Users** (if initialized):
  - Username: `zhangsan`, `lisi`, `wangwu`, `zhaoliu`, `qianqi`
  - Password: `password123`

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/auth/status` - Check authentication status

### Dashboard
- `GET /api/dashboard` - Get system statistics (requires auth)

### Computers
- `GET /api/computers` - Get all computers (requires auth)
- `POST /api/computers` - Add computer (requires auth)
- `PUT /api/computers/:id` - Update computer (requires auth)
- `DELETE /api/computers/:id` - Delete computer (requires auth)

### Devices
- `GET /api/devices` - Get all devices (requires auth)
- `POST /api/devices` - Add device (requires auth)
- `PUT /api/devices/:id` - Update device (requires auth)
- `DELETE /api/devices/:id` - Delete device (requires auth)

### Users
- `GET /api/users` - Get all users (requires auth)
- `POST /api/users` - Add user (requires auth)
- `PUT /api/users/:id` - Update user (requires auth)
- `DELETE /api/users/:id` - Delete user (requires auth)

### Settings
- `GET /api/settings` - Get system settings (requires auth)
- `PUT /api/settings` - Update settings (requires auth)

## Design Style

Huawei's "One-Point-Red" design:
- Primary color: Huawei Red (#CF0A2C)
- Clean, modern interface
- Responsive layout
- Card-based design
- Intuitive status indicators

## Database

SQLite database at `backend/assets.db` with tables:
- `computer_asset` - Computer assets
- `device_asset` - Device assets
- `user` - Users (with password hashes)

## Notes

1. Database and tables are created automatically on first run
2. Default admin account is created automatically
3. Backend runs on port 5000
4. Frontend runs on port 8080
5. All protected API endpoints require authentication
6. Sessions are maintained via cookies

## Development

To modify or extend:
1. Backend code: `backend/app.py`
2. Frontend code: `frontend/index.html`
3. Database models: Defined in Flask app
4. API follows RESTful design