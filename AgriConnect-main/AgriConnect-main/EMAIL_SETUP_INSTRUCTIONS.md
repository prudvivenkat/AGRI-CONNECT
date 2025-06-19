# Email Verification Setup Instructions

## Overview
The application now uses real email verification for user registration. When a user registers with an email address, they will receive a verification code via email that they must enter to complete the registration process.

## Setting Up Gmail for Sending Verification Emails

To enable email sending functionality, you need to set up a Gmail account with an App Password. **Please see the detailed GMAIL_SETUP_GUIDE.md file for step-by-step instructions with screenshots and troubleshooting tips.**

1. **Configure Your Gmail Account**:
   - Use any Gmail account you have access to
   - Make sure you can receive text messages for verification

2. **Enable 2-Step Verification**:
   - Go to your Google Account settings: https://myaccount.google.com/
   - Navigate to "Security" > "2-Step Verification"
   - Follow the steps to enable 2-Step Verification
   - This is required to generate an App Password

3. **Create an App Password**:
   - After enabling 2-Step Verification, go back to the Security page
   - Scroll down and click on "App passwords"
   - Select "Other (Custom name)" and enter "AgriConnect"
   - Click "Generate" to create an app password
   - Copy the 16-character password that appears (without spaces)

4. **Update the .env File**:
   - Open the `backend/.env` file
   - Set both the `EMAIL_ID` and `EMAIL_PASSWORD` values:
     ```
     EMAIL_ID=your-gmail-address@gmail.com
     EMAIL_PASSWORD=yoursixteencharacterapppassword
     ```
   - Note: Remove all spaces from the App Password when adding it to the .env file

## How Email Verification Works

1. **Registration Process**:
   - When a user registers with an email address, the system generates a 6-digit OTP
   - The OTP is sent to the user's email address
   - The OTP is stored in the database with an expiration time (5 minutes)

2. **Verification Process**:
   - The user is redirected to the verification page
   - The user enters the OTP they received via email
   - If the OTP is correct and not expired, the user's account is verified
   - The user is then logged in and redirected to the dashboard

3. **Resend Functionality**:
   - If the user doesn't receive the email, they can request a new code
   - A new OTP is generated and sent to the user's email
   - The previous OTP is invalidated

## Troubleshooting

If emails are not being sent:

1. **Check Gmail Settings**:
   - Ensure that "Less secure app access" is enabled in your Google account settings
   - Make sure the app password is correctly entered in the .env file
   - Check if your Gmail account has any restrictions that might block automated emails

2. **Check Server Logs**:
   - Look for any SMTP-related errors in the server logs
   - Verify that the connection to the SMTP server is successful

3. **Test Email Configuration**:
   - You can test the email configuration by sending a test email
   - Use the Python `smtplib` module to send a test email

## Security Considerations

- The app password gives limited access to your Gmail account for sending emails only
- Never commit your app password to version control
- In a production environment, consider using a dedicated email service like SendGrid or Mailgun
- OTPs expire after 5 minutes for security reasons
- Failed verification attempts are logged for security monitoring
