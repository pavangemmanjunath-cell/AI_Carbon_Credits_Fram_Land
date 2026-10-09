"""The deterministic intent router, in English and other languages."""

from __future__ import annotations

import pytest

from atlas_agents import default_router, parse_age_years, parse_tree_change

ROUTER = default_router()


@pytest.mark.parametrize(
    "question,intent,plan",
    [
        ("How much carbon if I add 200 trees?", "what_if", "quick-estimate"),
        ("My mango trees are 60 years old — do they count?", "tree_age", "tree-age-check"),
        ("Please make me a report", "report", "full-assessment"),
        ("How much money could I earn?", "value", "full-assessment"),
        ("Can I get carbon credits for my farm?", "programmes", "full-assessment"),
        ("What is my NDVI?", "vegetation", "full-assessment"),
        ("How big is my plot?", "land", "quick-estimate"),
        ("How much carbon do my trees store?", "carbon", "quick-estimate"),
    ],
)
def test_english_questions(question: str, intent: str, plan: str):
    route = ROUTER.route(question)
    assert (route.intent, route.plan, route.fallback) == (intent, plan, False)
    assert route.matched and route.languages == ("en",)


@pytest.mark.parametrize(
    "question,intent,language,change",
    [
        ("मेरे खेत में कितना कार्बन है?", "carbon", "hi", None),
        ("अगर मैं 200 और पेड़ लगाऊं तो कितना कार्बन होगा?", "what_if", "hi", 200),
        ("ನಾನು 200 ಮರಗಳನ್ನು ನೆಟ್ಟರೆ ಎಷ್ಟು ಇಂಗಾಲ?", "what_if", "kn", 200),
        ("Wie viel Kohlenstoff, wenn ich 200 Bäume pflanze?", "what_if", "de", 200),
        ("Wie viel Kohlenstoff binden meine Bäume?", "carbon", "de", None),
        ("Et si je plante 200 arbres ?", "what_if", "fr", 200),
        ("Combien de carbone stockent mes arbres ?", "carbon", "fr", None),
        ("¿Cuánto carbono si planto 50 árboles más?", "what_if", "es", 50),
    ],
)
def test_other_languages(question: str, intent: str, language: str, change: int | None):
    route = ROUTER.route(question)
    assert route.intent == intent and language in route.languages
    assert route.tree_change == change


def test_unknown_questions_fall_back_honestly():
    route = ROUTER.route("Hello there")
    assert route.fallback and route.intent == "general" and route.plan == "quick-estimate"
    assert route.matched == ()


def test_whole_words_only_for_latin_keywords():
    # "ans" (French: years) must not fire inside "plans"; "plan" is not a keyword at all.
    assert ROUTER.route("Show me the plans").intent == "general"


def test_what_if_needs_a_number():
    assert ROUTER.route("What if I plant more trees?").intent == "general"
    assert ROUTER.route("What if I plant 30 more trees?").intent == "what_if"


@pytest.mark.parametrize(
    "question,change",
    [
        ("add 200 trees", 200),
        ("plant 50 more", 50),
        ("What if I add 1,000 more trees?", 1000),
        ("remove 30 trees", -30),
        ("If I cut 12 trees", -12),
        ("Trees planted in 2023 — add 50 trees", 50),
        ("२०० पेड़ और", 200),
        ("How much carbon?", None),
    ],
)
def test_parse_tree_change(question: str, change: int | None):
    assert parse_tree_change(question) == change


@pytest.mark.parametrize(
    "question,age",
    [
        ("They are 60 years old", 60),
        ("a 60-year-old mango", 60),
        ("मेरे पेड़ 60 साल पुराने हैं", 60),
        ("Meine Bäume sind 60 Jahre alt", 60),
        ("Mes arbres ont 60 ans", 60),
        ("Mis árboles tienen 60 años", 60),
        ("How old are they?", None),
    ],
)
def test_parse_age_years(question: str, age: int | None):
    assert parse_age_years(question) == age


def test_route_to_dict_is_plain_data():
    data = ROUTER.route("add 20 trees").to_dict()
    assert data["intent"] == "what_if" and data["tree_change"] == 20 and data["focus"] == ["carbon"]
