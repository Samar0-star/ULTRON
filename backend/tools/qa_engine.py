# venv/backend/tools/qa_engine.py
"""
Question & Answer Engine Tool
Handles document-based Q&A using vector search and LLM responses.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import json
import re
from datetime import datetime

# Import your existing tools
from backend.memory.vectorstore import vectorstore_instance
from backend.llm_manager import get_llm_manager


@dataclass
class QARequest:
    """Q&A request structure."""
    question: str
    context_docs: Optional[List[str]] = None
    max_results: int = 5
    include_sources: bool = True
    temperature: float = 0.7
    max_tokens: int = 32768


@dataclass
class QAResponse:
    """Q&A response structure."""
    answer: str
    confidence: float
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    processing_time: float
    timestamp: datetime


class QAEngine:
    """Advanced Question & Answer engine for document analysis."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm_manager = get_llm_manager()
        self.vector_store = vectorstore_instance
        
        # Q&A prompts
        self.qa_prompts = {
            "general": """Based on the following context, answer the question accurately and concisely.
            
Context: {context}

Question: {question}

Answer:""",
            
            "analytical": """Analyze the following context and provide a detailed answer to the question.
Include relevant facts, figures, and insights from the provided information.

Context: {context}

Question: {question}

Analysis:""",
            
            "comparative": """Compare and contrast the information in the context to answer the question.
Highlight similarities, differences, and key insights.

Context: {context}

Question: {question}

Comparison:"""
        }
        
    def ask_question(self, request: QARequest) -> QAResponse:
        """Main method to ask a question and get an answer."""
        start_time = datetime.now()
        
        try:
            # Step 1: Retrieve relevant documents
            if request.context_docs:
                relevant_docs = [{"content": d, "metadata": {"source": f"Provided Doc {i+1}"}, "score": 1.0} for i, d in enumerate(request.context_docs)]
            else:
                relevant_docs = self._retrieve_relevant_documents(request.question, request.max_results)
            
            # Step 2: Generate context from documents
            context = self._generate_context(relevant_docs)
            
            # Step 3: Generate answer using LLM
            answer, confidence = self._generate_answer(request.question, context, request)
            
            # Step 4: Prepare sources
            sources = self._prepare_sources(relevant_docs) if request.include_sources else []
            
            # Step 5: Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Step 6: Create response
            response = QAResponse(
                answer=answer,
                confidence=confidence,
                sources=sources,
                metadata={
                    "question_type": self._classify_question(request.question),
                    "context_length": len(context),
                    "documents_used": len(relevant_docs)
                },
                processing_time=processing_time,
                timestamp=datetime.now()
            )
            
            self.logger.info(f"Q&A completed in {processing_time:.2f}s with confidence {confidence:.2f}")
            return response
            
        except Exception as e:
            self.logger.error(f"Error in Q&A engine: {str(e)}")
            raise e
    
    def _retrieve_relevant_documents(self, question: str, max_results: int) -> List[Dict[str, Any]]:
        """Retrieve relevant documents using vector search."""
        try:
            if hasattr(self.vector_store, "search"):
                results = self.vector_store.search(query=question, k=max_results)
            elif hasattr(self.vector_store, "similarity_search"):
                results = self.vector_store.similarity_search(query=question, k=max_results)
            else:
                results = []
            
            # Format results
            formatted_results = []
            for result in results:
                if isinstance(result, dict):
                    meta = result.get("metadata") if isinstance(result.get("metadata"), dict) else {
                        k: v for k, v in result.items() if k not in ("text", "content", "distance", "score")
                    }
                    dist = result.get("distance")
                    score = result.get("score")
                    if score is None and isinstance(dist, (int, float)):
                        score = max(0.0, 1.0 - (float(dist) ** 2) / 2.0)
                    formatted_results.append({
                        "content": result.get("content") or result.get("text") or str(result),
                        "metadata": meta,
                        "score": float(score) if score is not None else 0.0
                    })
                else:
                    formatted_results.append({
                        "content": result.page_content if hasattr(result, 'page_content') else str(result),
                        "metadata": result.metadata if hasattr(result, 'metadata') else {},
                        "score": getattr(result, 'score', 0.0)
                    })
            
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"Error retrieving documents: {str(e)}")
            return []
    
    def _generate_context(self, documents: List[Dict[str, Any]]) -> str:
        """Generate context string from retrieved documents."""
        if not documents:
            return "No relevant documents found."
        
        context_parts = []
        for i, doc in enumerate(documents, 1):
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            
            # Add document identifier
            doc_id = metadata.get("source", f"Document {i}")
            context_parts.append(f"[{doc_id}]: {content}")
        
        return "\n\n".join(context_parts)
    
    def _generate_answer(self, question: str, context: str, request: QARequest) -> tuple[str, float]:
        """Generate answer using LLM."""
        try:
            # Select appropriate prompt based on question type
            question_type = self._classify_question(question)
            prompt_template = self.qa_prompts.get(question_type, self.qa_prompts["general"])
            
            # Format prompt
            prompt = prompt_template.format(
                context=context,
                question=question
            )
            
            # Generate response using LLMManager.run
            if hasattr(self.llm_manager, "run"):
                response = self.llm_manager.run(
                    prompt=prompt,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                )
            else:
                response = self.llm_manager.generate_response(
                    prompt=prompt,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                )
            
            # Extract answer and estimate confidence
            answer = response.get("text", "Unable to generate answer.") if isinstance(response, dict) else str(response)
            confidence = self._estimate_confidence(question, answer, context)
            
            return answer, confidence
            
        except Exception as e:
            self.logger.error(f"Error generating answer: {str(e)}")
            return "Error generating answer. Please try again.", 0.0
    
    def _classify_question(self, question: str) -> str:
        """Classify the type of question to select appropriate prompt."""
        question_lower = question.lower()
        
        # Analytical questions
        if any(word in question_lower for word in ["analyze", "explain", "describe", "discuss", "how", "why"]):
            return "analytical"
        
        # Comparative questions
        if any(word in question_lower for word in ["compare", "contrast", "difference", "similar", "versus", "vs"]):
            return "comparative"
        
        # General questions
        return "general"
    
    def _estimate_confidence(self, question: str, answer: str, context: str) -> float:
        """Estimate confidence score for the answer."""
        try:
            # Simple confidence estimation based on answer length and context relevance
            base_confidence = 0.5
            
            # Boost confidence for longer, more detailed answers
            if len(answer) > 100:
                base_confidence += 0.2
            
            # Boost confidence if answer contains specific details from context
            context_words = set(re.findall(r'\b\w+\b', context.lower()))
            answer_words = set(re.findall(r'\b\w+\b', answer.lower()))
            overlap = len(context_words.intersection(answer_words))
            
            if overlap > 10:
                base_confidence += 0.2
            
            # Boost confidence for structured answers
            if any(marker in answer.lower() for marker in ["first", "second", "third", "1.", "2.", "3."]):
                base_confidence += 0.1
            
            return min(base_confidence, 1.0)
            
        except Exception:
            return 0.5
    
    def _prepare_sources(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare source information for the answer."""
        sources = []
        
        for doc in documents:
            metadata = doc.get("metadata", {})
            source_info = {
                "title": metadata.get("title", "Unknown"),
                "source": metadata.get("source", "Unknown"),
                "page": metadata.get("page", "Unknown"),
                "score": doc.get("score", 0.0),
                "excerpt": doc.get("content", "")[:200] + "..." if len(doc.get("content", "")) > 200 else doc.get("content", "")
            }
            sources.append(source_info)
        
        return sources
    
    def batch_qa(self, questions: List[str], **kwargs) -> List[QAResponse]:
        """Process multiple questions in batch."""
        responses = []
        
        for question in questions:
            request = QARequest(question=question, **kwargs)
            response = self.ask_question(request)
            responses.append(response)
        
        return responses
    
    def get_qa_history(self, session_id: str) -> List[QAResponse]:
        """Get Q&A history for a session."""
        # This would integrate with your memory system
        # For now, return empty list
        return []
    
    def export_qa_session(self, session_id: str, format: str = "json") -> str:
        """Export Q&A session in specified format."""
        history = self.get_qa_history(session_id)
        
        if format.lower() == "json":
            return json.dumps([self._response_to_dict(response) for response in history], indent=2)
        elif format.lower() == "csv":
            # Implement CSV export
            return "CSV export not implemented yet"
        else:
            return "Unsupported format"
    
    def _response_to_dict(self, response: QAResponse) -> Dict[str, Any]:
        """Convert QAResponse to dictionary for export."""
        return {
            "answer": response.answer,
            "confidence": response.confidence,
            "sources": response.sources,
            "metadata": response.metadata,
            "processing_time": response.processing_time,
            "timestamp": response.timestamp.isoformat()
        }


# Global QA engine instance
qa_engine = QAEngine()


def ask_question(question: str, **kwargs) -> QAResponse:
    """Convenience function to ask a question."""
    request = QARequest(question=question, **kwargs)
    return qa_engine.ask_question(request)


def batch_questions(questions: List[str], **kwargs) -> List[QAResponse]:
    """Convenience function for batch Q&A."""
    return qa_engine.batch_qa(questions, **kwargs)
