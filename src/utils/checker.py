import re
from collections import Counter
from difflib import SequenceMatcher
from functools import cached_property
from typing import List, Set, Optional

ALLOWED_DOMAIN_PREFIXES = ("hotmail.", "outlook.", "live.", "msn.")
FORBIDDEN_USERNAME_CHARS = "'\"\\/<>|` \t\n\r@:,?&%$;"
FORBIDDEN_PASSWORD_CHARS = " \t\n\r\v\f"


def email_domain_allowed(email: str) -> bool:
    try:
        domain = email.lower().split("@", 1)[1]
        return domain.startswith(ALLOWED_DOMAIN_PREFIXES)
    except (IndexError, AttributeError):
        return False


class SpamChecker:
    HIGH_PRIORITY_KEYWORDS = {"whale", "adm", "bdelahw"}
    LOW_PRIORITY_KEYWORDS = {"whal", "whan", "duolc", "cloud", "snap"}
    OBFUSCATED_KEYWORDS = {"snap", "telegram", "articxu", "carpenater"}

    def __init__(
        self, email: str, password: str, spammy_substrings: Optional[Set[str]] = None
    ):
        self.email = email.lower()
        self.password = password
        self.spammy_substrings = spammy_substrings or set()
        try:
            self.username, self.domain = self.email.split("@", 1)
        except ValueError:
            self.username, self.domain = self.email, ""

    @cached_property
    def password_lower(self) -> str:
        return self.password.lower()

    @cached_property
    def username_core(self) -> str:
        return re.sub(r"[^a-z]", "", self.username)

    @cached_property
    def password_core(self) -> str:
        return re.sub(r"[^a-z]", "", self.password_lower)

    def _contains_keywords(self, keyword_set: Set[str]) -> bool:
        return any(
            key in self.password_core or key in self.username_core
            for key in keyword_set
        )

    @cached_property
    def contains_high_priority_keyword(self) -> bool:
        return self._contains_keywords(self.HIGH_PRIORITY_KEYWORDS)

    @cached_property
    def contains_low_priority_keyword(self) -> bool:
        return self._contains_keywords(self.LOW_PRIORITY_KEYWORDS)

    @cached_property
    def contains_telegram_reference(self) -> bool:
        pattern = r"telegram|t\.me|\.tg|\btg\b|t\.g"
        return bool(
            re.search(pattern, self.email) or re.search(pattern, self.password_lower)
        )

    @cached_property
    def username_has_forbidden_chars(self) -> bool:
        return any(char in FORBIDDEN_USERNAME_CHARS for char in self.username)

    @cached_property
    def password_has_forbidden_chars(self) -> bool:
        return any(char in FORBIDDEN_PASSWORD_CHARS for char in self.password)

    @cached_property
    def contains_spammy_substring(self) -> bool:
        text_to_check = self.email + self.password_lower
        return any(sub in text_to_check for sub in self.spammy_substrings)

    @cached_property
    def password_contains_url(self) -> bool:
        return bool(re.search(r"https?://|wa\.me", self.password_lower))

    @cached_property
    def is_password_doubled(self) -> bool:
        pw_len = len(self.password)
        if pw_len > 2 and pw_len % 2 == 0:
            mid = pw_len // 2
            return self.password[:mid] == self.password[mid:]
        return False

    @cached_property
    def is_substring(self) -> bool:
        u_core, p_core = self.username_core, self.password_core
        return (len(p_core) >= 4 and p_core in u_core) or (
            len(u_core) >= 4 and u_core in p_core
        )

    @cached_property
    def composite_similarity(self) -> float:
        u_core, p_core = self.username_core, self.password_core
        sim_ratio_core = SequenceMatcher(None, u_core, p_core).ratio()
        sim_ratio_reversed = SequenceMatcher(None, u_core, p_core[::-1]).ratio()
        return max(sim_ratio_core, sim_ratio_reversed)

    def is_spam(self) -> bool:
        if self.username_has_forbidden_chars or self.password_has_forbidden_chars:
            return True
        if self.contains_high_priority_keyword:
            return True

        spam_flags = [
            self.contains_low_priority_keyword,
            self.is_password_doubled,
            self.is_substring,
            self.composite_similarity > 0.80,
            self.contains_spammy_substring,
            self.contains_telegram_reference,
            self.password_contains_url,
        ]

        if sum(spam_flags) >= 2:
            return True

        return False


def filter_combos(file_content: str) -> List[str]:
    lines = [line.strip() for line in file_content.strip().split("\n") if ":" in line]

    substring_counts = Counter(
        part
        for line in lines
        for part in re.split(
            r"[@._\-|]", (line.split(":", 1)[0] + line.split(":", 1)[1]).lower()
        )
        if len(part) >= 5
    )
    spammy_substrings = {part for part, count in substring_counts.items() if count > 5}

    valid_lines = []
    for line in lines:
        try:
            email, password = line.split(":", 1)
            checker = SpamChecker(email, password, spammy_substrings)

            if not checker.is_spam():
                valid_lines.append(line)

        except ValueError:
            continue

    return valid_lines
