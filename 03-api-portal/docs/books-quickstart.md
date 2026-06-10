# Bookstore API Quick Start

## Browse Books

```bash
curl -H "apikey: YOUR_KEY" https://<YOUR_SERVERLESS_PROXY_URL>/books
```

## Get a Specific Book

```bash
curl -H "apikey: YOUR_KEY" https://<YOUR_SERVERLESS_PROXY_URL>/books/42
```

## Add a Book

```bash
curl -X POST -H "apikey: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "isbn": "978-0451524935", "genre": "Fiction", "price": 9.99}' \
  https://<YOUR_SERVERLESS_PROXY_URL>/books
```

## Browse Authors

```bash
curl -H "apikey: YOUR_KEY" https://<YOUR_SERVERLESS_PROXY_URL>/authors
```

## Get a Specific Author

```bash
curl -H "apikey: YOUR_KEY" https://<YOUR_SERVERLESS_PROXY_URL>/authors/7
```

## Browse Reviews

```bash
curl -H "apikey: YOUR_KEY" https://<YOUR_SERVERLESS_PROXY_URL>/reviews
```

## Submit a Review

```bash
curl -X POST -H "apikey: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"bookId": 42, "rating": 5, "comment": "A masterpiece!", "reviewer": "Jane Doe"}' \
  https://<YOUR_SERVERLESS_PROXY_URL>/reviews
```

## Error Handling

| Status | Meaning | Action |
|--------|---------|--------|
| 200 | Success | Process the response |
| 201 | Created | Resource was created |
| 401 | Unauthorized | Check your API key |
| 404 | Not found | Check the resource ID |
