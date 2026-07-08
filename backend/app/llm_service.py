from __future__ import annotations

import json

from openai import OpenAI
from pydantic import BaseModel, Field

from .config import Settings
from .schemas import ConversationMessage, MovieIntent, MovieSummary, Recommendation


class MovieExplanation(BaseModel):
    movie_id: int
    reason: str


class RecommendationNarrative(BaseModel):
    message: str
    explanations: list[MovieExplanation]


def sanitize_movie_intent(intent: MovieIntent) -> MovieIntent:
    """Remove similarity phrasing that is not an actual thematic keyword."""
    if not intent.reference_title:
        return intent

    reference_title = intent.reference_title.strip().lower()
    similarity_phrases = ("similar to", "similar with", "mirip dengan", "mirip seperti")
    intent.keywords = [
        keyword
        for keyword in intent.keywords
        if reference_title not in keyword.strip().lower()
        and not any(phrase in keyword.strip().lower() for phrase in similarity_phrases)
    ]
    return intent


class OpenAILLMService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.enabled = settings.llm_enabled
        self.client = (
            OpenAI(
                api_key=settings.openai_api_key,
                timeout=settings.openai_timeout_seconds,
                max_retries=1,
            )
            if self.enabled
            else None
        )

    def parse_intent(self, message: str) -> MovieIntent | None:
        if not self.client:
            return None

        response = self.client.responses.parse(
            model=self.settings.openai_model,
            instructions=(
                "Extract structured movie search intent from Indonesian or English text. "
                "Never invent a movie title, actor, director, or constraint. reference_title must "
                "only contain a movie title explicitly present in the message. Return genres and "
                "keywords in English, original_languages as ISO 639-1 codes, runtime in minutes, "
                "and people names as written. Do not turn similarity relations such as 'similar to "
                "Interstellar' or 'mirip dengan Interstellar' into keywords. When reference_title is "
                "present, keywords may only contain additional thematic constraints explicitly stated "
                "by the user. A request may search by metadata without a reference "
                "movie. Set clarification_needed=true only when there is neither a reference title "
                "nor any usable genre, actor, director, keyword, language, rating, year, or runtime filter."
            ),
            input=message,
            text_format=MovieIntent,
        )
        return sanitize_movie_intent(response.output_parsed)

    def create_narrative(
        self,
        user_message: str,
        source: MovieSummary | None,
        recommendations: list[Recommendation],
    ) -> RecommendationNarrative | None:
        if not self.client:
            return None

        candidates = [
            {
                "id": movie.id,
                "title": movie.title,
                "year": movie.release_year,
                "genres": movie.genres,
                "language": movie.original_language,
                "runtime": movie.runtime,
                "director": movie.director,
                "cast": movie.cast,
                "keywords": movie.keywords,
                "rating": movie.vote_average,
                "overview": movie.overview,
                "similarity_score": movie.similarity_score,
                "ranking_score": movie.hybrid_score,
                "score_type": movie.score_type,
            }
            for movie in recommendations
        ]
        response = self.client.responses.parse(
            model=self.settings.openai_model,
            instructions=(
                "You explain movie recommendations in concise natural Indonesian. "
                "The source movie can be null for metadata discovery. Use only the supplied source and "
                "candidate movies. Never add, replace, or invent a movie. "
                "Write one short opening message and one specific one-sentence reason per candidate. "
                "Every explanation must use the exact candidate movie_id."
            ),
            input=json.dumps(
                {
                    "user_message": user_message,
                    "source_movie": source.model_dump() if source else None,
                    "candidates": candidates,
                },
                ensure_ascii=False,
            ),
            text_format=RecommendationNarrative,
        )
        return response.output_parsed

    def answer_movie_question(
        self,
        movie: MovieSummary,
        message: str,
        history: list[ConversationMessage],
    ) -> str | None:
        if not self.client:
            return None

        movie_context = {
            "id": movie.id,
            "title": movie.title,
            "year": movie.release_year,
            "genres": movie.genres,
            "language": movie.original_language,
            "runtime": movie.runtime,
            "director": movie.director,
            "cast": movie.cast,
            "keywords": movie.keywords,
            "rating": movie.vote_average,
            "overview": movie.overview,
        }
        conversation_input = [
            {"role": item.role, "content": item.content}
            for item in history[-12:]
        ]
        conversation_input.append({"role": "user", "content": message})

        response = self.client.responses.create(
            model=self.settings.openai_model,
            instructions=(
                "You answer follow-up questions in concise natural Indonesian about exactly one movie. "
                "Use the supplied movie metadata and conversation history as the source of truth. "
                "Do not switch the subject to another movie unless making a brief comparison requested "
                "by the user. If a requested fact is not available in the metadata, say that the data is "
                "not available instead of inventing it. Return plain text without Markdown symbols, "
                "headings, or bullet formatting. "
                f"MOVIE_CONTEXT_JSON={json.dumps(movie_context, ensure_ascii=False)}"
            ),
            input=conversation_input,
            store=False,
        )
        return response.output_text.strip() if response.output_text else None
