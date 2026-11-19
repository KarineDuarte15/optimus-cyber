"""Enums e tipos de opção compartilhados pelos comandos."""

from enum import StrEnum


class ReviewFocus(StrEnum):
    """Foco da revisão de código."""

    ALL = "all"
    QUALITY = "quality"
    SECURITY = "security"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"


class CommitType(StrEnum):
    """Tipos do padrão Conventional Commits."""

    FEAT = "feat"
    FIX = "fix"
    DOCS = "docs"
    STYLE = "style"
    REFACTOR = "refactor"
    PERF = "perf"
    TEST = "test"
    BUILD = "build"
    CI = "ci"
    CHORE = "chore"


class DocsTarget(StrEnum):
    """Alvo da atualização de documentação."""

    README = "readme"
    CHANGELOG = "changelog"
    API = "api"
    ALL = "all"
