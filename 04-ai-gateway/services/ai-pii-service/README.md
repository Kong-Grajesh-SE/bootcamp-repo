# AI PII Anonymizer Service

This is an HTTP API service that provides the ability to identify and anonymize PII information, as well as sanitizing credentials and passwords.

Two endpoints are available:

* `POST /llm/v1/sanitize`: sanitize specified types of pii information, including credentials, and custom patterns
* `POST /llm/v1/sanitize_credentials`: only for sanitizing credentials

# Get started

First run the API server, then make requests to it.

## Run with Python

First install dependencies via [Poetry](https://python-poetry.org/):

```sh
$ poetry install
```

The run the server:

```sh
$ python ai-pii-service/server.py [-p 8080] [-c ai_pii_service/nlp_engine_conf.yml] [--log_level info]
```

## Run with Docker

You can run with Docker by building the image:

```sh
$ docker build -t pii-service .
```

And then running the container (the following example exposes the service on port `9000`):

```sh
$ docker run -d --name pii-service -p 9000:8080 pii-service
```

Three envs can be specified:

* GUNICORN_WORKERS: specifies the number of gunicorn processes to run

* PII_SERVICE_ENGINE_CONF: specifies the nlp engine configuration file

* GUNICORN_LOG_LEVEL: specifies log level

* GUNICORN_CERTFILE: path to the TLS certificate file. When both GUNICORN_CERTFILE and GUNICORN_KEYFILE are set, the server will listen on port 8443 with HTTPS instead of port 8080 with HTTP.

* GUNICORN_KEYFILE: path to the TLS private key file

So you can run the container:

```sh
$ docker run -d --name pii-service -p 9000:8080 -e GUNICORN_WORKERS=2 -e GUNICORN_LOG_LEVEL=info -e PII_SERVICE_ENGINE_CONF=/app/nlp_engine_conf.yml pii-service
```

To enable TLS:

```sh
$ docker run -d --name pii-service -p 9000:8443 \
  -v /path/to/certs:/certs:ro \
  -e GUNICORN_CERTFILE=/certs/server.crt \
  -e GUNICORN_KEYFILE=/certs/server.key \
  pii-service
```

**Note**: The Docker distribution includes settings that are more suitable for production use, including using Gunicorn as the ingress server to run the underlying Flask application.

## Making a request

You can use the API like:

```sh
$ curl -X POST http://localhost:8080/llm/v1/sanitize -H "Content-Type: application/json" -d '{
    "text": "Hello world, this is John Doe and you can call me at 999-999-9999. I really like to use kong products!",
    "anonymize": ["all_and_credentials"],
		"options": {
			"redact_type": "placeholder"
		}
}'
```

When sanitizing PII, we can also enter custom regex recognizers:

```sh
$ curl -X POST http://localhost:8080/llm/v1/sanitize -H "Content-Type: application/json" -d '{
	"text": "Hello world, this is John Doe and you can call me at 999-999-9999. I really like to use all kong products!",
	"options": {
		"redact_type": "placeholder"
	},
	"anonymize": [
		"all"
	],
	"custom_patterns": [
		{
			"name": "AnotherNamePattern",
			"regex": "\\bkong\\b",
			"score": 0.8
		}
	]
}'
```

## Available anonymization modes

You can anonymize using the following redact modes:

* `placeholder`: Redact the sensitive data with a fixed placeholder pattern: PLACEHOLDER{i} where `i` is a sequence number and the same original text share the same number.
* `synthetic`: Redact the sensitive data with a word in the same type. **Note**: For custom patterns, they will be replaced with CUSTOM{i}, and for credentials, a string of '#' with the same length as the original string will be used as a replacement.

## Custom patterns

You can introduce an array of custom patterns on a per-request basis. Today we support regex patterns and all fields are required `name`, `regex` and `score`).

The `name` should also be unique for different patterns.

## Fields that can be anonymized

You can use these fields in the `anonymize` array:

* `general`: Anonymizes general PII entities such as person names, locations, and organizations.
* `phone`: Anonymizes phone numbers (e.g., mobile, landline).
* `email`: Anonymizes email addresses.
* `creditcard`: Anonymizes credit card numbers.
* `crypto`: Anonymizes cryptocurrency addresses.
* `date`: Anonymizes dates and timestamps.
* `ip`: Anonymizes IP addresses (both IPv4 and IPv6).
* `nrp`: Anonymizes a person’s Nationality, religious or political group.
* `ssn`: Anonymizes Social Security Numbers (SSN) and other related identifiers like ITIN, NIF, ABN, and more.
* `domain`: Anonymizes domain names.
* `url`: Anonymizes web URLs.
* `medical`: Anonymizes medical identifiers (e.g., medical license numbers, NHS numbers, Medicare numbers).
* `driverlicense`: Anonymizes driver's license numbers.
* `passport`: Anonymizes passport numbers.
* `bank`: Anonymizes bank account numbers and related banking identifiers (e.g., VAT codes, IBAN, etc).
* `nationalid`: Anonymizes various national identification numbers (e.g., Aadhaar, PESEL, NRIC, social security, or voter IDs).
* `custom`: Anonymizes user-defined custom PII patterns using regular expressions only when custom patterns are provided.
* `credentials`: Anonymizes the credentials like we would do with `/sanitize_credentials`.
* `all`: Includes all the fields above, including custom ones.

# Running tests

Execute the following command:

```sh
$ poetry run pytest tests/test_server.py
```

# License

This is a proprietary application as stated in the [LICENSE](https://github.com/Kong/ai-pii-service/blob/main/LICENSE).