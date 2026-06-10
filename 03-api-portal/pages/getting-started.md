# Getting Started with the Bookstore API

Welcome to the Bookstore Developer Portal. This guide walks you through getting your first API key and making your first request.

## Step 1: Create an Account

Click **Sign Up** in the top-right corner and fill in your details. If auto-approve is enabled, you're in immediately.

## Step 2: Create an Application

Once registered, go to **My Apps** and create a new application. Give it a name that describes your integration (e.g., "My Reading List App").

## Step 3: Register for the Bookstore API

Browse the API catalog and click **Register** on the Bookstore API. Select your application and you'll receive an API key.

## Step 4: Make Your First Request

Use the API key in the `apikey` header:

```bash
curl -H "apikey: YOUR_API_KEY" https://<YOUR_SERVERLESS_PROXY_URL>/books
```

## Step 5: Explore the Docs

The Bookstore API has interactive documentation powered by OpenAPI specs. Use the **Try It** panel to make live requests directly from the portal.

## Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/books` | GET, POST | Browse and add books |
| `/books/{bookId}` | GET, PUT, DELETE | Manage a specific book |
| `/authors` | GET | Browse author profiles |
| `/authors/{authorId}` | GET | Get author details |
| `/reviews` | GET, POST | Browse and submit reviews |

## Need Help?

- Check the [API Changelog](/changelog) for recent changes
- Review the [Terms of Service](/terms-of-service) for usage policies
- Contact us at **api-support@bookstore.example.com**
