"""
Nexus Retriever - Avon's Active Recall Engine.

Dynamically retrieves relevant facts from the WorldModel (Nexus) 
to provide the agent with local, relevant context for its current task.
"""
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class NexusRetriever:
    """
    Queries the Avon WorldModel (Nexus) for context-specific knowledge.
    """
    def __init__(self, world_model):
        self.nexus = world_model

    def retrieve_relevant_nodes(self, focus_area: str, limit: int = 12) -> str:
        """
        Performs a 'Knowledge Jump' into the Nexus to find nodes related to the focus area.
        """
        if not self.nexus:
            return ""
            
        if not isinstance(focus_area, str):
            if isinstance(focus_area, list):
                focus_area = " ".join(str(item) for item in focus_area)
            elif isinstance(focus_area, dict):
                focus_area = str(focus_area.get('statement', '')) or str(focus_area.get('topic', '')) or str(focus_area)
            else:
                focus_area = str(focus_area)

        # Query the WorldModel using its semantic/keyword engine
        knowledge_nodes = self.nexus.query(focus_area, min_confidence=0.4, max_results=limit)
        
        # Format the recall context
        recall_parts = []
        
        if knowledge_nodes:
            recall_parts.append(f"--- NEXUS ACTIVE RECALL ({focus_area}) ---")
            for node in knowledge_nodes:
                val = str(node.value)
                if len(val) > 2500: val = val[:2500] + "..."
                recall_parts.append(f" NODE {node.key}: {val} (Confidence: {node.confidence:.2f})")

        # Check for deep entities in the graph if available
        if hasattr(self.nexus, "_entities"):
            search_term = focus_area.lower()
            entity_matches = []
            for eid, entity in self.nexus._entities.items():
                if search_term in entity.type.lower() or \
                   any(search_term in str(v).lower() for v in entity.properties.values()):
                    entity_matches.append(entity)
            
            if entity_matches:
                recall_parts.append("\n--- RELATED ENTITIES ---")
                for ent in entity_matches[:4]:
                    recall_parts.append(f" {ent.type}: {ent.properties}")

        if not recall_parts:
            return ""
            
        return "\n".join(recall_parts)
