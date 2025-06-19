# Authentication Flow in AgriConnect

## Overview
This document explains the authentication flow in the AgriConnect application, focusing on how the UI and navigation change based on the user's login status.

## Authentication States

### Not Logged In
When a user is not logged in:
1. Only the Home page is accessible
2. The navigation menu only shows the Home link
3. Login and Register buttons are displayed on the Home page
4. Attempting to access protected routes redirects to the Login page

### Logged In
When a user is logged in:
1. All pages are accessible (based on user role)
2. The navigation menu shows all available links
3. The Home page shows service cards for Equipment, Workers, and Crop Prediction
4. The Login and Register buttons are replaced with a Dashboard button

## Protected Routes
The following routes are protected and require authentication:

1. **User Dashboard Routes**:
   - `/dashboard` - User dashboard
   - `/profile` - User profile

2. **Equipment Module Routes**:
   - `/equipment` - Equipment list
   - `/equipment/:id` - Equipment details
   - `/equipment/add` - Add equipment
   - `/equipment/edit/:id` - Edit equipment
   - `/my-equipment` - User's equipment
   - `/bookings` - Equipment bookings

3. **Worker Module Routes**:
   - `/workers` - Worker list
   - `/workers/:id` - Worker details
   - `/worker-profile` - Worker profile
   - `/my-hirings` - User's hirings
   - `/hiring-requests` - Hiring requests

4. **Prediction Module Route**:
   - `/crop-prediction` - Crop prediction

5. **Admin Routes** (require admin role):
   - `/admin-dashboard` - Admin dashboard
   - `/admin-users` - User management
   - `/admin-equipment` - Equipment management
   - `/admin-workers` - Worker management
   - `/admin-feedback` - Feedback management

## Public Routes
The following routes are publicly accessible:

1. `/` - Home page
2. `/login` - Login page
3. `/register` - Registration page
4. `/verify-otp` - OTP verification page

## Implementation Details

### Route Protection
Route protection is implemented using wrapper components:

1. **ProtectedRoute Component**:
   - Checks if the user is logged in
   - Redirects to the login page if not authenticated
   - Renders the child component if authenticated

2. **AdminRoute Component**:
   - Extends the ProtectedRoute functionality
   - Checks if the authenticated user has the admin role
   - Redirects to the dashboard if the user is not an admin

### UI Conditional Rendering
The UI adapts based on authentication status:

1. **Header Component**:
   - Uses the `currentUser` state from AuthContext
   - Conditionally renders navigation links
   - Shows different menu items for logged-in and logged-out states

2. **Home Component**:
   - Shows login/register buttons for logged-out users
   - Shows dashboard button for logged-in users
   - Only displays service cards when the user is logged in

## Authentication Context
The authentication state is managed by the AuthContext:

1. **Key States**:
   - `currentUser` - Contains user data when logged in, null when logged out
   - `loading` - Indicates if authentication state is being checked

2. **Key Functions**:
   - `login` - Authenticates the user and sets the currentUser state
   - `logout` - Clears the authentication state
   - `register` - Creates a new user account
   - `verifyOTP` - Verifies the OTP during registration

## Security Considerations

1. **Token Storage**:
   - Access tokens are stored in localStorage
   - Refresh tokens are used to obtain new access tokens

2. **Route Protection**:
   - All sensitive routes are protected on the client side
   - API endpoints are also protected on the server side

3. **Session Management**:
   - Sessions expire after a configurable time
   - Users are automatically logged out when tokens expire

## Testing Authentication Flow

To test the authentication flow:

1. **Logged Out State**:
   - Open the application in an incognito window
   - Verify that only the Home page is accessible
   - Verify that attempting to access protected routes redirects to login

2. **Login Process**:
   - Click the Login button on the Home page
   - Enter valid credentials
   - Verify redirection to the Dashboard
   - Verify that all navigation links are now visible

3. **Logout Process**:
   - Click the Logout button
   - Verify redirection to the Home page
   - Verify that protected routes are no longer accessible
