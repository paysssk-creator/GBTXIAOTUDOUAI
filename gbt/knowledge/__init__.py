"""GBT Knowledge Base - A-Share & Desktop Control Expertise"""
from gbt.knowledge.ashare import ASHARE_KNOWLEDGE
from gbt.knowledge.desktop import DESKTOP_KNOWLEDGE

SYSTEM_KNOWLEDGE = ASHARE_KNOWLEDGE + "\n\n" + DESKTOP_KNOWLEDGE
