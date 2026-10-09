"""Tree-age rules: load, validate and evaluate ``config/tree-age/rules.yaml``.

The file lists real programmes and laws that treat trees differently by age or size (carbon
programmes, payments, tree-protection laws, compensatory planting, methodology notes). This
module only *reads and matches* them; every rule and every number stays in the YAML with its
sources and ``verification_status`` (CLAUDE.md principles 2, 3, 10 and 13). Results are
screening information — never an eligibility determination, never a carbon credit.

Matching, for a user in ``country`` (ISO 3166-1), ``region`` (IN / US / EU), optionally
``subdivision`` (ISO 3166-2) with trees of a given ``setting`` and ``age_years``
(``docs/research/tree-age-carbon-rules.md`` §"How the app uses this"):

1. **Geography, hard filter.** Rules with scope ``GLOBAL``, the user's region and — when the
   rule names a country (the Berlin example is scope ``EU``, country ``DE``) — the user's
   country are returned; rules of other regions are not.
2. **Returned with ``applies`` true or false** (never silently dropped, so a user can see what
   *would* apply elsewhere): a rule with a different ``subdivision``; a municipal example
   (``locality``) when the user's place is not that locality; an age outside
   ``[min_age_years, max_age_years]`` (``null`` = no bound); a rule written for another
   ``setting`` (``urban`` / ``forest`` / ``non-forest``; a farm tree is non-forest).
   ``why`` says in plain words which condition decided.
3. **``outcome_for_you``.** With ``age_years ≥ 1`` the rule's ``outcome_for_existing_trees``.
   With ``age_years = 0`` (trees being *planned*): rules written for new planting or for any
   trees → ``conditional``; rules that regulate existing trees → ``not-applicable``.
4. **Order.** Applicable rules first, then category (carbon-credit eligibility, incentive
   payment, tree protection, compensatory planting, methodology note), then rule id.

:func:`credit_outlook` condenses the applicable carbon-credit rules into one statement: it
says ``not-eligible`` unless a rule that is in force names a route for existing trees, and it
never says ``eligible`` — only a programme can decide that.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from policy_engine.loader import find_config_dir

SCOPES = ("GLOBAL", "IN", "US", "EU")
CATEGORIES = (
    "carbon-credit-eligibility",
    "incentive-payment",
    "tree-protection",
    "compensatory-planting",
    "methodology-note",
)
OUTCOMES = ("not-eligible", "eligible", "conditional", "protected", "payment", "not-applicable")
RULE_STATUSES = ("in-force", "proposed", "superseded", "unknown")
TREE_STATUSES = ("any", "new-planting", "existing")
RULE_SETTINGS = ("any", "non-forest", "forest", "urban")
#: what the user can say about where the trees stand (a farm tree is "non-forest")
REQUEST_SETTINGS = ("farm", "urban", "forest", "any")
VERIFICATION_STATUSES = ("verified", "pending")
CREDIT_OUTLOOKS = ("not-eligible", "conditional", "eligible")

RULES_FILE = Path("tree-age") / "rules.yaml"
SUBDIVISIONS_FILE = Path("tree-age") / "subdivisions.yaml"

_REQUIRED_RULE_FIELDS = (
    "id",
    "scope",
    "country",
    "subdivision",
    "locality",
    "name",
    "authority",
    "category",
    "applies_to",
    "outcome_for_existing_trees",
    "summary",
    "details",
    "amount",
    "status",
    "is_example",
    "sources",
    "verification_status",
)
_OPTIONAL_RULE_FIELDS = ("notes",)
_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_COUNTRY = re.compile(r"^[A-Z]{2}$")
_SUBDIVISION = re.compile(r"^[A-Z]{2}-[A-Z0-9]{1,3}$")
_FULL_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MONTH_OR_DATE = re.compile(r"^\d{4}-\d{2}(?:-\d{2})?$")
_STATUS_FLAG = {
    "proposed": "proposed, not yet in force",
    "superseded": "superseded",
    "unknown": "status unknown",
}


class TreeAgeRulesError(ValueError):
    """The rules file does not match the schema (the message lists every problem)."""


# --------------------------------------------------------------------------------- loading
def _plain(value: Any) -> Any:
    """Make YAML output JSON-ready: dates (``updated: 2026-10-05``) become ISO strings."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def _read(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise TreeAgeRulesError(f"{path} must contain a mapping")
    plain = _plain(data)
    assert isinstance(plain, dict)
    return plain


@lru_cache(maxsize=4)
def _load_cached(config_dir: str) -> tuple[dict[str, Any], dict[str, Any]]:
    base = Path(config_dir)
    for relative in (RULES_FILE, SUBDIVISIONS_FILE):
        if not (base / relative).is_file():
            raise FileNotFoundError(f"missing {relative} under {base}")
    rules = _read(base / RULES_FILE)
    subdivisions = _read(base / SUBDIVISIONS_FILE)
    validate_rules(rules, subdivisions)
    return rules, subdivisions


def load_rules(config_dir: Path | None = None) -> dict[str, Any]:
    """Load and validate ``config/tree-age/rules.yaml`` (JSON-ready; a private copy)."""
    base = (config_dir or find_config_dir()).resolve()
    return copy.deepcopy(_load_cached(str(base))[0])


def load_subdivisions(config_dir: Path | None = None) -> dict[str, Any]:
    """Load ``config/tree-age/subdivisions.yaml`` (ISO 3166-2 labels; a private copy)."""
    base = (config_dir or find_config_dir()).resolve()
    return copy.deepcopy(_load_cached(str(base))[1])


# ------------------------------------------------------------------------------- validation
def validate_rules(doc: Mapping[str, Any], subdivisions: Mapping[str, Any] | None = None) -> None:
    """Raise :class:`TreeAgeRulesError` listing every schema problem in ``doc``."""
    problems = rule_problems(doc, subdivisions)
    if problems:
        raise TreeAgeRulesError(
            "config/tree-age/rules.yaml is invalid:\n" + "\n".join(f" - {p}" for p in problems)
        )


def rule_problems(
    doc: Mapping[str, Any], subdivisions: Mapping[str, Any] | None = None
) -> list[str]:
    """Schema problems in a rules document, as plain sentences (empty list = valid)."""
    if not isinstance(doc, Mapping):
        return ["the rules document must be a mapping"]
    problems: list[str] = []
    for key in ("version", "updated", "disclaimer", "age_classes", "rules"):
        if key not in doc:
            problems.append(f"missing top-level field {key!r}")
    for key in ("version", "disclaimer"):
        if key in doc and not _text(doc[key]):
            problems.append(f"top-level field {key!r} must be a non-empty string")
    if "updated" in doc and not (
        isinstance(doc["updated"], str) and _FULL_DATE.match(doc["updated"])
    ):
        problems.append("top-level field 'updated' must be a date like 2026-10-05")
    problems.extend(_age_class_problems(doc.get("age_classes")))

    rules = doc.get("rules")
    if not isinstance(rules, list) or not rules:
        problems.append("'rules' must be a non-empty list")
        return problems
    known = _subdivision_index(subdivisions) if subdivisions is not None else None
    seen: set[str] = set()
    for position, rule in enumerate(rules, start=1):
        if not isinstance(rule, Mapping):
            problems.append(f"rule #{position} must be a mapping")
            continue
        rule_id = str(rule.get("id", f"#{position}"))
        if rule_id in seen:
            problems.append(f"rule id {rule_id!r} is used more than once")
        seen.add(rule_id)
        problems.extend(f"rule {rule_id!r}: {p}" for p in _rule_field_problems(rule, known))
    return problems


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _one_of(value: Any, allowed: tuple[str, ...]) -> bool:
    return isinstance(value, str) and value in allowed


def _age_class_problems(classes: Any) -> list[str]:
    if not isinstance(classes, list) or not classes:
        return ["'age_classes' must be a non-empty list"]
    problems: list[str] = []
    ids: set[str] = set()
    previous_max: int | None = None
    for position, item in enumerate(classes, start=1):
        label = f"age class #{position}"
        if not isinstance(item, Mapping):
            problems.append(f"{label} must be a mapping")
            continue
        class_id, low, high = item.get("id"), item.get("min_age"), item.get("max_age")
        if not (isinstance(class_id, str) and _ID.match(class_id)):
            problems.append(f"{label}: 'id' must be a lowercase slug")
        elif class_id in ids:
            problems.append(f"{label}: id {class_id!r} is used more than once")
        else:
            ids.add(class_id)
        if not _text(item.get("label")):
            problems.append(f"{label}: 'label' must be a non-empty string")
        if not _is_age(low):
            problems.append(f"{label}: 'min_age' must be a whole number of years, 0 or more")
            continue
        if high is not None and (not _is_age(high) or high < low):
            problems.append(f"{label}: 'max_age' must be null or a whole number ≥ 'min_age'")
            continue
        expected = 0 if position == 1 else (None if previous_max is None else previous_max + 1)
        if expected is not None and low != expected:
            problems.append(
                f"{label}: 'min_age' is {low} but the classes must be contiguous (expected "
                f"{expected})"
            )
        if high is None and position != len(classes):
            problems.append(f"{label}: only the last age class may have 'max_age: null'")
        if high is not None and position == len(classes):
            problems.append(f"{label}: the last age class must be open-ended ('max_age: null')")
        previous_max = high if high is not None else previous_max
    return problems


def _is_age(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _rule_field_problems(
    rule: Mapping[str, Any], known_subdivisions: Mapping[str, str] | None
) -> list[str]:
    problems: list[str] = []
    missing = [f for f in _REQUIRED_RULE_FIELDS if f not in rule]
    if missing:
        problems.append(f"missing field(s): {', '.join(missing)}")
    unknown = sorted(set(rule) - set(_REQUIRED_RULE_FIELDS) - set(_OPTIONAL_RULE_FIELDS))
    if unknown:
        problems.append(f"unknown field(s): {', '.join(unknown)}")

    def check(name: str, ok: bool, message: str) -> None:
        if name in rule and not ok:
            problems.append(f"{name!r} {message}")

    check("id", isinstance(rule.get("id"), str) and bool(_ID.match(rule["id"])), "must be a slug")
    for name in ("name", "authority", "summary", "details"):
        check(name, _text(rule.get(name)), "must be a non-empty string")
    if "notes" in rule:
        check("notes", rule["notes"] is None or _text(rule["notes"]), "must be text or null")
    check("scope", _one_of(rule.get("scope"), SCOPES), f"must be one of {', '.join(SCOPES)}")
    check(
        "category",
        _one_of(rule.get("category"), CATEGORIES),
        f"must be one of {', '.join(CATEGORIES)}",
    )
    check(
        "outcome_for_existing_trees",
        _one_of(rule.get("outcome_for_existing_trees"), OUTCOMES),
        f"must be one of {', '.join(OUTCOMES)}",
    )
    check(
        "status",
        _one_of(rule.get("status"), RULE_STATUSES),
        f"must be one of {', '.join(RULE_STATUSES)}",
    )
    check(
        "verification_status",
        _one_of(rule.get("verification_status"), VERIFICATION_STATUSES),
        f"must be one of {', '.join(VERIFICATION_STATUSES)}",
    )
    check("is_example", isinstance(rule.get("is_example"), bool), "must be true or false")

    country, subdivision, locality = (
        rule.get("country"),
        rule.get("subdivision"),
        rule.get("locality"),
    )
    check(
        "country",
        country is None or (isinstance(country, str) and bool(_COUNTRY.match(country))),
        "must be null or an upper-case ISO 3166-1 alpha-2 code",
    )
    check(
        "subdivision",
        subdivision is None
        or (isinstance(subdivision, str) and bool(_SUBDIVISION.match(subdivision))),
        "must be null or an ISO 3166-2 code such as IN-KA",
    )
    check("locality", locality is None or _text(locality), "must be null or a place name")
    scope = rule.get("scope")
    if scope == "GLOBAL" and (country or subdivision or locality):
        problems.append("a GLOBAL rule must not name a country, subdivision or locality")
    if scope in ("IN", "US") and country not in (None, scope):
        problems.append(f"a {scope} rule must have country {scope} (or null), not {country!r}")
    if isinstance(subdivision, str) and isinstance(country, str):
        if not subdivision.startswith(country + "-"):
            problems.append(f"subdivision {subdivision!r} is not inside country {country!r}")
    if isinstance(subdivision, str) and scope in ("IN", "US", "EU"):
        prefix = subdivision.split("-")[0]
        if scope != "EU" and prefix != scope:
            problems.append(f"subdivision {subdivision!r} is not inside scope {scope!r}")
    if locality and not subdivision:
        problems.append("a rule with a 'locality' must also name its 'subdivision'")
    if known_subdivisions is not None and isinstance(subdivision, str):
        if subdivision not in known_subdivisions:
            problems.append(
                f"subdivision {subdivision!r} is not listed in config/tree-age/subdivisions.yaml"
            )

    problems.extend(_applies_to_problems(rule.get("applies_to"), "applies_to" in rule))
    problems.extend(_amount_problems(rule.get("amount"), "amount" in rule))
    problems.extend(_source_problems(rule.get("sources"), "sources" in rule))
    return problems


def _applies_to_problems(value: Any, present: bool) -> list[str]:
    if not present:
        return []
    if not isinstance(value, Mapping):
        return ["'applies_to' must be a mapping"]
    problems: list[str] = []
    expected = {"min_age_years", "max_age_years", "trees", "setting"}
    if set(value) != expected:
        problems.append(f"'applies_to' must have exactly the keys {', '.join(sorted(expected))}")
    low, high = value.get("min_age_years"), value.get("max_age_years")
    for name, bound in (("min_age_years", low), ("max_age_years", high)):
        if bound is not None and not _is_age(bound):
            problems.append(f"'applies_to.{name}' must be null or a whole number of years")
    if isinstance(low, int) and isinstance(high, int) and low > high:
        problems.append("'applies_to.min_age_years' is larger than 'applies_to.max_age_years'")
    if not _one_of(value.get("trees"), TREE_STATUSES):
        problems.append(f"'applies_to.trees' must be one of {', '.join(TREE_STATUSES)}")
    if not _one_of(value.get("setting"), RULE_SETTINGS):
        problems.append(f"'applies_to.setting' must be one of {', '.join(RULE_SETTINGS)}")
    return problems


def _amount_problems(value: Any, present: bool) -> list[str]:
    if not present or value is None:
        return []
    if not isinstance(value, Mapping):
        return ["'amount' must be null or a mapping"]
    problems: list[str] = []
    number = value.get("value")
    if isinstance(number, bool) or not isinstance(number, (int, float)) or number < 0:
        problems.append("'amount.value' must be a number, 0 or more")
    for name in ("currency", "unit"):
        if not _text(value.get(name)):
            problems.append(f"'amount.{name}' must be a non-empty string")
    as_of = value.get("as_of")
    if not (isinstance(as_of, str) and _MONTH_OR_DATE.match(as_of)):
        problems.append("'amount.as_of' must be a date such as 2026-07 or 2026-07-15")
    return problems


def _source_problems(value: Any, present: bool) -> list[str]:
    if not present:
        return []
    if not isinstance(value, list) or not value:
        return ["'sources' must list at least one source"]
    problems: list[str] = []
    for position, source in enumerate(value, start=1):
        label = f"source #{position}"
        if not isinstance(source, Mapping):
            problems.append(f"{label} must be a mapping")
            continue
        for name in ("title", "publisher"):
            if not _text(source.get(name)):
                problems.append(f"{label}: {name!r} must be a non-empty string")
        url = source.get("url")
        if not (isinstance(url, str) and url.startswith("https://") and len(url) > len("https://")):
            problems.append(f"{label}: 'url' must be an https:// link")
        accessed = source.get("accessed")
        if not (isinstance(accessed, str) and _FULL_DATE.match(accessed)):
            problems.append(f"{label}: 'accessed' must be a date such as 2026-10-05")
    return problems


def _subdivision_index(subdivisions: Mapping[str, Any] | None) -> dict[str, str]:
    """``{"IN-HR": "IN", …}`` — every known subdivision code with its country."""
    index: dict[str, str] = {}
    countries = (subdivisions or {}).get("countries") or {}
    for country, block in countries.items():
        for item in (block or {}).get("subdivisions", []):
            index[str(item["code"])] = str(country)
    return index


def pending_rules(doc: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Rules not confirmed from a primary source (production releases must have none)."""
    return [r for r in doc.get("rules", []) if r.get("verification_status") == "pending"]


# ---------------------------------------------------------------------------------- lookups
def age_class_for(age_years: int, rules_doc: Mapping[str, Any] | None = None) -> dict[str, str]:
    """``{"id": "old", "label": "Old (50–74 years)"}`` for ``age_years`` (project convention)."""
    doc = rules_doc if rules_doc is not None else load_rules()
    for item in doc["age_classes"]:
        high = item["max_age"]
        if item["min_age"] <= age_years and (high is None or age_years <= high):
            return {"id": str(item["id"]), "label": str(item["label"])}
    raise ValueError(f"no age class covers {age_years} years")


class _Names:
    """Place names from ``subdivisions.yaml`` for the plain-language sentences."""

    def __init__(self, subdivisions: Mapping[str, Any] | None) -> None:
        self._countries: dict[str, str] = {}
        self._subdivisions: dict[str, str] = {}
        for country, block in ((subdivisions or {}).get("countries") or {}).items():
            article = f"{block['article']} " if block.get("article") else ""
            self._countries[str(country)] = f"{article}{block.get('name', country)}"
            for item in block.get("subdivisions", []):
                self._subdivisions[str(item["code"])] = str(item["name"])

    def country(self, code: str) -> str:
        return self._countries.get(code, code)

    def subdivision(self, code: str) -> str:
        return self._subdivisions.get(code, code)

    def label(self, code: str) -> str:
        return f"{self.subdivision(code)} ({code})"


def select_rules(
    rules_doc: Mapping[str, Any],
    country: str | None = None,
    region: str | None = None,
    subdivision: str | None = None,
    *,
    allow_pending: bool = True,
) -> list[dict[str, Any]]:
    """Rules as written in the file, filtered by geography (copies).

    No ``country``/``region``: every rule. Otherwise ``GLOBAL`` rules, rules of ``region``
    (a rule that names a country must match ``country``), and — when ``subdivision`` is given —
    only rules that are not tied to a *different* subdivision. With ``allow_pending=False``
    (production) rules whose ``verification_status`` is ``pending`` are withheld, the way the
    carbon engine refuses pending parameters (CLAUDE.md principle 10);
    :func:`withheld_rule_ids` names them.
    """
    country = country.upper() if country else None
    region = region.upper() if region else None
    subdivision = subdivision.upper() if subdivision else None
    chosen: list[dict[str, Any]] = []
    for rule in rules_doc.get("rules", []):
        if country or region:
            if rule["scope"] not in ("GLOBAL", region):
                continue
            if rule.get("country") not in (None, country):
                continue
        if subdivision and rule.get("subdivision") not in (None, subdivision):
            continue
        if not allow_pending and rule["verification_status"] == "pending":
            continue
        chosen.append(copy.deepcopy(rule))
    return chosen


def withheld_rule_ids(
    rules_doc: Mapping[str, Any],
    country: str | None = None,
    region: str | None = None,
    subdivision: str | None = None,
) -> list[str]:
    """Ids of the pending rules that ``allow_pending=False`` hides for this place."""
    everything = select_rules(rules_doc, country, region, subdivision)
    return [str(r["id"]) for r in everything if r["verification_status"] == "pending"]


# --------------------------------------------------------------------------------- evaluate
def evaluate(
    rules_doc: Mapping[str, Any],
    country: str | None,
    region: str,
    subdivision: str | None,
    setting: str,
    age_years: int,
    *,
    locality: str | None = None,
    subdivisions: Mapping[str, Any] | None = None,
    allow_pending: bool = True,
) -> list[dict[str, Any]]:
    """Rules for this place, each with ``applies``, ``why`` and ``outcome_for_you`` added.

    ``setting`` ∈ ``farm | urban | forest | any`` (``any`` never excludes a rule). ``locality``
    (a city or town name) is optional: municipal example rules apply only when it matches, or
    when the subdivision *is* that city (Berlin, ``DE-BE``). ``allow_pending=False`` withholds
    rules that are not yet confirmed from a primary source (see :func:`select_rules`).
    """
    if setting not in REQUEST_SETTINGS:
        raise ValueError(f"setting must be one of {', '.join(REQUEST_SETTINGS)}, not {setting!r}")
    if not _is_age(age_years):
        raise ValueError("age_years must be a whole number of years, 0 or more")
    if subdivisions is None:
        subdivisions = _default_subdivisions()
    names = _Names(subdivisions)
    sub = subdivision.upper() if subdivision else None
    place = locality.strip().casefold() if locality and locality.strip() else None

    results: list[dict[str, Any]] = []
    chosen = select_rules(rules_doc, country=country, region=region, allow_pending=allow_pending)
    for rule in chosen:
        reason = _mismatch(rule, sub, place, setting, age_years, names)
        rule["applies"] = reason is None
        rule["why"] = reason or _applies_because(rule, names)
        rule["outcome_for_you"] = _outcome_for(rule, age_years)
        results.append(rule)
    results.sort(key=_sort_key)
    return results


def _default_subdivisions() -> dict[str, Any] | None:
    try:
        return load_subdivisions()
    except FileNotFoundError:
        return None


def _sort_key(rule: Mapping[str, Any]) -> tuple[bool, int, str]:
    return (not rule["applies"], CATEGORIES.index(rule["category"]), str(rule["id"]))


def _outcome_for(rule: Mapping[str, Any], age_years: int) -> str:
    if age_years >= 1:
        return str(rule["outcome_for_existing_trees"])
    # trees being planned: rules about trees that already stand do not apply to them yet
    return "not-applicable" if rule["applies_to"]["trees"] == "existing" else "conditional"


def _mismatch(
    rule: Mapping[str, Any],
    subdivision: str | None,
    locality: str | None,
    setting: str,
    age_years: int,
    names: _Names,
) -> str | None:
    """The plain reason a rule does not apply, or ``None`` when it does."""
    rule_sub = rule.get("subdivision")
    if rule_sub and rule_sub != subdivision:
        return f"Only in {names.label(rule_sub)}"
    rule_locality = rule.get("locality")
    if rule_locality and not _locality_matches(rule_locality, rule_sub, locality, names):
        return f"Municipal example for {rule_locality} ({rule_sub}); check your own city's rules"
    applies_to = rule["applies_to"]
    low, high = applies_to["min_age_years"], applies_to["max_age_years"]
    if (low is not None and age_years < low) or (high is not None and age_years > high):
        return f"Needs trees {_age_phrase(low, high)}"
    rule_setting = applies_to["setting"]
    if rule_setting != "any" and setting != "any" and not _setting_matches(rule_setting, setting):
        return f"Only for {_setting_phrase(rule_setting)}"
    return None


def _locality_matches(
    rule_locality: str, rule_sub: str | None, locality: str | None, names: _Names
) -> bool:
    wanted = rule_locality.casefold()
    if locality is not None and locality == wanted:
        return True
    # a city-state: the subdivision is the city (DE-BE is Berlin)
    return rule_sub is not None and names.subdivision(rule_sub).casefold() == wanted


def _setting_matches(rule_setting: str, setting: str) -> bool:
    if rule_setting == "non-forest":
        return setting in ("farm", "urban")
    return rule_setting == setting


def _setting_phrase(rule_setting: str) -> str:
    return {
        "urban": "urban trees",
        "forest": "trees in forests",
        "non-forest": "trees outside forests",
    }.get(rule_setting, "trees")


def _age_phrase(low: int | None, high: int | None) -> str:
    if low is not None and high is not None:
        return f"aged {low} to {high} years"
    if low is not None:
        return f"aged {low} years or more"
    if high is not None:
        return f"aged {high} years or less"
    return "of any age"


def _applies_because(rule: Mapping[str, Any], names: _Names) -> str:
    where = _where(rule, names)
    applies_to = rule["applies_to"]
    low, high = applies_to["min_age_years"], applies_to["max_age_years"]
    setting = applies_to["setting"]
    if setting == "any" and low is None and high is None:
        sentence = f"Applies {where} at any age"
    else:
        trees = _setting_phrase(setting)
        age = "at any age" if low is None and high is None else _age_phrase(low, high)
        sentence = f"Applies {where} to {trees} {age}"
    if rule.get("is_example"):
        sentence += " — a municipal example; check your own city's rules"
    flags = []
    if rule["status"] != "in-force":
        flags.append(_STATUS_FLAG.get(rule["status"], rule["status"]))
    if rule["verification_status"] == "pending":
        flags.append("not yet confirmed from a primary source")
    if flags:
        sentence += f" ({'; '.join(flags)})"
    return sentence


def _where(rule: Mapping[str, Any], names: _Names) -> str:
    if rule.get("subdivision"):
        return f"in {names.label(rule['subdivision'])}"
    if rule.get("country"):
        return f"in {names.country(rule['country'])}"
    if rule["scope"] == "GLOBAL":
        return "worldwide"
    if rule["scope"] == "EU":
        return "in the EU"
    return f"in {names.country(rule['scope'])}"


# ------------------------------------------------------------------------------ credit outlook
def credit_outlook(rules: Iterable[Mapping[str, Any]], age_years: int) -> dict[str, Any]:
    """What the *applicable* carbon-credit rules say about these trees, in one sentence.

    ``rules`` are :func:`evaluate` results. Age 0 (trees being planned) → ``conditional``: new
    planting can be credited if a project meets a programme's rules. Otherwise
    ``not-eligible`` unless an applicable rule that is in force gives existing trees a route
    (outcome ``conditional`` or ``eligible``), which gives ``conditional``. ``eligible`` is
    never returned: only the programme's own verification can decide that.
    """
    eligibility = [
        r
        for r in rules
        if r["applies"]
        and r["category"] == "carbon-credit-eligibility"
        and r["status"] == "in-force"
    ]
    ids = [str(r["id"]) for r in eligibility]
    if age_years == 0:
        return {
            "existing_trees": "conditional",
            "summary": (
                "Newly planted trees can earn removal credits only through a project that meets a "
                "programme's rules; nothing is stored or creditable until they are planted and "
                "verified, and an estimate is never a credit."
            ),
            "based_on_rule_ids": ids,
        }
    routes = [r for r in eligibility if r["outcome_for_you"] in ("conditional", "eligible")]
    if not routes:
        return {
            "existing_trees": "not-eligible",
            "summary": (
                "Trees that already stand usually do not earn removal credits under the rules "
                "that apply here, because credits reward carbon added by new planting, not "
                "carbon already stored."
            ),
            "based_on_rule_ids": ids,
        }
    if len(routes) == 1:
        who = _short_name(routes[0])
    else:
        who = f"{len(routes)} of the applicable rules"
    sentence = (
        f"Existing trees can qualify only under specific conditions in {who}; confirm with the "
        "programme, because an estimate is never a credit"
    )
    if all(r["verification_status"] == "pending" for r in routes):
        sentence += " (this rests on a rule not yet confirmed from a primary source)"
    return {
        "existing_trees": "conditional",
        "summary": sentence + ".",
        "based_on_rule_ids": ids,
    }


def _short_name(rule: Mapping[str, Any]) -> str:
    return str(rule["name"]).split(": ")[0].strip()
