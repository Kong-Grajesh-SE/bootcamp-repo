from presidio_analyzer import RecognizerResult, EntityRecognizer
from presidio_analyzer.nlp_engine import NlpArtifacts
import re
import logging

PASSWORD_ENTITY = "PASSWORD"
CREDENTIAL_LENGTH = 5
CONTEXT = {
    "pin", "code", "credential", "password", "security", "otp", "token", 
    "verification", "auth", "authentication", "passcode", "identifier", 
    "access", "key", "login", "secret", "unlock", "challenge"
}
MAX_TOKEN_COUNT = 40
COMMON_WEAK_WORDS = ["1234", "123456", "12345678", "qwerty", "letmein", "helloworld", "welcome", "admin",
                      "abcd", "abcde"]

logger = logging.getLogger('PasswordRecognizer')

class PasswordRecognizer(EntityRecognizer):
    def __init__(self, language):
        super().__init__(supported_entities=[PASSWORD_ENTITY])
        self.common_word_threshold = -7  # Adjust this threshold as needed
        self.language = language

    def load(self):
        pass

    def detect_weak_passwords(self, token):
        results = []

        if (token.text.lower() in COMMON_WEAK_WORDS
            or re.search(r'(.)\1{4,}', token.text) # Repeated Characters 
        ):
            results.append(
                RecognizerResult(
                    entity_type=PASSWORD_ENTITY,
                    start=token.idx,
                    end=token.idx + len(token.text),
                    score=0.9,
                )
            )

        return results

    def detect_concatenated_words(self, token, nlp):
        results = []
        if len(token.text) < 6:
            return results

        for i in range(3, len(token.text) - 3):
            first_part = token.text[:i]
            second_part = token.text[i:]
            first_lexeme = nlp.vocab[first_part]
            second_lexeme = nlp.vocab[second_part]
            logger.debug(
                f"text: {token.text}, first_part: {first_part}(prob: {first_lexeme.prob}), second_part: {second_part}(prob: {second_lexeme.prob})"
            )
            if (
                first_lexeme.prob > self.common_word_threshold
                and second_lexeme.prob > self.common_word_threshold
            ):
                start = token.idx
                end = start + len(token.text)
                results.append(
                    RecognizerResult(
                        entity_type=PASSWORD_ENTITY, start=start, end=end, score=0.9
                    )
                )
                break
        return results

    def detect_unknown_words(self, token):
        if token.is_oov and len(token.text) >= CREDENTIAL_LENGTH:
            return [
                RecognizerResult(
                    entity_type=PASSWORD_ENTITY,
                    start=token.idx,
                    end=token.idx + len(token.text),
                    score=0.85,
                )
            ]
        return []

    def detect_alphanumeric_tokens(self, token):
        if (
            len(token.text) >= CREDENTIAL_LENGTH
            and any(char.isdigit() for char in token.text)
            and any(char.isalpha() for char in token.text)
        ):
            return [
                RecognizerResult(
                    entity_type=PASSWORD_ENTITY,
                    start=token.idx,
                    end=token.idx + len(token.text),
                    score=0.85,
                )
            ]
        return []

    def detect_long_numbers(self, token):
        # Check if the token is a long number
        if token.text.isdigit() and len(token.text) >= 4:
            return [
                RecognizerResult(
                    entity_type=PASSWORD_ENTITY,
                    start=token.idx,
                    end=token.idx + len(token.text),
                    score=0.9,
                )
            ]
        return []

    def analyze(self, text, entities, nlp_artifacts: NlpArtifacts):
        results = []
        doc = nlp_artifacts.tokens
        for sentence in doc.sents:
            token_count = len(sentence)
            if token_count > MAX_TOKEN_COUNT:
                # PasswordRecognizer will have many false positive results
                # for a long sentence so we split long sentence into small by ',' or ';'
                results.extend(self.__analyze_long_sentence(sentence))
            else:
                results.extend(self.__analyze(sentence))

        return results

    def __analyze_long_sentence(self, sentence):
        part = []
        results = []
        for token in sentence:
            if token.text in [',', ';'] and len(part) > 0:
                results.extend(self.__analyze(part))
                part = []
            else:
                part.append(token)

        if len(part) > 0:
            results.extend(self.__analyze(part))
            part = []

        return results

    def __contains_context(self, sentence):
        for c in CONTEXT:
            for token in sentence:
                if c in token.text.lower():
                    return True

        return False

    def __analyze(self, sentence):
        results = []
        if not self.__contains_context(sentence):
            return results
        for token in sentence:
            if (token.is_stop or token.text in CONTEXT
                or len(token.text) < 4
            ):
                continue

            # Detect alphanumeric tokens
            alphanumeric_results = self.detect_alphanumeric_tokens(token)
            if alphanumeric_results:
                logger.debug(f"Alphanumeric token: {token.text}")
                results.extend(alphanumeric_results)
                continue

            # Detect unknown words
            unknown_results = self.detect_unknown_words(token)
            if unknown_results:
                logger.debug(f"Unknown words: {token.text}")
                results.extend(unknown_results)
                continue

            # Detect weak passwords
            weak_password_results = self.detect_weak_passwords(token)
            if weak_password_results:
                logger.debug(f"Weak passwords: {token.text}")
                results.extend(weak_password_results)
                continue

            # Detect concatenated words
            # concatenated_results = self.detect_concatenated_words(token, nlp)
            # if concatenated_results:
            #     results.extend(concatenated_results)
            #     continue

            # Detect long numeric words with trigger words in the same sentence
            long_number_results = self.detect_long_numbers(token)
            if long_number_results:
                logger.debug(f"Long numbers: {token.text}")
                results.extend(long_number_results)

        return results
