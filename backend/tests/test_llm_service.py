import json
import unittest
from types import SimpleNamespace

from backend.app.llm_service import (
    OpenAILLMService,
    RecommendationNarrative,
    sanitize_movie_intent,
)
from backend.app.schemas import MovieIntent, MovieSummary, Recommendation


class FakeResponses:
    def __init__(self) -> None:
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs["text_format"] is MovieIntent:
            parsed = MovieIntent(
                actors=["Christian Bale"],
                preferred_genres=["action"],
                min_rating=7,
                max_runtime=160,
            )
        else:
            parsed = RecommendationNarrative(message="Pilihan yang sesuai.", explanations=[])
        return SimpleNamespace(output_parsed=parsed)

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text="Jawaban tentang film.")


class LLMServiceTests(unittest.TestCase):
    def setUp(self):
        self.responses = FakeResponses()
        self.service = OpenAILLMService.__new__(OpenAILLMService)
        self.service.client = SimpleNamespace(responses=self.responses)
        self.service.settings = SimpleNamespace(openai_model="test-model")

    def test_parse_complete_metadata_intent(self):
        intent = self.service.parse_intent(
            "Film action Christian Bale rating minimal 7 maksimal 160 menit"
        )
        self.assertEqual(intent.actors, ["Christian Bale"])
        self.assertEqual(intent.preferred_genres, ["action"])
        self.assertEqual(intent.min_rating, 7)
        self.assertEqual(intent.max_runtime, 160)

    def test_narrative_receives_discovery_metadata(self):
        movie = Recommendation(
            id=1,
            title="The Dark Knight",
            release_year=2008,
            genres="action crime drama",
            original_language="en",
            runtime=152,
            director="christopher nolan",
            cast="christian bale, heath ledger",
            keywords="joker, gotham city",
            vote_average=8.5,
            similarity_score=0,
            hybrid_score=0.87,
            reason="Sesuai filter.",
            score_type="discovery",
        )
        self.service.create_narrative("Film Christian Bale", None, [movie])
        payload = json.loads(self.responses.calls[-1]["input"])
        candidate = payload["candidates"][0]
        self.assertIsNone(payload["source_movie"])
        self.assertEqual(candidate["director"], "christopher nolan")
        self.assertIn("christian bale", candidate["cast"])
        self.assertEqual(candidate["score_type"], "discovery")

    def test_similarity_phrase_is_not_treated_as_keyword(self):
        intent = MovieIntent(
            reference_title="Interstellar",
            keywords=["similar to Interstellar", "space exploration"],
        )
        sanitized = sanitize_movie_intent(intent)
        self.assertEqual(sanitized.reference_title, "Interstellar")
        self.assertEqual(sanitized.keywords, ["space exploration"])

    def test_movie_follow_up_sends_history_without_provider_storage(self):
        movie = MovieSummary(id=157336, title="Interstellar", director="Christopher Nolan")
        history = [
            SimpleNamespace(role="user", content="Ceritanya tentang apa?"),
            SimpleNamespace(role="assistant", content="Tentang perjalanan antariksa."),
        ]
        answer = self.service.answer_movie_question(movie, "Siapa sutradaranya?", history)
        call = self.responses.calls[-1]
        self.assertEqual(answer, "Jawaban tentang film.")
        self.assertFalse(call["store"])
        self.assertEqual(call["input"][-1]["content"], "Siapa sutradaranya?")
        self.assertIn("MOVIE_CONTEXT_JSON", call["instructions"])


if __name__ == "__main__":
    unittest.main()
