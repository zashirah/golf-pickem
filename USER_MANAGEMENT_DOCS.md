# Golf Pickem League - User Management Features (Phase 2)

## Overview
This implementation provides comprehensive user management functionality for the Golf Pickem League web application, built with FastHTML.

## Features Implemented

### 1. User Registration and Login System
- **Enhanced Registration**: Users can register with first name, last name, username, email, and password
- **Secure Authentication**: Improved password hashing with salt
- **Session Management**: Secure session tokens with expiration
- **First User Admin**: The first registered user automatically becomes an administrator

### 2. User Profile Management
- **View Profile**: Users can view their profile information including account type and member since date
- **Edit Profile**: Users can update their personal information (name, username, email)
- **Change Password**: Coming soon! Currently disabled.

### 3. Password Reset Functionality
- **Forgot Password**: Users can request password resets
- **Reset Tokens**: Secure, time-limited reset tokens (1 hour expiration)
- **Password Reset**: Users can set new passwords using valid reset tokens
- **Token Security**: Reset tokens are single-use and automatically expire

### 4. Session Management
- **Secure Sessions**: 30-day session cookies with automatic cleanup
- **Session Validation**: Sessions are validated on each request
- **Automatic Logout**: Expired sessions are automatically cleaned up
- **Active User Check**: Only active users can maintain sessions

### 5. Admin User Roles and Privileges
- **User Management**: Admins can view, edit, create, and manage all users
- **Admin Toggle**: Admins can grant/revoke admin privileges (with protection for last admin)
- **User Activation**: Admins can activate/deactivate user accounts
- **Admin Protection**: System prevents removing the last administrator
- **Tournament Management**: Basic admin tournament management page

## Database Schema Enhancements

### Users Table
```sql
- id (Primary Key)
- username (Unique)
- email (Unique)
- password_hash (Salted hash)
- first_name
- last_name
- is_admin (Boolean)
- is_active (Boolean)
- created_at
- updated_at
```

### Sessions Table
```sql
- id (Primary Key)
- user_id (Foreign Key)
- session_token (Unique)
- created_at
- expires_at
```

### Password Resets Table
```sql
- id (Primary Key)
- user_id (Foreign Key)
- reset_token (Unique)
- created_at
- expires_at
- used (Boolean)
```

## Security Features

### Password Security
- Minimum 8 character password requirement
- Salted password hashing using SHA-256
- Secure password verification
- Password change requires current password verification

### Session Security
- Cryptographically secure session tokens
- 30-day session expiration
- Automatic session cleanup on expiration
- Session validation on each request

### Reset Token Security
- Cryptographically secure reset tokens
- 1-hour expiration for reset tokens
- Single-use reset tokens
- Automatic token cleanup

### Admin Protection
- First user automatically becomes admin
- Cannot remove admin privileges from last admin
- Admin-only routes protected with decorators
- Proper access control validation

## Routes and Endpoints

### Authentication Routes
- `GET /login` - Login page
- `POST /auth/login` - Process login
- `GET /register` - Registration page
- `POST /auth/register` - Process registration
- `GET /logout` - Logout and clear session

### Password Reset Routes
- `GET /forgot-password` - Forgot password page
- `POST /auth/forgot-password` - Process password reset request
- `GET /reset-password?token=<token>` - Password reset form
- `POST /auth/reset-password` - Process password reset

### Profile Management Routes
- `GET /profile` - View user profile (requires auth)
- `GET /profile/edit` - Edit profile form (requires auth)
- `POST /profile/update` - Update profile (requires auth)
- `GET /profile/change-password` - Change password feature coming soon (requires auth)
- `POST /profile/change-password` - Change password feature coming soon (requires auth)

### Admin Routes
- `GET /admin/users` - User management dashboard (requires admin)
- `GET /admin/users/new` - Add new user form (requires admin)
- `POST /admin/users/create` - Create new user (requires admin)
- `GET /admin/users/<id>/edit` - Edit user form (requires admin)
- `POST /admin/users/<id>/update` - Update user (requires admin)
- `GET /admin/users/<id>/toggle-admin` - Toggle admin status (requires admin)
- `GET /admin/users/<id>/toggle-active` - Toggle user status (requires admin)
- `GET /admin/tournaments` - Tournament management (requires admin)

## UI Enhancements

### Enhanced Styling
- Modern, responsive design with enhanced CSS
- Professional color scheme and typography
- Improved form styling with focus states
- Enhanced table styling with hover effects
- Status badges and alerts
- Admin panel styling
- Mobile-responsive design

### User Experience
- Clear navigation between user management features
- Informative success and error messages
- Professional profile management interface
- Intuitive admin dashboard
- Responsive design for mobile devices

## Usage Instructions

### For Regular Users
1. **Registration**: Visit `/register` to create a new account
2. **Login**: Use `/login` to access your account
3. **Profile**: Click "Profile" from the home page to manage your account
4. **Password Reset**: Use "Forgot Password?" link on login page if needed

### For Administrators
1. **User Management**: Access `/admin/users` from the admin panel on home page
2. **Create Users**: Use "Add New User" button in user management
3. **Edit Users**: Click "Edit" next to any user in the user table
4. **Manage Permissions**: Toggle admin/active status for users
5. **Tournament Management**: Access basic tournament admin features

## Security Considerations

### Password Policy
- Minimum 8 characters required
- Consider implementing additional complexity requirements in production

### Email Integration
- Currently shows reset links directly (for development)
- In production, integrate with email service (SendGrid, Mailgun, etc.)

### Rate Limiting
- Consider implementing rate limiting for login attempts and password resets

### HTTPS
- Always use HTTPS in production for secure session management

## Future Enhancements

### Potential Improvements
1. Email verification for new accounts
2. Two-factor authentication
3. User role system beyond admin/user
4. User activity logging
5. Advanced password complexity requirements
6. Account lockout after failed login attempts
7. Email notifications for account changes
8. User profile pictures
9. Social login integration
10. API key management for admin users

## Development Notes

### Dependencies
- No additional Python packages required beyond existing FastHTML setup
- Uses built-in `hashlib`, `secrets`, and `datetime` modules
- Email functionality would require additional packages in production

### Database Migration
- The enhanced schema will automatically create new columns when the app starts
- Existing user data will need to have default values set for new fields
- Consider running a migration script for production deployments

### Testing
- Test all authentication flows
- Verify session management
- Test admin privilege escalation protection
- Test password reset flow
- Verify responsive design on various devices

This implementation provides a solid foundation for user management in the Golf Pickem League application, with security best practices and a professional user interface.
