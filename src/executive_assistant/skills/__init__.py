"""Skills for the Executive Assistant agent."""

from executive_assistant.skills.builder import SkillsBuilder
from executive_assistant.skills.loader import load_and_register_skills, load_skills_from_directory
from executive_assistant.skills.registry import Skill, SkillsRegistry, get_skills_registry, reset_skills_registry
from executive_assistant.skills.tool import get_skill_tool, load_skill

__all__ = [
    # Core classes
    "Skill",
    "SkillsRegistry",
    "SkillsBuilder",
    # Registry functions
    "get_skills_registry",
    "reset_skills_registry",
    # Loader functions
    "load_skills_from_directory",
    "load_and_register_skills",
    # Tool
    "load_skill",
    "get_skill_tool",
]
