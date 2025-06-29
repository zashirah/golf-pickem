# Golf Pickem League

A FastHTML-based web application for managing golf tournament pick'em leagues. Players can register, login, and make picks from different tiers of golfers to compete based on their chosen players' performance.

## 🏌️ Features

### ✅ Phase 1 Complete - Foundation & Authentication
- **User Authentication**: Complete registration, login, logout system with session management
- **Tournament Management**: Create and manage golf tournaments with configurable settings
- **Player Picks**: Select golfers from different tiers (1-4) for each tournament
- **Leaderboards**: View tournament results and pick'em league standings
- **Real-time Updates**: HTMX-powered interface for seamless user experience
- **Database Management**: SQLite database with FastHTML's built-in ORM
- **Responsive UI**: Modern, clean interface with custom CSS

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/your-username/golf-pickem.git
cd golf-pickem
```

2. **Set up virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run the application:**
```bash
python main.py
```

5. **Open your browser:**
```
http://localhost:5001
```
## 🛠️ Technology Stack

- **Framework**: FastHTML (Python web framework)
- **Frontend**: HTMX for dynamic interactions, Custom CSS
- **Database**: SQLite with FastHTML's built-in database tools
- **Authentication**: Session-based with secure token management
- **Server**: Uvicorn (built into FastHTML)

## 📁 Project Structure

```
golf-pickem/
├── main.py              # Main application file (monolithic approach)
├── static/              # Static files (CSS, images)
├── data/                # Database files (SQLite)
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker configuration
├── docker-compose.yml  # Docker Compose setup
├── setup.sh            # Setup script
├── run_dev.py          # Development runner
└── README.md           # This file
```

## 🔐 Authentication System

- **Registration**: Create new user accounts with email validation
- **Login/Logout**: Secure session-based authentication
- **Session Management**: 30-day session tokens with automatic cleanup
- **Protected Routes**: Pick creation and management require authentication
- **Guest Access**: Public viewing of tournaments, field, and leaderboards

## 🎯 Usage

### For Players:
1. **Register** or **Login** to your account
2. **View Tournaments** to see available competitions
3. **Make Picks** by selecting golfers from each tier
4. **Track Progress** on the leaderboards

### For Administrators:
1. **Manage Tournaments**: Create, edit, and configure tournaments
2. **Manage Field**: Assign golfers to tiers
3. **Update Leaderboards**: Input tournament results

## 🐳 Docker Support

### Using Docker Compose:
```bash
docker-compose up -d
```

### Building manually:
```bash
docker build -t golf-pickem .
docker run -p 5001:5001 golf-pickem
```

## 🗺️ Development Roadmap

### Phase 1 ✅ (Complete)
- [x] Project setup and FastHTML foundation
- [x] Database schema and models
- [x] User authentication system
- [x] Basic tournament and pick management
- [x] Initial UI and navigation

### Phase 2 (Planned)
- [ ] Enhanced pick validation and rules
- [ ] Automated scoring system
- [ ] Email notifications
- [ ] Advanced leaderboards and statistics
- [ ] Tournament administration tools

### Phase 3 (Future)
- [ ] Real-time tournament data integration
- [ ] Mobile app support
- [ ] Social features and groups
- [ ] Payment integration for entry fees
- [ ] Advanced analytics and reports

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com/your-username/golf-pickem/issues) page
2. Create a new issue with detailed information
3. Join our community discussions

## 🙏 Acknowledgments

- Built with [FastHTML](https://fastht.ml/) - A modern Python web framework
- UI powered by [HTMX](https://htmx.org/) for dynamic interactions
- Database management with SQLite and FastHTML's ORM

---

⭐ **Star this repo if you find it helpful!**

* **Tournament Management**: ✅ In progress
  * Basic CRUD operations implemented
  * Need to improve form handling and validation

* **Picks System**: ✅ In progress  
  * Pick submission working
  * Need tournament association and validation

* **Golfer Management**: 🔄 To do
  * Database schema defined
  * Need import/management interface

* **User System**: 🔄 To do
  * Authentication needed
  * User profiles and permissions

* **Leaderboards**: 🔄 Partial
  * Basic display implemented
  * Need scoring calculation logic