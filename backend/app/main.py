from __future__ import annotations

from contextlib import asynccontextmanager

import requests
from openai import OpenAIError
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings
from .llm_service import OpenAILLMService
from .qdrant_gateway import QdrantGateway
from .recommender import (
    AmbiguousTitleError,
    MovieNotFoundError,
    MovieRecommender,
    apply_intent_filters,
    extract_title_candidate,
    intent_has_filters,
    parse_fallback_intent,
)
from .schemas import (
    ChatRequest,
    ChatResponse,
    DiscoverMoviesResponse,
    MovieCatalogResponse,
    MovieConversationRequest,
    MovieConversationResponse,
    MovieIntent,
    QueryAnalysis,
    SearchMoviesResponse,
    SimilarMoviesResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    app.state.settings = settings
    app.state.recommender = MovieRecommender(settings, QdrantGateway(settings))
    app.state.llm = OpenAILLMService(settings)
    yield


app = FastAPI(
    title="Movie Recommendation API",
    version="0.1.0",
    description="Content-based movie recommendation using Word2Vec, Qdrant, and hybrid re-ranking.",
    lifespan=lifespan,
)

settings_for_cors = Settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings_for_cors.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_recommender(request: Request) -> MovieRecommender:
    return request.app.state.recommender


def build_query_analysis(
    *,
    body: ChatRequest,
    intent: MovieIntent,
    interpreter: str,
    settings: Settings,
    execution_mode: str,
    backend_query: str,
    execution_parameters: dict,
    steps: list[str],
) -> QueryAnalysis:
    return QueryAnalysis(
        original_query=body.message,
        interpreter=interpreter,
        llm_model=settings.openai_model if interpreter == "openai" else None,
        extracted_intent=intent,
        execution_mode=execution_mode,
        backend_query=backend_query,
        execution_parameters=execution_parameters,
        steps=steps,
    )


@app.get("/health")
def health(request: Request) -> dict:
    recommender = get_recommender(request)
    try:
        qdrant = recommender.gateway.health()
        collection = recommender.gateway.collection_info().get("result", {})
    except requests.RequestException as error:
        raise HTTPException(status_code=503, detail=f"Qdrant tidak tersedia: {error}") from error

    return {
        "status": "ok",
        "qdrant": qdrant.get("title", "qdrant"),
        "collection": recommender.settings.qdrant_collection,
        "points_count": collection.get("points_count"),
        "llm": {
            "enabled": request.app.state.llm.enabled,
            "model": recommender.settings.openai_model,
        },
    }


@app.get("/movies/search", response_model=SearchMoviesResponse)
def search_movies(
    request: Request,
    title: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=10, ge=1, le=20),
) -> SearchMoviesResponse:
    return SearchMoviesResponse(
        query=title, results=get_recommender(request).search_titles(title, limit)
    )


@app.get("/movies", response_model=MovieCatalogResponse)
def list_movies(
    request: Request,
    limit: int = Query(default=12, ge=1, le=50),
) -> MovieCatalogResponse:
    return MovieCatalogResponse(results=get_recommender(request).catalog(limit))


@app.get("/movies/discover", response_model=DiscoverMoviesResponse)
def discover_movies(
    request: Request,
    genre: list[str] | None = Query(default=None),
    actor: list[str] | None = Query(default=None),
    director: list[str] | None = Query(default=None),
    keyword: list[str] | None = Query(default=None),
    language: list[str] | None = Query(default=None),
    min_rating: float | None = Query(default=None, ge=0, le=10),
    max_rating: float | None = Query(default=None, ge=0, le=10),
    year_from: int | None = Query(default=None, ge=1870, le=2100),
    year_to: int | None = Query(default=None, ge=1870, le=2100),
    min_runtime: int | None = Query(default=None, ge=1, le=1000),
    max_runtime: int | None = Query(default=None, ge=1, le=1000),
    limit: int = Query(default=10, ge=1, le=50),
) -> DiscoverMoviesResponse:
    intent = MovieIntent(
        preferred_genres=genre or [],
        actors=actor or [],
        directors=director or [],
        keywords=keyword or [],
        original_languages=language or [],
        min_rating=min_rating,
        max_rating=max_rating,
        release_year_from=year_from,
        release_year_to=year_to,
        min_runtime=min_runtime,
        max_runtime=max_runtime,
    )
    if not intent_has_filters(intent):
        raise HTTPException(status_code=400, detail="Berikan minimal satu filter pencarian.")
    if min_rating is not None and max_rating is not None and min_rating > max_rating:
        raise HTTPException(status_code=400, detail="min_rating tidak boleh melebihi max_rating.")
    if year_from is not None and year_to is not None and year_from > year_to:
        raise HTTPException(status_code=400, detail="year_from tidak boleh melebihi year_to.")
    if min_runtime is not None and max_runtime is not None and min_runtime > max_runtime:
        raise HTTPException(status_code=400, detail="min_runtime tidak boleh melebihi max_runtime.")
    return DiscoverMoviesResponse(
        filters=intent,
        results=get_recommender(request).discover(intent, limit),
    )


@app.get("/recommend/similar", response_model=SimilarMoviesResponse)
def recommend_similar(
    request: Request,
    title: str = Query(min_length=1, max_length=200),
    top_k: int = Query(default=10, ge=1, le=20),
) -> SimilarMoviesResponse:
    recommender = get_recommender(request)
    try:
        return recommender.recommend(title, top_k)
    except MovieNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except AmbiguousTitleError as error:
        raise HTTPException(
            status_code=409,
            detail={"message": str(error), "candidates": [item.model_dump() for item in error.candidates]},
        ) from error
    except (requests.RequestException, LookupError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


def fallback_movie_answer(movie, message: str) -> str:
    normalized = message.lower()
    if any(term in normalized for term in ["cerita", "sinopsis", "tentang apa", "plot"]):
        return movie.overview or f"Sinopsis {movie.title} belum tersedia pada metadata kami."
    if any(term in normalized for term in ["aktor", "pemain", "cast"]):
        return f"Pemeran yang tercatat untuk {movie.title}: {movie.cast}." if movie.cast else "Data pemeran belum tersedia."
    if any(term in normalized for term in ["sutradara", "director"]):
        return f"{movie.title} disutradarai oleh {movie.director}." if movie.director else "Data sutradara belum tersedia."
    if any(term in normalized for term in ["genre", "jenis film"]):
        return f"Genre {movie.title}: {movie.genres}." if movie.genres else "Data genre belum tersedia."
    if any(term in normalized for term in ["rating", "nilai"]):
        return f"Rating TMDB {movie.title} adalah {movie.vote_average:.1f}/10." if movie.vote_average is not None else "Data rating belum tersedia."
    if any(term in normalized for term in ["durasi", "berapa lama", "runtime"]):
        return f"Durasi {movie.title} adalah {movie.runtime} menit." if movie.runtime else "Data durasi belum tersedia."
    return (
        f"Saya bisa membahas sinopsis, genre, sutradara, pemeran, rating, atau durasi {movie.title}. "
        "OpenAI belum aktif, jadi pertanyaan lanjutan saat ini dijawab dari metadata terstruktur."
    )


@app.post("/movies/{movie_id}/chat", response_model=MovieConversationResponse)
def chat_about_movie(
    movie_id: int,
    request: Request,
    body: MovieConversationRequest,
) -> MovieConversationResponse:
    recommender = get_recommender(request)
    llm: OpenAILLMService = request.app.state.llm
    try:
        movie = recommender.get_movie(movie_id)
    except MovieNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    answer = None
    if llm.enabled:
        try:
            answer = llm.answer_movie_question(movie, body.message, body.history)
        except (OpenAIError, ValueError):
            answer = None

    llm_used = bool(answer)
    return MovieConversationResponse(
        movie=movie,
        answer=answer or fallback_movie_answer(movie, body.message),
        llm_used=llm_used,
        llm_model=recommender.settings.openai_model if llm_used else None,
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: Request, body: ChatRequest) -> ChatResponse:
    recommender = get_recommender(request)
    llm: OpenAILLMService = request.app.state.llm
    intent = None
    llm_used = False
    interpreter = "fallback_pattern"

    if llm.enabled:
        try:
            intent = llm.parse_intent(body.message)
            llm_used = intent is not None
            if llm_used:
                interpreter = "openai"
        except (OpenAIError, ValueError):
            intent = None

    if intent is None:
        intent = parse_fallback_intent(body.message)

    if (
        intent
        and intent.clarification_needed
        and not intent.reference_title
        and not intent_has_filters(intent)
    ):
        query_analysis = build_query_analysis(
            body=body,
            intent=intent,
            interpreter=interpreter,
            settings=recommender.settings,
            execution_mode="clarification",
            backend_query="request_clarification()",
            execution_parameters={"reason": "Tidak ada judul atau filter yang dapat digunakan."},
            steps=[
                "LLM mengekstrak intent dari pesan user.",
                "Backend memvalidasi bahwa judul dan seluruh filter masih kosong.",
                "Backend meminta informasi tambahan sebelum melakukan retrieval.",
            ],
        )
        return ChatResponse(
            status="needs_clarification",
            message=intent.clarification_question
            or "Sebutkan satu judul film yang kamu suka agar rekomendasinya lebih tepat.",
            llm_used=llm_used,
            llm_model=recommender.settings.openai_model if llm_used else None,
            query_analysis=query_analysis,
        )

    if intent and not intent.reference_title and intent_has_filters(intent):
        query_analysis = build_query_analysis(
            body=body,
            intent=intent,
            interpreter=interpreter,
            settings=recommender.settings,
            execution_mode="discovery",
            backend_query="metadata_discovery(filters) -> discovery_ranking -> top_k",
            execution_parameters={
                "filters": intent.model_dump(exclude_none=True),
                "top_k": body.top_k,
                "ranking": "40% rating + 25% vote count + 15% popularity + 20% metadata quality",
            },
            steps=[
                "LLM mengubah bahasa natural menjadi filter terstruktur.",
                "Backend menerapkan OR dalam kategori dan AND antarkategori.",
                "Backend menghitung discovery score untuk film yang lolos filter.",
                f"Backend mengembalikan maksimal {body.top_k} hasil terbaik.",
            ],
        )
        selected = recommender.discover(intent, body.top_k)
        if not selected:
            return ChatResponse(
                status="not_found",
                message="Belum ada film yang memenuhi semua filter tersebut. Coba longgarkan salah satu filter.",
                llm_used=llm_used,
                llm_model=recommender.settings.openai_model if llm_used else None,
                query_analysis=query_analysis,
            )

        response_message = f"Saya menemukan {len(selected)} film yang memenuhi filter kamu."
        if llm.enabled:
            try:
                narrative = llm.create_narrative(body.message, None, selected)
                if narrative:
                    response_message = narrative.message
                    reasons = {item.movie_id: item.reason for item in narrative.explanations}
                    for movie in selected:
                        if movie.id in reasons:
                            movie.reason = reasons[movie.id]
                    llm_used = True
            except (OpenAIError, ValueError):
                pass

        return ChatResponse(
            status="recommendations",
            message=response_message,
            recommendations=selected,
            llm_used=llm_used,
            llm_model=recommender.settings.openai_model if llm_used else None,
            query_analysis=query_analysis,
        )

    title = (
        intent.reference_title
        if intent and intent.reference_title
        else extract_title_candidate(body.message)
    )
    effective_intent = intent or MovieIntent(reference_title=title)
    if not effective_intent.reference_title:
        effective_intent.reference_title = title
    expanded_top_k = max(
        recommender.settings.recommendation_candidate_k,
        body.top_k * 10,
    )
    query_analysis = build_query_analysis(
        body=body,
        intent=effective_intent,
        interpreter=interpreter,
        settings=recommender.settings,
        execution_mode="similarity",
        backend_query="resolve_title -> Qdrant cosine_search -> hybrid_rerank -> intent_filters -> top_k",
        execution_parameters={
            "reference_title": title,
            "qdrant_collection": recommender.settings.qdrant_collection,
            "candidate_pool_target": expanded_top_k,
            "top_k": body.top_k,
            "ranking": "70% similarity + 10% rating + 8% vote count + 7% popularity + 5% metadata quality",
        },
        steps=[
            f'LLM/parser mengambil judul acuan: "{title}".',
            "Backend mencocokkan judul dengan movie ID pada payload lokal.",
            "Backend mengambil vector film acuan dari Qdrant.",
            "Qdrant menjalankan cosine similarity search.",
            "Backend melakukan hybrid re-ranking dan menerapkan filter tambahan.",
            f"Backend mengembalikan maksimal {body.top_k} hasil terbaik.",
        ],
    )

    try:
        result = recommender.recommend(title, expanded_top_k)
    except MovieNotFoundError:
        candidates = recommender.search_titles(title, limit=8)
        return ChatResponse(
            status="not_found",
            message="Saya belum menemukan film tersebut. Coba tulis judul film yang lebih spesifik.",
            candidates=candidates,
            llm_used=llm_used,
            llm_model=recommender.settings.openai_model if llm_used else None,
            query_analysis=query_analysis,
        )
    except AmbiguousTitleError as error:
        return ChatResponse(
            status="needs_selection",
            message="Saya menemukan beberapa film. Pilih salah satu agar rekomendasi lebih tepat.",
            candidates=error.candidates,
            llm_used=llm_used,
            llm_model=recommender.settings.openai_model if llm_used else None,
            query_analysis=query_analysis,
        )
    except (requests.RequestException, LookupError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    filtered = apply_intent_filters(result.recommendations, intent)
    if intent_has_filters(intent) and not filtered:
        return ChatResponse(
            status="not_found",
            message=(
                f"Film yang mirip dengan {result.source.title} ditemukan, tetapi tidak ada yang "
                "memenuhi semua filter. Coba longgarkan salah satu filter."
            ),
            source=result.source,
            llm_used=llm_used,
            llm_model=recommender.settings.openai_model if llm_used else None,
            query_analysis=query_analysis,
        )
    selected = filtered[: body.top_k]
    response_message = f"Berikut rekomendasi film yang mirip dengan {result.source.title}."

    if llm.enabled:
        try:
            narrative = llm.create_narrative(body.message, result.source, selected)
            if narrative:
                response_message = narrative.message
                reasons = {item.movie_id: item.reason for item in narrative.explanations}
                for movie in selected:
                    if movie.id in reasons:
                        movie.reason = reasons[movie.id]
                llm_used = True
        except (OpenAIError, ValueError):
            pass

    return ChatResponse(
        status="recommendations",
        message=response_message,
        source=result.source,
        recommendations=selected,
        llm_used=llm_used,
        llm_model=recommender.settings.openai_model if llm_used else None,
        query_analysis=query_analysis,
    )
