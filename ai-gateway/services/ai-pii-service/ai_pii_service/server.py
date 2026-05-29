import os
import time
import argparse
import logging
import itertools
import json
from flask import Flask, request, jsonify
from flask.json.provider import DefaultJSONProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer.entities import OperatorConfig
from presidio_analyzer import PatternRecognizer, Pattern, AnalyzerEngine
from password_recognizer import PasswordRecognizer
from langdetect import detect
from faker import Faker

class CustomJSONProvider(DefaultJSONProvider):
    def dumps(self, obj, **kwargs):
        kwargs.setdefault('ensure_ascii', False)
        return json.dumps(obj, **kwargs)

    def loads(self, s, **kwargs):
        return json.loads(s, **kwargs)

LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

app = Flask(__name__)
app.json_provider_class = CustomJSONProvider
app.json = app.json_provider_class(app)

anonymizer = AnonymizerEngine()
global_analyzer = None

NLP_ENGINE_CONF = "ai_pii_service/nlp_engine_conf.yml"
NLP_CONFIGURATION = None
SUPPORTED_LANGS = None

# Fallback mapping used when no model_to_presidio_entity_mapping is provided in the conf file.
# This overrides presidio's built-in default to cover NER labels not included there
# (e.g. labels from the Stanza Korean model).
DEFAULT_MODEL_TO_PRESIDIO_ENTITY_MAPPING = dict(
    # Default mappings
    PER="PERSON",
    PERSON="PERSON",
    LOC="LOCATION",
    LOCATION="LOCATION",
    GPE="LOCATION",
    ORG="ORGANIZATION",
    DATE="DATE_TIME",
    TIME="DATE_TIME",
    NORP="NRP",
    AGE="AGE",
    ID="ID",
    EMAIL="EMAIL",
    PATIENT="PERSON",
    STAFF="PERSON",
    HOSP="ORGANIZATION",
    PATORG="ORGANIZATION",
    PHONE="PHONE_NUMBER",
    HCW="PERSON",
    HOSPITAL="ORGANIZATION",

    #Korean model compat
    PS="PERSON",
    LC="LOCATION",
    OG="ORGANIZATION"
)

REDACT_TYPES = ["synthetic", "placeholder"]
PASSWORD_ENTITY = "PASSWORD"
MASKED_CHAR_PASSWORD = "#"
MASK_LENGTH = 8
PASSWORD_REPLACEMENT = MASKED_CHAR_PASSWORD * MASK_LENGTH

CUSTOM_ENTITY = "CUSTOM"

ANONYMIZE_MAP = {
    "general": ["PERSON", "LOCATION", "ORGANIZATION"],
    "phone": ["PHONE_NUMBER"],
    "email": ["EMAIL_ADDRESS"],
    "creditcard": ["CREDIT_CARD"],
    "crypto": ["CRYPTO"],
    "date": ["DATE_TIME"],
    "ip": ["IP_ADDRESS"],
    "nrp": ["NRP"],
    "ssn": ["US_SSN", "US_ITIN", "ES_NIF", "AU_ABN", "AU_ACN", "AU_TFN", "IN_PAN"],
    # "ssn": ["US_SSN"],
    "url": ["URL"],
    "medical": ["MEDICAL_LICENSE", "UK_NHS", "AU_MEDICARE"],
    # "medical": ["MEDICAL_LICENSE"],
    "driverlicense": ["DRIVER_LICENSE", "IT_DRIVER_LICENSE", "IN_VEHICLE_REGISTRATION"],
    # "passport": ["US_PASSPORT", "IT_PASSPORT", "IN_PASSPORT"],
    "passport": ["US_PASSPORT"],
    "bank": ["US_BANK_NUMBER", "IT_VAT_CODE", "IBAN_CODE"],
    "nationalid": [
        "NATIONAL_ID",
        "ES_NIE",
        "IT_FISCAL_CODE",
        "IT_IDENTITY_CARD",
        "PL_PESEL",
        "SG_NRIC_FIN",
        "SG_UEN",
        "IN_AADHAAR",
        "IN_VOTER",
        "FI_PERSONAL_IDENTITY_CODE",
    ],
    "custom": [CUSTOM_ENTITY],
    "credentials": [PASSWORD_ENTITY],
}

ALL_ANONYMIZERS = list(
    set(entity for entities in ANONYMIZE_MAP.values() for entity in entities)
)

ALL_WITHOUT_CREDENTIAL = list(
    set(entity for entities in ANONYMIZE_MAP.values() for entity in entities if entity != PASSWORD_ENTITY)
)

# Remove subspan
# Any result that contains or is contained in an ORGANIZATION result
# will be prioritized
def remove_subspan(results):
    results = sorted(results, key=lambda x: -(x.end - x.start))
    filtered_results = []
    orgs = []

    for result in results:
        if result.entity_type == "ORGANIZATION":
            orgs.append(result)
            continue
        to_keep = True
        for filtered in filtered_results:
            if result.contained_in(filtered):
                to_keep = False
                break
        if to_keep:
            filtered_results.append(result)

    for org in orgs:
        to_keep = True
        for result in filtered_results:
            if org.contained_in(result) or org.contains(result):
                to_keep = False
                break
        if to_keep:
            filtered_results.append(org)

    return filtered_results

def get_sorted_anonymize_keys(values):
    result = set()
    for key, mapped_values in ANONYMIZE_MAP.items():
        for value in values:
            if value in mapped_values:
                result.add(key)
    return sorted(list(result))  # return in alphabetical order

def detect_language(text):
    lang_code = detect(text)
    lang_code = 'zh' if lang_code == 'zh-cn' or lang_code == 'zh-tw' else lang_code
    # Return the detected language if supported, otherwise default to English
    return lang_code if lang_code in SUPPORTED_LANGS else "en"

def current_milli_time():
    return round(time.time() * 1000)

def get_entities_to_anonymize(anonymize):
    if not isinstance(anonymize, list):
        raise TypeError("No valid `anonymize` found")
    
    if "all_and_credentials" in anonymize:
        return ALL_ANONYMIZERS
    
    if "all" in anonymize:
        return ALL_WITHOUT_CREDENTIAL

    entities_to_anonymize = []
    for entity in anonymize:
        try:
            assert isinstance(entity, str)
        except AssertionError:
            raise TypeError(f"Invalid type of item found in `anonymize`: {entity}")

        entity = entity.lower()
        if entity in ANONYMIZE_MAP:
            entities_to_anonymize.extend(ANONYMIZE_MAP[entity])
        else:
            raise TypeError(f"Invalid item found in `anonymize`: {entity}")

    return entities_to_anonymize

def create_analyzer_with_custom_patterns(analyzer, custom_patterns):
    patterns = [
        Pattern(
            name=pattern.get("name"),
            regex=pattern.get("regex"),
            score=pattern.get("score")
        )
        for pattern in custom_patterns
    ]

    if patterns and len(patterns) > 0:
        custom_recognizer = PatternRecognizer(
            supported_entity=CUSTOM_ENTITY, patterns=patterns
        )
        analyzer.registry.add_recognizer(custom_recognizer)

    return analyzer

# Use the global analyzer if no custom patterns, otherwise create a custom one
def get_analyzer(custom_patterns):
    if custom_patterns and len(custom_patterns) > 0:
        return create_analyzer_with_custom_patterns(global_analyzer, custom_patterns)

    return global_analyzer

def remove_duplicated_span(results):
    filtered_results = dict()
    for result in results:
        key = "%s:%s" % (result.start, result.end)
        existed = filtered_results.get(key)
        if existed is None:
            filtered_results[key] = result
            continue
        
        if result.score > existed.score:
            filtered_results.update({key: result})
    return list(filtered_results.values())

def find_all_indexes(main_string, substring):
    indices = []
    if not substring:
        return indices

    start_index = 0

    while True:
        start_index = main_string.find(substring, start_index)
        if start_index == -1:
            break

        indices.append(start_index)
        start_index += 1 

    return indices

def get_analyzer_results(text, anonymized_items, op_map, lang):
    results = []
    found = {}
    for item in anonymized_items:
        origin = item["original_text"]
        redact = op_map.get(origin)[0] if op_map.get(origin) else None
        if redact:
            results.append({
                "start": item["start"],
                "end": item["end"],
                "detected_language": lang,
                "original_text": origin,
                "redact_text": redact,
                "entity_type": op_map[origin][1]
            })
            found.setdefault(origin, True)

    # Those not included in items_to_anonymize are merged entities
    # For example: I live in Shanghai China.
    # items_to_anonymize: [{"original_text": "Shanghai"}, {"original_text": "China"}]
    # op_map: {"Shanghai China": ("PLACEHOLDER", "LOCATION")}
    for origin, (redact, et) in op_map.items():
        # skip origin in op_map if already appended from anonymized_items above
        if found.get(origin):
            continue

        indexes = find_all_indexes(text, origin)
        for idx in indexes:
            start, end = idx, idx + len(origin)
            results.append({
                "start": start,
                "end": end,
                "detected_language": lang,
                "original_text": origin,
                "redact_text": redact,
                "entity_type": et
            })

    return sorted(results, key = lambda x: x["start"])

def validate_rpc_request(request):
    if not request:
        return False, "Invalid request: no request body"
    if not request.get("jsonrpc") or request.get("jsonrpc") != "2.0":
        return False, "Invalid request: invalid jsonrpc version"
    if not request.get("method"):
        return False, "Invalid request: no method"
    if not request.get("params"):
        return False, "Invalid request: no params"
    if request.get("id") is None:
        return False, "Invalid request: no idd"
    return True, None

def anonymize_passwords(text, analyzer_results):
    # Process the text based on the anonymization type
    masked_text = text
    offset = 0  # Keep track of character shifts after replacements

    for result in analyzer_results:
        start, end = result.start + offset, result.end + offset
        password_length = end - start

        # Replace the identified password in the text
        masked_text = masked_text[:start] + PASSWORD_REPLACEMENT + masked_text[end:]
        offset += MASK_LENGTH - password_length  # Adjust offset for future replacements

    return masked_text

def jsonrpc_response(result, id):
    return jsonify({"jsonrpc": "2.0", "result": result, "id": id})

def jsonrpc_error_response(error, id):
    return jsonify({"jsonrpc": "2.0", "error": error, "id": id})

def request_validation(data):
    text = data.get("text")
    if not (type(text) is list or type(text) is str):
        raise TypeError("No valid `text` found")

    messages = [ { "text": text, "msg_id": 1 } ] if type(text) is str else text

    anonymize = data.get("anonymize")
    entities_to_anonymize = get_entities_to_anonymize(anonymize)

    def validate_custom_patterns(custom_patterns):
        if not isinstance(custom_patterns, list):
            raise TypeError("Invalid type of `custom_patterns`")
        for pattern in custom_patterns:
            name = pattern.get("name")
            regex = pattern.get("regex")
            score = pattern.get("score")
            if (not (isinstance(name, str) and len(name.strip()) > 0)
            or not (isinstance(regex, str) and len(regex.strip()) > 0)
            or not isinstance(score, float) or score < 0 or score > 1):
                raise TypeError("Invalid item found in `custom_patterns`")

    custom_patterns = data.get("custom_patterns", [])
    validate_custom_patterns(custom_patterns)

    options = data.get("options")
    if not isinstance(options, dict):
        raise TypeError("No valid `options` found")

    redact_type = options.get("redact_type")
    if not isinstance(redact_type, str) or not redact_type in REDACT_TYPES:
        raise TypeError("No valid `redact_type` found")

    return {
        "messages": messages,
        "entities_to_anonymize": entities_to_anonymize,
        "redact_type": redact_type,
        "custom_patterns": custom_patterns
    }

def do_sanitize_pii(data, id=None):
    counter1 = itertools.count(1)
    counter2 = itertools.count(1)
    def get_generator(redact_type, lang):
        nonlocal counter1, counter2
        def custom_gen():
            return f"CUSTOM{next(counter1)}"

        def placeholder_gen(_):
                return f"PLACEHOLDER{next(counter2)}"

        default_fn = lambda: "#####"

        class SafeFakerWrapper:
            def __init__(self, faker_instance):
                self._faker = faker_instance

            def __getattr__(self, name):
                if hasattr(self._faker, name):
                    return getattr(self._faker, name)
                else:
                    # You can log it or handle differently here
                    return default_fn

        if redact_type == "synthetic":
            fake = SafeFakerWrapper(Faker([lang]))

            def faker_gen(entity_type):
                fake_map = {
                    "PERSON": fake.name,
                    "LOCATION": fake.city,
                    "ORGANIZATION": fake.company,
                    "PHONE_NUMBER": fake.phone_number,
                    "EMAIL_ADDRESS": fake.email,
                    "CITY": fake.city,
                    "NRP": fake.country,
                    "CREDIT_CARD": fake.credit_card_number,
                    "DATE_TIME": lambda: fake.date_time().strftime('%Y-%m-%d %H:%M:%S'),
                    "IP_ADDRESS": fake.ipv4,
                    "US_SSN": fake.ssn,
                    "US_ITIN": fake.itin,
                    "ES_NIF": fake.ssn,
                    "AU_ABN": fake.ssn,
                    "AU_ACN": fake.ssn,
                    "AU_TFN": fake.ssn,
                    "IN_PAN": fake.ssn,
                    "DOMAIN_NAME": fake.safe_domain_name,
                    "URL": fake.url,
                    "CUSTOM": custom_gen,
                    "PASSWORD": lambda: PASSWORD_REPLACEMENT,
                    "CRYPTO": None,
                    "MEDICAL_LICENSE": None,
                    "UK_NHS": None,
                    "AU_MEDICARE": None,
                    "DRIVER_LICENSE": None,
                    "IT_DRIVER_LICENSE": None,
                    "IN_VEHICLE_REGISTRATION": None,
                    "US_PASSPORT": None,
                    "IT_PASSPORT": None,
                    "IN_PASSPORT": None,
                    "US_BANK_NUMBER": None,
                    "IT_VAT_CODE": None,
                    "IBAN_CODE": None,
                    "NATIONAL_ID": None,
                    "ES_NIE": None,
                    "IT_FISCAL_CODE": None,
                    "IT_IDENTITY_CARD": None,
                    "PL_PESEL": None,
                    "SG_NRIC_FIN": None,
                    "SG_UEN": None,
                    "IN_AADHAAR": None,
                    "IN_VOTER": None,
                    "FI_PERSONAL_IDENTITY_CODE": None
                }

                fn = fake_map.get(entity_type, default_fn) or default_fn
                return fn()

            return faker_gen
        else:
            return placeholder_gen

    start_time = current_milli_time()
    messages = data.get("messages")
    redact_type = data.get("redact_type")
    entities_to_anonymize = data.get("entities_to_anonymize")
    custom_patterns = data.get("custom_patterns")

    analyzer = get_analyzer(custom_patterns)
    identified_pii_set = set()
    anonymized_pii_set = set()
    sanitized_messages = []
    for message in messages:
        msg_id = message.get("msg_id")
        if not isinstance(msg_id, int):
            raise TypeError("No valid `msg_id` found")
        
        text = message.get("text")
        if type(text) != str:
            raise TypeError("`text` in the message is not string")

        analyzer_results = []
        if len(text.strip()) == 0:
            sanitized_messages.append(
                {
                    "sanitized_text": text,
                    "analyzer_results": [],
                    "detected_language": None,
                    "msg_id": msg_id
                }
            )
            continue

        try:
            detected_lang = detect_language(text)
        except Exception:
            sanitized_messages.append({
                "sanitized_text": text, "detected_language": "unknown", "msg_id": msg_id,
                "analyzer_results": []
            })
            continue

        analyzer_results = analyzer.analyze(text=text, entities=ALL_ANONYMIZERS, language=detected_lang)
        # keep the one with the highest score for the same spans
        unique_results = remove_duplicated_span(analyzer_results)
        sorted_results = sorted(remove_subspan(unique_results), key = lambda x: x.start)
        identified_pii_set.update({result.entity_type for result in sorted_results})
        # Filter results to only include the entities specified in `entities_to_anonymize`
        results_to_anonymize = [ result for result in sorted_results if result.entity_type in entities_to_anonymize ]
        anonymized_pii_set.update({result.entity_type for result in results_to_anonymize})
        # If there are entities to anonymize, perform the anonymization
        items_to_anonymize = [
            result.to_dict()
            for result in results_to_anonymize
        ]

        operation_map = {}
        anonymized_text= None
        if len(items_to_anonymize) > 0:
            anonymizer_config = {}
            redact_map = {}
            generator = get_generator(redact_type, detected_lang)
            for item in items_to_anonymize:
                # save original text
                original_text = text[item.get("start") : item.get("end")]
                item.update({"original_text": original_text, "start": item.get("start"), "end":item.get("end")})

                # Create the anonymizer configuration
                entity_type = item.get("entity_type")
                anonymizer_config.setdefault(
                    entity_type,
                    OperatorConfig("custom", {
                        "lambda": lambda t, _et=entity_type: (
                            redact_map[t] if t in redact_map
                            else
                                "" if t == "PII" # not sure how comes we see 'PII', but exclude it
                                else
                                    operation_map.setdefault(t, (redact_map.setdefault(t, generator(_et)), _et))[0]
                        )
                    })
                )

            # Perform anonymization only on the identified entities that should be anonymized
            anonymized_result = anonymizer.anonymize(text=text, analyzer_results=results_to_anonymize, operators=anonymizer_config)
            anonymized_text = anonymized_result.text

        analyzer_results = get_analyzer_results(text, items_to_anonymize, operation_map, detected_lang)
        sanitized_messages.append({
            "sanitized_text": anonymized_text or text, "detected_language": detected_lang, "msg_id": msg_id,
            "analyzer_results": analyzer_results
        })

    ret = {
        "text": sanitized_messages,
        "identified_pii": get_sorted_anonymize_keys(list(identified_pii_set)),
        "anonymized_pii": get_sorted_anonymize_keys(list(anonymized_pii_set)),
        "detected_languages": list({
            message["detected_language"] for message in sanitized_messages
            if message["detected_language"]
        }),
        "duration": current_milli_time() - start_time
    }

    logging.info(f"--- Sanitize PII Request ---\n{json.dumps(data, indent=2)}")
    logging.info(f"--- Sanitize PII Response ---\n{json.dumps(ret, indent=2)}")

    if id is not None:
        return jsonrpc_response(ret, id)
    return jsonify(ret)

def do_sanitize_credentials(data, id=None):
    start_time = current_milli_time()
    text = data.get("text")
    if not (type(text) is list or type(text) is str):
        raise TypeError("No valid `text` found")

    messages = [ { "text": text, "msg_id": 1 } ] if type(text) is str else text

    sanitized_messages = []

    for message in messages:
        msg_id = message.get("msg_id")
        if not isinstance(msg_id, int):
            raise TypeError("No valid `msg_id` found")
        
        text = message.get("text")
        if type(text) != str:
            raise TypeError("`text` in the message is not string")
        analyzer_results = []
        if len(text.strip()) == 0:
            sanitized_messages.append(
                {
                    "sanitized_text": text,
                    "analyzer_results": [],
                    "detected_language": None,
                    "msg_id": msg_id
                }
            )
            continue

        detected_lang = detect_language(text)

        analyzer_results = global_analyzer.analyze(
            text=text, entities=[PASSWORD_ENTITY], language=detected_lang
        )
        analyzer_results = sorted(analyzer_results, key=lambda x: x.start)

        masked_text = text
        if len(analyzer_results) > 0:
            masked_text = anonymize_passwords(text, analyzer_results)

        sanitized_messages.append({
            "sanitized_text": masked_text,
            "detected_language": detected_lang,
            "msg_id": msg_id,
            "analyzer_results": [ {
                "start": result.start,
                "end": result.end,
                "detected_language": detected_lang,
                "original_text": text[result.start : result.end],
                "redact_text": PASSWORD_REPLACEMENT,
                "entity_type": result.entity_type
            } for result in analyzer_results ]
        })

    ret = {
        "text": sanitized_messages,
        "identified_pii": [ "credentials" ] if len(analyzer_results) > 0 else [],
        "anonymized_pii": [ "credentials" ] if len(analyzer_results) > 0 else [],
        "detected_languages": list({
            message["detected_language"] for message in sanitized_messages
        if message["detected_language"]
        }),
        "duration": (current_milli_time() - start_time),
    }

    logging.info(f"--- Sanitize Credentials Request ---\n{json.dumps(data, indent=2)}")
    logging.info(f"--- Sanitize Credentials Response ---\n{json.dumps(ret, indent=2)}")

    if id is not None:
        return jsonrpc_response(ret, id)
    return jsonify(ret)

@app.route("/", methods=["POST"])
def dispatch_rpc():
    method_prefix = "llm.v1."
    data = request.json
    ok, err = validate_rpc_request(data)
    if not ok:
        return jsonify({"error": err}), 400
    params = data.get("params")
    id = data.get("id")

    try:
        if data.get("method") == method_prefix + "sanitizePrompt":
            data = request_validation(params)
            return do_sanitize_pii(data, id)

        elif data.get("method") == method_prefix + "sanitize_credentials":
            return do_sanitize_credentials(params, id)
        
        else:
            return jsonify({"error": "Invalid method"}), 400
    except Exception as e:
        logging.exception("Error:")
        return jsonify({ "error": str(e)}), 400

@app.route("/llm/v1/sanitize", methods=["POST"])
def sanitize_pii():
    logging.info(f"--- Raw Incoming Request to {request.path} ---\n{json.dumps(request.json, indent=2)}")
    try:
        data = request_validation(request.json)
        return do_sanitize_pii(data)
    except Exception as e:
        logging.exception("Error:")
        return jsonify({ "error": str(e)}), 400

@app.route("/llm/v1/sanitize_credentials", methods=["POST"])
def sanitize_credentials():
    logging.info(f"--- Raw Incoming Request to {request.path} ---\n{json.dumps(request.json, indent=2)}")
    try:
        return do_sanitize_credentials(request.json)
    except Exception as e:
        logging.exception("Error:")
        return jsonify({ "error": str(e)}), 400

@app.route("/llm/v1/status", methods=["GET"])
def status():
    return jsonify({
        "status": "ok",
        "supported_languages": list(SUPPORTED_LANGS),
        })

def init_globals(engine_conf):
    global NLP_CONFIGURATION, SUPPORTED_LANGS, global_analyzer
    # Configure the spaCy NLP engine
    provider = NlpEngineProvider(conf_file=engine_conf)
    NLP_CONFIGURATION = provider.nlp_configuration
    SUPPORTED_LANGS = {model["lang_code"] for model in NLP_CONFIGURATION["models"]}
    # always add en to simulate regex-based recognizers
    SUPPORTED_LANGS.add('en')
    nlp_engine = provider.create_engine()

    # If the conf file does not provide model_to_presidio_entity_mapping, apply the
    # fallback mapping to cover NER labels missing from presidio's built-in default.
    ner_conf = NLP_CONFIGURATION.get("ner_model_configuration") or {}
    if "model_to_presidio_entity_mapping" not in ner_conf:
        nlp_engine.ner_model_configuration.model_to_presidio_entity_mapping = DEFAULT_MODEL_TO_PRESIDIO_ENTITY_MAPPING

    # Initialize the analyzer
    global_analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=SUPPORTED_LANGS)

    # Add the Password recognizer for every language
    for model in NLP_CONFIGURATION["models"]:
        lang_code = model["lang_code"]
        password_recognizer = PasswordRecognizer(lang_code)
        password_recognizer.supported_language = lang_code
        global_analyzer.registry.add_recognizer(password_recognizer)
        # Add sentencizer to support `doc.sents` in PasswordRecognizer
        nlp_engine.nlp[lang_code].add_pipe('sentencizer')

def cmdline_parser():
    parser = argparse.ArgumentParser(description="Run the PII Sanitization API.")
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8080,
        help="Port to run the server on. Default is 8080.",
    )
    parser.add_argument(
        "--log_level",
        type=str,
        default="info",
        choices=LOG_LEVELS.keys(),
        help="Set the logging level (default: info)"
    )
    parser.add_argument(
        "-c",
        "--engine_conf",
        type=str,
        default=NLP_ENGINE_CONF,
        help="Path to the NLP engine configuration file (default: %s)" % NLP_ENGINE_CONF
    )

    return parser

def main():
    parser = cmdline_parser()
    args = parser.parse_args()

    logging.basicConfig(level=LOG_LEVELS[args.log_level])
    assert os.path.exists(args.engine_conf), f"Error: engine configuration file: `{args.engine_conf}` does not exist"
    init_globals(args.engine_conf)

    app.run(host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()

elif __name__ == "ai_pii_service.server":
    engine_conf = os.getenv("PII_SERVICE_ENGINE_CONF", NLP_ENGINE_CONF)
    assert os.path.exists(engine_conf), f"Error: engine configuration file: `{engine_conf}` does not exist"
    log_level = os.getenv("PII_SERVICE_LOG_LEVEL", "info")
    logging.basicConfig(level=LOG_LEVELS.get(log_level, logging.INFO))
    init_globals(engine_conf)
