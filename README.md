# TWS - Tool Warehouse System

> Tool Warehouse Management System with robot simulation

## Overview

A web-based tool warehouse management system supporting tool borrowing, employee management, and request approval workflow. The system simulates warehouse robots fetching tools from shelves and placing them on conveyor belts for delivery.

## Directory Structure

```
TWS_System/
├── backend/
│   └── app.py            # RESTful API + warehouse simulation
├── frontend/
│   ├── index.html        # SPA entry
│   ├── style.css         # Stylesheet
│   └── app.js            # App logic (routing, state, CRUD)
├── .gitignore
└── README.md
```

## Features

- **Tool Management**: Full CRUD with search and filter
- **Employee Management**: User info and permissions
- **Borrowing Workflow**: Direct borrow by admin + request-approval flow
- **Permission Control**: Normal employees borrow only department tools; experts borrow any
- **Warehouse Simulation**: Expensive tools (>=200$) trigger robot fetching + conveyor delivery
- **Dashboard**: Statistics with data visualization

## Tech Stack

- **Backend**: Python Flask + SQLite
- **Frontend**: Vanilla JavaScript SPA
- **Styles**: CSS Custom Properties + Glass Morphism
- **Simulation**: Python threading (robots / conveyor)

## Quick Start

```bash
# 1. Install dependencies
pip install flask

# 2. Start the API server
cd backend
python app.py

# 3. In another terminal, preview the frontend
cd frontend
python -m http.server 8080
```

- API runs at `http://localhost:8900/api/`
- Frontend at `http://localhost:8080`
- Default accounts: `E001`-`E005` / password `123456` (`E005` also works with `admin123`)
- `E005` has expert privileges

## License

This project is for educational purposes only.
