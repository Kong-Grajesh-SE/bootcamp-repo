# Bookstore API Quick Start

## Browse Books

```bash
curl -H "apikey: YOUR_KEY" http://localhost:8000/books/get
```

## Get a Specific Book

```bash
curl -H "apikey: YOUR_KEY" http://localhost:8000/books/42/get
```

## Add a Book

```bash
curl -X POST -H "apikey: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "1984", "author": "George Orwell", "isbn": "978-0451524935", "genre": "Fiction", "price": 9.99}' \
  http://localhost:8000/books/post
```

## Browse Authors

```bash
curl -H "apikey: YOUR_KEY" http://localhost:8000/authors/get
```

## Get a Specific Author

```bash
curl -H "apikey: YOUR_KEY" http://localhost:8000/authors/7/get
```

## Browse Reviews

```bash
curl -H "apikey: YOUR_KEY" http://localhost:8000/reviews/get
```

## Submit a Review

```bash
curl -X POST -H "apikey: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"bookId": 42, "rating": 5, "comment": "A masterpiece!", "reviewer": "Jane Doe"}' \
  http://localhost:8000/reviews/post
```

## Error Handling

| Status | Meaning | Action |
|--------|---------|--------|
| 200 | Success | Process the response |
| 201 | Created | Resource was created |
| 401 | Unauthorized | Check your API key |
| 404 | Not found | Check the resource ID |
