import re
import math
from collections import Counter
from difflib import SequenceMatcher


def email_domain_allowed(email):
    try:
        domain = email.lower().split("@")[1]
        allowed_prefixes = ["hotmail.", "outlook.", "live.", "msn."]
        return any(domain.startswith(p) for p in allowed_prefixes)
    except (IndexError, AttributeError):
        return False


class SpamChecker:
    HIGH_PRIORITY_KEYWORDS = ["whale", "adm", "bdelahw"]
    LOW_PRIORITY_KEYWORDS = ["whal", "whan", "duolc", "cloud", "tg", "snap"]
    OBFUSCATED_KEYWORDS = ["snap", "telegram", "articxu", "carpenater"]
    FORBIDDEN_CHARS = [
        "'",
        '"',
        "\\",
        "/",
        "<",
        ">",
        "{",
        "}",
        "[",
        "]",
        ";",
        ":",
        "&",
        "|",
        "#",
        "%",
        "^",
        "`",
        "~",
        "=",
        "+",
        ",",
        "?",
        "(",
        ")",
        "-",
    ]

    def __init__(self, email, password):
        self.email = email
        self.password = password
        try:
            self.username, self.domain = self.email.split("@", 1)
        except ValueError:
            self.username = self.email
            self.domain = ""
        self.username_lower = self.username.lower()
        self.password_lower = self.password.lower()
        self.username_core = re.sub(r"[^a-z]", "", self.username_lower)
        self.password_core = re.sub(r"[^a-z]", "", self.password_lower)
        self.features = self._extract_all_features()

    def _extract_all_features(self):
        features = {
            "username_len": len(self.username),
            "password_len": len(self.password),
            "username_entropy": self._calculate_entropy(self.username_lower),
            "password_entropy": self._calculate_entropy(self.password_lower),
            "username_transitions": self._count_char_type_transitions(self.username),
            "password_transitions": self._count_char_type_transitions(self.password),
            "contains_high_priority_keyword": self._contains_keywords(
                self.HIGH_PRIORITY_KEYWORDS
            ),
            "contains_low_priority_keyword": self._contains_keywords(
                self.LOW_PRIORITY_KEYWORDS
            ),
            "contains_obfuscated_keyword": self._contains_obfuscated_keywords(),
            "contains_pipe_pattern": "||" in self.password,
            "contains_telegram_pattern": bool(
                re.search(r"t\s*[|:_.-]\s*g", self.password_lower)
            ),
            "password_contains_url": bool(
                re.search(r"https?://|t\.me|wa\.me", self.password_lower)
            ),
            "contains_forbidden_chars": self._contains_forbidden_chars(),
            "contains_consecutive_hyphens": "--" in self.username
            or "--" in self.password,
            "password_is_doubled": self._is_password_doubled(),
            "username_is_repetitive": self._is_username_repetitive(),
            "is_substring": self._is_substring(),
            "cross_repetition": self._has_cross_repetition(),
            "composite_similarity": self._calculate_composite_similarity(),
            "contains_t_g_pattern": self._contains_t_g_pattern(),
        }
        features["username_transition_density"] = (
            (features["username_transitions"] / features["username_len"])
            if features["username_len"] > 0
            else 0
        )
        features["password_transition_density"] = (
            (features["password_transitions"] / features["password_len"])
            if features["password_len"] > 0
            else 0
        )
        return features

    def _calculate_entropy(self, s):
        if not s:
            return 0
        p, lns = Counter(s), float(len(s))
        return -sum(count / lns * math.log(count / lns, 2) for count in p.values())

    def _count_char_type_transitions(self, s):
        if not s or len(s) < 2:
            return 0

        def get_type(char):
            if char.isdigit():
                return "digit"
            if char.isalpha():
                return "alpha"
            return "special"

        transitions = 0
        current_type = get_type(s[0])
        for char in s[1:]:
            next_type = get_type(char)
            if next_type != current_type:
                transitions += 1
                current_type = next_type
        return transitions

    def _contains_keywords(self, keyword_list):
        return any(
            key in self.password_core or key in self.username_core
            for key in keyword_list
        )

    def _contains_obfuscated_keywords(self):
        for key in self.OBFUSCATED_KEYWORDS:
            pattern = r"\W*".join(list(key))
            if re.search(pattern, self.password_lower):
                return True
        return False

    def _contains_forbidden_chars(self):
        return any(char in self.password for char in self.FORBIDDEN_CHARS)

    def _is_password_doubled(self):
        pw_len = len(self.password)
        if pw_len > 2 and pw_len % 2 == 0:
            mid = pw_len // 2
            if self.password[:mid] == self.password[mid:]:
                return True
        return False

    def _is_username_repetitive(self):
        username_len = len(self.username_core)
        if username_len > 12:
            mid = username_len // 2
            part1 = self.username_core[:mid]
            part2 = self.username_core[mid:]
            if SequenceMatcher(None, part1, part2).ratio() > 0.75:
                return True
        return False

    def _is_substring(self):
        if len(self.password_core) >= 4 and self.password_core in self.username_core:
            return True
        if len(self.username_core) >= 4 and self.username_core in self.password_core:
            return True
        return False

    def _has_cross_repetition(self):
        if (
            len(self.username_core) > 3
            and self.password_core.count(self.username_core) >= 2
        ):
            return True
        if (
            len(self.password_core) > 3
            and self.username_core.count(self.password_core) >= 2
        ):
            return True
        return False

    def _calculate_composite_similarity(self):
        sim_ratio_core = SequenceMatcher(
            None, self.username_core, self.password_core
        ).ratio()
        sim_ratio_reversed = SequenceMatcher(
            None, self.username_core, self.password_core[::-1]
        ).ratio()
        return max(sim_ratio_core, sim_ratio_reversed)

    def _contains_t_g_pattern(self):
        return bool(re.search(r"t.*?g", self.password_lower))

    def is_spam(self):
        f = self.features
        if (
            f["contains_forbidden_chars"]
            or f["contains_pipe_pattern"]
            or f["contains_consecutive_hyphens"]
        ):
            return True

        if (
            not f["contains_high_priority_keyword"]
            and not f["contains_low_priority_keyword"]
        ):
            return f["contains_obfuscated_keyword"]

        spam_conditions = [
            f["cross_repetition"],
            f["password_contains_url"],
            f["contains_telegram_pattern"],
            f["contains_obfuscated_keyword"],
            f["password_is_doubled"],
            f["username_is_repetitive"],
            f["password_len"] > 60,
            f["composite_similarity"] > 0.45,
            f["is_substring"],
            f["username_len"] > 20 and f["username_transition_density"] > 0.3,
            f["contains_high_priority_keyword"],
            f["contains_t_g_pattern"],
        ]
        return any(spam_conditions)


seen_passwords = set()


def checker_combo(line):
    try:
        email, password = line.strip().split(":", 1)

        if password in seen_passwords:
            return False

        seen_passwords.add(password)

        if not email_domain_allowed(email):
            return False
        checker = SpamChecker(email, password)
        return not checker.is_spam()
    except Exception:
        return False
