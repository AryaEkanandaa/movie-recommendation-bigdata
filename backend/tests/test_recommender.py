import unittest

from backend.app.recommender import (
    apply_intent_filters,
    extract_title_candidate,
    intent_has_filters,
    normalize_title,
)
from backend.app.schemas import MovieIntent, Recommendation


class RecommenderTextTests(unittest.TestCase):
    def test_extract_title_after_seperti(self):
        self.assertEqual(
            extract_title_candidate("Saya ingin nonton film seperti Batman"), "Batman"
        )

    def test_extract_title_after_mirip(self):
        self.assertEqual(extract_title_candidate("Rekomendasi mirip Interstellar"), "Interstellar")

    def test_normalize_title(self):
        self.assertEqual(normalize_title("  The   Dark Knight "), "the dark knight")

    def test_apply_llm_intent_filters(self):
        movies = [
            Recommendation(
                id=1,
                title="Space Film",
                release_year=2020,
                genres="science fiction drama",
                original_language="en",
                runtime=120,
                director="Jane Director",
                cast="Actor One, Actor Two",
                keywords="space, time travel",
                vote_average=8.0,
                overview="A journey through space and time.",
                similarity_score=0.9,
                hybrid_score=0.8,
                reason="test",
            ),
            Recommendation(
                id=2,
                title="Comedy Film",
                release_year=2010,
                genres="comedy",
                original_language="fr",
                runtime=150,
                director="Other Director",
                cast="Another Actor",
                keywords="friendship",
                vote_average=6.0,
                similarity_score=0.8,
                hybrid_score=0.7,
                reason="test",
            ),
        ]
        intent = MovieIntent(
            reference_title="Interstellar",
            preferred_genres=["science fiction"],
            actors=["Actor One"],
            directors=["Jane Director"],
            keywords=["time travel"],
            original_languages=["English"],
            min_rating=7.0,
            max_rating=9.0,
            release_year_from=2015,
            release_year_to=2025,
            min_runtime=100,
            max_runtime=130,
        )
        result = apply_intent_filters(movies, intent)
        self.assertEqual([movie.id for movie in result], [1])

    def test_intent_can_search_without_reference_movie(self):
        intent = MovieIntent(actors=["Christian Bale"], max_runtime=150)
        self.assertTrue(intent_has_filters(intent))

    def test_empty_intent_has_no_filters(self):
        self.assertFalse(intent_has_filters(MovieIntent()))


if __name__ == "__main__":
    unittest.main()
