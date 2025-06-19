# Setting Up Gemini API for Agri Connect

## Getting a Gemini API Key

1. Visit the [Google AI Studio](https://makersuite.google.com/) website
2. Sign in with your Google account
3. Go to "API Keys" in your settings
4. Create a new API key
5. Copy the generated API key

## Configuring the API Key

### Development Environment

1. In the `backend` directory, locate the `.env` file
2. Find the line: `GEMINI_API_KEY=replace-with-your-actual-gemini-api-key`
3. Replace the placeholder with your actual API key
4. Save the file

```
GEMINI_API_KEY=your-actual-api-key-from-google-ai-studio
```

### Production Environment

For production, set the environment variable directly on your server:

```bash
export GEMINI_API_KEY=your-actual-api-key-from-google-ai-studio
```

Or add it to your hosting platform's environment variables configuration.

## Security Notes

- Never commit your actual API key to the repository
- The `.env` file is already in `.gitignore` to prevent accidental commits
- For team development, share the `.env.example` file which contains the format but not actual keys
- Each developer should create their own `.env` file locally
- For production, use a secure method to manage environment variables 