# Gmail Setup Guide for AgriConnect Email Verification

## Problem
If you're seeing the error: `Failed to send email: (535, b'5.7.8 Username and Password not accepted...`, it means Gmail is rejecting your login credentials. This is a common issue when using Gmail for sending emails from applications.

## Solution
You need to set up your Gmail account correctly and use an App Password instead of your regular password. Follow these detailed steps:

## Step 1: Enable 2-Step Verification on Your Gmail Account

1. Go to your Google Account: https://myaccount.google.com/
2. Click on "Security" in the left sidebar
3. Scroll down to "Signing in to Google"
4. Click on "2-Step Verification"
5. Follow the steps to turn on 2-Step Verification
6. You may need to verify your phone number during this process

## Step 2: Generate an App Password

After enabling 2-Step Verification:

1. Go back to your Google Account Security page
2. Scroll down to "Signing in to Google" again
3. Click on "App passwords" (you might need to sign in again)
4. At the bottom, click "Select app" and choose "Other (Custom name)"
5. Enter "AgriConnect" as the name
6. Click "Generate"
7. Google will display a 16-character password (with spaces)
8. **IMPORTANT**: Copy this password immediately - you won't be able to see it again!

## Step 3: Update Your .env File

1. Open the `backend/.env` file in your project
2. Update the email settings:
   ```
   EMAIL_ID=your-gmail-address@gmail.com
   EMAIL_PASSWORD=your16characterapppassword
   ```
3. **IMPORTANT NOTES**:
   - Use your actual Gmail address for EMAIL_ID
   - For EMAIL_PASSWORD, use the 16-character App Password you generated
   - Remove all spaces from the App Password when adding it to the .env file
   - Make sure there are no extra spaces or quotes around the values

## Step 4: Restart Your Application

After updating the .env file, restart your backend server for the changes to take effect.

## Common Issues and Solutions

### 1. "Username and Password not accepted" Error
- Make sure you're using an App Password, not your regular Gmail password
- Verify that you've entered the App Password correctly (no spaces)
- Check that your EMAIL_ID is correct and matches the account where you generated the App Password

### 2. "Access to less secure apps" Issue
- This is no longer relevant if you're using an App Password
- App Passwords bypass the "less secure apps" restriction

### 3. Gmail Sending Limits
- Be aware that Gmail has sending limits (about 500 emails per day for regular accounts)
- For production use, consider a dedicated email service like SendGrid or Mailgun

### 4. Email Not Received
- Check spam/junk folders
- Verify the recipient email address is correct
- Make sure your Gmail account isn't temporarily blocked for suspicious activity

## Testing Your Setup

After completing these steps, try registering a new user with a valid email address. The system should now successfully send a verification code to that email.

If you continue to have issues, check the server logs for more detailed error messages that can help identify the specific problem.
