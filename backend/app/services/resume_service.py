"""Resume Service – Context Resume briefing generator.

A read-only aggregation service that gathers context from chunks,
entities, TF-IDF similarity, and optionally the LLM to produce a
synthesized "Morning Briefing" for a project.

No database writes – pure read aggregation.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from ..core.ollama_client import KomorebiLLM
from ..core.similarity import TFIDFService
from ..db.repository import ChunkRepository, EntityRepository, ProjectRepository
from ..models import EntityType
from ..models.resume import BriefingSection, ProjectBriefing

logger = logging.getLogger(__name__)

# Maximum recent chunks to include in briefing
MAX_RECENT_CHUNKS = 10

# Approximate characters per token (for context window estimation)
CHARS_PER_TOKEN = 4

# Max context window for prompt (matches CompactorService)
MAX_CONTEXT_WINDOW = 12000


class ResumeService:
    """Generates project context resume briefings.

    Aggregates data from multiple sources:
    1. Project metadata (name, description, context_summary)
    2. Recent chunks (last N by recency)
    3. Decision entities (filtered by time window)
    4. TF-IDF related chunks (semantically similar to most recent)

    Then synthesizes a 3-bullet briefing via LLM (or template fallback).
    """

    def __init__(
        self,
        chunk_repo: ChunkRepository,
        project_repo: ProjectRepository,
        entity_repo: EntityRepository,
        tfidf_service: TFIDFService,
        llm: KomorebiLLM,
    ) -> None:
        self.chunk_repo = chunk_repo
        self.project_repo = project_repo
        self.entity_repo = entity_repo
        self.tfidf_service = tfidf_service
        self.llm = llm

    async def generate_briefing(
        self,
        project_id: UUID,
        hours: int = 48,
    ) -> ProjectBriefing:
        """Generate a context resume briefing for a project.

        Args:
            project_id: The project UUID.
            hours: Look-back window for recent decisions (default 48h).

        Returns:
            ProjectBriefing with summary, recent context, and decisions.

        Raises:
            ValueError: If project not found.
        """
        # 1. Fetch project
        project = await self.project_repo.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # 2. Fetch recent chunks (non-archived preferred)
        recent_chunks = await self.chunk_repo.list(
            project_id=project_id,
            limit=MAX_RECENT_CHUNKS,
        )

        # 3. Edge case: empty project
        if not recent_chunks:
            return ProjectBriefing(
                project_id=project_id,
                project_name=project.name,
                summary="No activity yet. Start capturing chunks to build context.",
                sections=[
                    BriefingSection(
                        heading="Getting Started",
                        content="This project has no captured chunks yet. "
                        "Use the capture endpoint or CLI to start adding context.",
                    )
                ],
                recent_chunks=[],
                decisions=[],
                related_context=[],
                ollama_available=await self.llm.is_available(),
            )

        # 4. Fetch recent decisions
        since = datetime.utcnow() - timedelta(hours=hours) if hours > 0 else None
        decisions = await self.entity_repo.list_by_project(
            project_id=project_id,
            entity_type=EntityType.DECISION,
            since=since,
            limit=20,
        )

        # 5. TF-IDF related context
        related_context = await self._find_related_context(recent_chunks)

        # 6. Generate summary (LLM or fallback)
        ollama_available = await self.llm.is_available()
        context_usage: Optional[float] = None

        if ollama_available:
            try:
                prompt, context_usage = self._build_context_prompt(
                    project, recent_chunks, decisions, related_context
                )
                summary = await self.llm.generate(
                    prompt=prompt,
                    system=self._system_anchor(project.name, project.description),
                )
                sections = self._parse_sections(summary, recent_chunks)
            except Exception as exc:
                logger.warning("LLM generation failed, using fallback: %s", exc)
                ollama_available = False
                summary = self._build_fallback_summary(
                    project, recent_chunks, decisions
                )
                sections = self._fallback_sections(recent_chunks, decisions)
        else:
            summary = self._build_fallback_summary(
                project, recent_chunks, decisions
            )
            sections = self._fallback_sections(recent_chunks, decisions)

        return ProjectBriefing(
            project_id=project_id,
            project_name=project.name,
            summary=summary,
            sections=sections,
            recent_chunks=recent_chunks,
            decisions=decisions,
            related_context=related_context,
            ollama_available=ollama_available,
            context_window_usage=context_usage,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _find_related_context(
        self, recent_chunks: list,
    ) -> list[str]:
        """Find TF-IDF related content snippets from corpus."""
        if not recent_chunks:
            return []

        try:
            # Build corpus from available chunks
            corpus = await self.chunk_repo.get_all_content()
            if len(corpus) < 2:
                return []

            target_id = str(recent_chunks[0].id)
            related = self.tfidf_service.find_related(
                target_id=target_id,
                documents=corpus,
                top_k=3,
            )

            # Extract content snippets for related docs
            corpus_dict = {doc_id: content for doc_id, content in corpus}
            snippets: list[str] = []
            for doc_id, score, terms in related:
                content = corpus_dict.get(doc_id, "")
                # Truncate to first 200 chars for brevity
                snippet = content[:200].strip()
                if snippet:
                    snippets.append(snippet)

            return snippets
        except Exception as exc:
            logger.warning("TF-IDF related lookup failed: %s", exc)
            return []

    def _build_context_prompt(
        self,
        project: object,
        chunks: list,
        decisions: list,
        related: list[str],
    ) -> tuple[str, float]:
        """Build structured prompt for LLM synthesis.

        Returns:
            Tuple of (prompt_text, context_window_usage_fraction).
        """
        parts: list[str] = []

        parts.append(f"Project: {project.name}")
        if project.description:  # type: ignore[union-attr]
            parts.append(f"Description: {project.description}")  # type: ignore[union-attr]

        if project.context_summary:  # type: ignore[union-attr]
            parts.append(f"\nPrior context summary:\n{project.context_summary}")  # type: ignore[union-attr]

        parts.append("\n--- Recent Activity (newest first) ---")
        for chunk in chunks[:5]:
            label = chunk.summary or chunk.content[:100]
            parts.append(f"• [{chunk.status.value}] {label}")

        if decisions:
            parts.append("\n--- Recent Decisions ---")
            for d in decisions[:5]:
                parts.append(f"• {d.value}")

        if related:
            parts.append("\n--- Related Context ---")
            for snippet in related[:3]:
                parts.append(f"• {snippet[:150]}")

        context_text = "\n".join(parts)

        parts.append(
            "\n\nBased on the above context, write a concise 3-bullet briefing:\n"
            "• Where you left off: ...\n"
            "• Key context: ...\n"
            "• Suggested next step: ...\n"
            "Keep each bullet under 50 words."
        )

        prompt = "\n".join(parts)

        # Estimate context window usage
        token_estimate = len(context_text) / CHARS_PER_TOKEN
        usage = min(token_estimate / MAX_CONTEXT_WINDOW, 1.0)

        return prompt, round(usage, 3)

    def _parse_sections(
        self, llm_output: str, chunks: list
    ) -> list[BriefingSection]:
        """Parse LLM 3-bullet output into BriefingSection objects."""
        sections: list[BriefingSection] = []
        lines = llm_output.strip().split("\n")

        headings = ["Where You Left Off", "Key Context", "Suggested Next Step"]
        heading_idx = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Strip bullet markers
            for prefix in ("• ", "- ", "* ", "· "):
                if line.startswith(prefix):
                    line = line[len(prefix) :]
                    break

            # Remove heading prefix if present (e.g., "Where you left off: ...")
            content = line
            for h in headings:
                lower_h = h.lower()
                if content.lower().startswith(lower_h):
                    content = content[len(lower_h) :].lstrip(": ")
                    break

            if heading_idx < len(headings):
                heading = headings[heading_idx]
            else:
                heading = f"Additional ({heading_idx + 1})"

            # Link first section to most recent chunk
            chunk_id = None
            if heading_idx == 0 and chunks:
                chunk_id = chunks[0].id

            sections.append(
                BriefingSection(
                    heading=heading,
                    content=content,
                    chunk_id=chunk_id,
                )
            )
            heading_idx += 1

        return sections

    def _build_fallback_summary(
        self,
        project: object,
        chunks: list,
        decisions: list,
    ) -> str:
        """Template-based fallback when LLM is unavailable."""
        parts: list[str] = []

        # Where you left off
        if chunks:
            latest = chunks[0]
            label = latest.summary or latest.content[:80]
            parts.append(f"• Where you left off: {label}")
        else:
            parts.append("• Where you left off: No recent activity recorded.")

        # Key context
        if decisions:
            decision_list = ", ".join(d.value for d in decisions[:3])
            parts.append(f"• Key context — recent decisions: {decision_list}")
        elif project.context_summary:  # type: ignore[union-attr]
            parts.append(f"• Key context: {project.context_summary[:120]}")  # type: ignore[union-attr]
        else:
            parts.append("• Key context: No compacted context available yet.")

        # Suggested next step
        inbox_count = sum(1 for c in chunks if c.status.value == "inbox")
        if inbox_count > 0:
            parts.append(
                f"• Suggested next step: Process {inbox_count} inbox chunk(s) "
                "to build richer context."
            )
        else:
            parts.append(
                "• Suggested next step: Continue capturing context or run compaction."
            )

        return "\n".join(parts)

    def _fallback_sections(
        self, chunks: list, decisions: list
    ) -> list[BriefingSection]:
        """Generate structured sections for fallback mode."""
        sections: list[BriefingSection] = []

        if chunks:
            latest = chunks[0]
            sections.append(
                BriefingSection(
                    heading="Where You Left Off",
                    content=latest.summary or latest.content[:120],
                    chunk_id=latest.id,
                )
            )

        if decisions:
            decision_text = "; ".join(d.value for d in decisions[:5])
            sections.append(
                BriefingSection(
                    heading="Recent Decisions",
                    content=decision_text,
                )
            )

        return sections

    @staticmethod
    def _system_anchor(project_name: str, description: Optional[str] = None) -> str:
        """Build system prompt with project context anchor."""
        anchor = (
            f"You are summarizing the current state of the project '{project_name}'."
        )
        if description:
            anchor += f" Project description: {description}."
        anchor += (
            " Your role is to help the user quickly resume work context. "
            "Be concise, technical, and actionable."
        )
        return anchor
