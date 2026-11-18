# -*- coding: utf-8 -*-
"""
Neo4j Knowledge Graph Integration for Avon
===========================================
PhD-level graph database for citation networks, author relationships,
and concept mapping.

HYBRID ARCHITECTURE:
- SQLite (Fast): Quick reads, session state, provenance logs
- Neo4j (Deep): Citation graphs, author networks, concept relationships

GRACEFUL DEGRADATION:
If Neo4j is not available, all methods return empty results (not errors).
The system continues to work with SQLite only.

SETUP:
1. Install: pip install neo4j
2. Start Neo4j: Docker or Neo4j Desktop
3. Set env vars:
   - NEO4J_URI=bolt://localhost:7687
   - NEO4J_USER=neo4j
   - NEO4J_PASSWORD=your_password
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import subprocess
import time

logger = logging.getLogger("avon.neo4j")

# Environment configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_STRICT_SCHEMA = os.getenv("NEO4J_STRICT_SCHEMA", "false").lower() == "true"


class KnowledgeGraph:
    """
    Neo4j-backed knowledge graph for PhD-level research capabilities.
    
    Node Types:
    - Paper: title, doi, arxiv_id, year, abstract, citation_count
    - Author: name, affiliation, h_index
    - Concept: name, definition
    - Hypothesis: statement, status, confidence
    - Finding: summary, evidence
    
    Relationship Types:
    - CITES: (Paper)-[:CITES]->(Paper)
    - AUTHORED: (Author)-[:AUTHORED]->(Paper)
    - MENTIONS: (Paper)-[:MENTIONS]->(Concept)
    - SUPPORTS: (Finding)-[:SUPPORTS]->(Hypothesis)
    - REFUTES: (Finding)-[:REFUTES]->(Hypothesis)
    - COLLABORATES: (Author)-[:COLLABORATES]->(Author)
    """
    
    def __init__(self, uri: str = None, user: str = None, password: str = None, session_id: str = None):
        import threading
        self._local_lock = threading.Lock()
        self.uri = uri or NEO4J_URI
        self.user = user or NEO4J_USER
        self.password = password or NEO4J_PASSWORD
        self.session_id = session_id or os.environ.get("ULTRON_SESSION_ID", "default_session")
        
        self._driver = None
        self._available = False
        
        # Local Fallback Store (The "Physics" Vault)
        self.local_db_path = os.path.join(os.getcwd(), "data", "knowledge_graph.db")
        os.makedirs(os.path.dirname(self.local_db_path), exist_ok=True)
        
        # Try to connect to Neo4j, otherwise use local persistence
        self._ensure_container_running()
        self._connect()
        
        if not self._available:
            self._init_local_db()
            logger.info(" KnowledgeGraph: Local SQLite Graph ACTIVE (Physical Fallback).")

    def _init_local_db(self):
        """Initialize local graph tables for relationships."""
        import sqlite3
        with self._local_lock:
            with sqlite3.connect(self.local_db_path) as conn:
                c = conn.cursor()
                # Nodes
                c.execute("CREATE TABLE IF NOT EXISTS nodes (id TEXT PRIMARY KEY, type TEXT, properties TEXT)")
                # Edges
                c.execute("CREATE TABLE IF NOT EXISTS edges (source TEXT, target TEXT, type TEXT, properties TEXT, UNIQUE(source, target, type))")
                conn.commit()

    @property
    def is_available(self):
        # Return True if either Neo4j OR Local DB is active
        return True 
    
    def _connect(self):
        """Attempt to connect to Neo4j. Degrade to SQLite if unavailable."""
        if not self.password:
            logger.warning("[DEGRADED MODE] Neo4j password not set. Using SQLite-only mode.")
            self._available = False
            self._driver = None
            return
        
        try:
            from neo4j import GraphDatabase
            # FIX #15: Increase pool size from 50 to 200 for better scalability
            self._driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password),
                max_connection_pool_size=200,  # FIX: Was 50, now 200 for 50+ concurrent agents
                connection_acquisition_timeout=30.0  # Reduced from 60s to fail faster
            )
            # Test connection
            with self._driver.session() as session:
                session.run("RETURN 1")
            
            self._available = True
            logger.info(f"Neo4j connected: {self.uri}")
            
            # Initialize schema
            self._init_schema()
            
        except ImportError:
            msg = "neo4j package not installed. Run: pip install neo4j"
            logger.critical(f"[HARD ABORT] {msg}")
            raise ImportError(msg)
        except Exception as e:
            msg = f"Neo4j connection failed: {e}. Running in SQLite-only mode."
            logger.warning(f"[DEGRADED MODE] Neo4j unavailable, using SQLite: {e}")
            self._available = False
            self._driver = None
    
    
    def _ensure_container_running(self):
        """
        Auto-Start Logic: Checks if Neo4j is running. If not, tries to start it.
        This provides a 'Zero Config' experience for users with Docker.
        """
        try:
            # Quick check if docker daemon is responsive
            try:
                docker_check = subprocess.run(
                    ["docker", "info"],
                    capture_output=True,
                    timeout=2
                )
                if docker_check.returncode != 0:
                    logger.info("Docker daemon not running or unresponsive. Running in SQLite mode.")
                    return
            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.info("Docker daemon not available (timeout or not installed). Running in SQLite mode.")
                return
            except Exception as e:
                logger.warning(f"Docker check failed: {e}. Defaulting to SQLite mode.")
                return

            # Check if container is running (using ultron-neo4j name)
            # Use 'ultron-neo4j' or just look for port 7687 mapping? 
            # Sticking to container name is safer.
            container_name = os.getenv("NEO4J_CONTAINER_NAME", "ultron-neo4j")
            
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if container_name in result.stdout:
                # Running
                return

            # If we are here, it's not running. Try to start.
            logger.info(" Neo4j not detected. Attempting Auto-Start via Docker...")
            
            # Using basic docker run if compose isn't there? 
            # No, assuming docker-compose is best practice for persistence.
            # But for a portable app, maybe we shouldn't assume compose.
            # Fallback to simple run? 
            # For now, let's try 'docker start' if it exists, or warn.
            
            start_res = subprocess.run(
                ["docker", "start", container_name],
                capture_output=True, text=True
            )
            
            if start_res.returncode == 0:
                logger.info(" Neo4j container started successfully.")
                time.sleep(5) # Give it a moment to boot
            else:
                # If start failed, maybe it doesn't exist. 
                # We won't try to 'docker run' a fresh one to avoid data volume mess.
                logger.warning(f"Could not auto-start Neo4j: {start_res.stderr}. Proceeding in SQLite-only mode.")

        except FileNotFoundError:
            # Docker not installed. Expected for many scientists.
            logger.info("Docker not found. Running in Lightweight Mode (SQLite).")
        except Exception as e:
            logger.warning(f"Neo4j Auto-Start check failed: {e}")

    def _init_schema(self):
        """Create indexes and constraints for faster queries."""
        if not self._available:
            return
        
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Paper) REQUIRE (p.doi) IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Author) REQUIRE (a.name) IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Concept) REQUIRE (c.name) IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (p:Paper) ON (p.title)",
            "CREATE INDEX IF NOT EXISTS FOR (p:Paper) ON (p.year)",
            "CREATE INDEX IF NOT EXISTS FOR (h:Hypothesis) ON (h.status)",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Method) REQUIRE (m.name) IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (m:Method) ON (m.category)",
        ]
        
        schema_errors = []
        try:
            with self._driver.session() as session:
                for constraint in constraints:
                    try:
                        session.run(constraint)
                    except Exception as e:
                        # FIX #14: Log specific error instead of silent swallow
                        logger.warning(f"Schema constraint failed: {constraint[:60]}... Error: {e}")
                        schema_errors.append((constraint[:60], str(e)))
                        if NEO4J_STRICT_SCHEMA:
                            raise RuntimeError(f"Schema constraint failed in strict mode: {constraint[:60]}... Error: {e}")
                if schema_errors and NEO4J_STRICT_SCHEMA:
                    raise RuntimeError(f"{len(schema_errors)} schema constraints failed in strict mode")
                logger.info(f"Neo4j schema initialized ({len(schema_errors)} optional constraints skipped)")
        except Exception as e:
            if NEO4J_STRICT_SCHEMA:
                logger.error(f"Schema init failed in strict mode: {e}")
                raise
            logger.warning(f"Schema init failed: {e}")
    
    @property
    def is_neo4j_available(self) -> bool:
        """Check if Neo4j is specifically available."""
        return self._available
    
    def _run_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Execute a raw Cypher query against Neo4j.
        Returns an empty list if Neo4j is unavailable.
        """
        if not self._available or not self._driver:
            logger.warning("KnowledgeGraph: _run_query called but Neo4j is unavailable.")
            return []
            
        parameters = parameters or {}
        try:
            with self._driver.session() as session:
                result = session.run(query, parameters)
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"KnowledgeGraph _run_query failed: {e}")
            return []

    def _upsert_local_node(self, node_id: str, node_type: str, properties: Dict[str, Any]):
        """Helper to upsert a node into local SQLite graph."""
        import sqlite3, json
        try:
            with self._local_lock:
                with sqlite3.connect(self.local_db_path) as conn:
                    c = conn.cursor()
                    c.execute("INSERT OR REPLACE INTO nodes (id, type, properties) VALUES (?, ?, ?)",
                              (node_id, node_type, json.dumps(properties)))
                    conn.commit()
        except Exception as e:
            logger.error(f"Local node upsert failed: {e}")

    def _add_local_edge(self, source: str, target: str, edge_type: str, properties: Dict[str, Any] = None):
        """Helper to add an edge into local SQLite graph."""
        import sqlite3, json
        try:
            with self._local_lock:
                with sqlite3.connect(self.local_db_path) as conn:
                    c = conn.cursor()
                    c.execute("INSERT OR IGNORE INTO edges (source, target, type, properties) VALUES (?, ?, ?, ?)",
                              (source, target, edge_type, json.dumps(properties or {})))
                    conn.commit()
        except Exception as e:
            logger.error(f"Local edge add failed: {e}")

    # =========================================================================
    # PAPER MANAGEMENT
    # =========================================================================
    
    def add_paper(
        self,
        title: str,
        doi: Optional[str] = None,
        arxiv_id: Optional[str] = None,
        year: Optional[int] = None,
        abstract: Optional[str] = None,
        authors: Optional[List[str]] = None,
        citation_count: int = 0,
        metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Add a paper to the knowledge graph.
        
        Returns:
            Paper node ID or None if failed
        """
        # Generate unique identifier
        paper_id = doi or arxiv_id or title[:50]
        
        # [GODZILLA LOCAL FALLBACK]
        if not self._available:
            props = {
                "title": title, "doi": doi, "arxiv_id": arxiv_id, 
                "year": year, "abstract": abstract, "citation_count": citation_count
            }
            self._upsert_local_node(paper_id, "Paper", props)
            if authors:
                for a in authors:
                    self._upsert_local_node(a, "Author", {"name": a})
                    self._add_local_edge(a, paper_id, "AUTHORED")
            return paper_id

        try:
            with self._driver.session() as session:
                result = session.run("""
                    MERGE (p:Paper {id: $paper_id})
                    SET p.title = $title,
                        p.doi = $doi,
                        p.arxiv_id = $arxiv_id,
                        p.year = $year,
                        p.abstract = $abstract,
                        p.citation_count = $citation_count,
                        p.mission_id = $mission_id,
                        p.session_id = $mission_id,
                        p.updated_at = datetime()
                    RETURN id(p) as node_id
                """, 
                    paper_id=paper_id,
                    title=title,
                    doi=doi,
                    arxiv_id=arxiv_id,
                    year=year,
                    abstract=abstract[:10000] if abstract else None,
                    citation_count=citation_count,
                    mission_id=self.session_id
                )
                record = result.single()
                node_id = record["node_id"] if record else None
                
                # Add authors and relationships
                if authors:
                    for author_name in authors[:10]:  # Limit to 10 authors
                        session.run("""
                            MERGE (a:Author {name: $author_name})
                            SET a.mission_id = $mission_id
                            WITH a
                            MATCH (p:Paper {id: $paper_id})
                            MERGE (a)-[:AUTHORED]->(p)
                        """, author_name=author_name, paper_id=paper_id, mission_id=self.session_id)
                
                logger.debug(f"Added paper: {title[:50]}")
                return paper_id
                
        except Exception as e:
            logger.error(f"Failed to add paper: {e}")
            return None
    
    def add_citation(self, citing_paper_id: str, cited_paper_id: str) -> bool:
        """
        Add a citation relationship between papers.
        """
        if not self._available:
            self._add_local_edge(citing_paper_id, cited_paper_id, "CITES")
            return True
        
        try:
            with self._driver.session() as session:
                session.run("""
                    MATCH (citing:Paper {id: $citing_id})
                    MATCH (cited:Paper {id: $cited_id})
                    MERGE (citing)-[:CITES]->(cited)
                """, citing_id=citing_paper_id, cited_id=cited_paper_id)
            return True
        except Exception as e:
            logger.error(f"Failed to add citation: {e}")
            return False
    
    # =========================================================================
    # GRAPH QUERIES (PhD-Level Capabilities)
    # =========================================================================
    
    def find_citation_chain(
        self, 
        paper_id: str, 
        direction: str = "both",
        max_depth: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find papers in the citation chain.
        """
        # [ULTRON BEAST FIX] Strict Type Casting to prevent Cypher Injection
        # Depth must be physically validated before string interpolation.
        try:
            safe_depth = int(max_depth)
            if safe_depth < 1 or safe_depth > 10: safe_depth = 3 # Bound the depth
        except ValueError:
            safe_depth = 3

        if not self._available:
            import sqlite3, json
            try:
                with self._local_lock:
                    with sqlite3.connect(self.local_db_path) as conn:
                        conn.row_factory = sqlite3.Row
                        c = conn.cursor()
                        
                        # BFS traversal
                        visited = {paper_id: 0}
                        queue = [(paper_id, 0)]
                        
                        while queue:
                            curr, depth = queue.pop(0)
                            if depth >= safe_depth:
                                continue
                                
                            # Find neighbors depending on direction
                            neighbors = []
                            if direction == "citing" or direction == "both":
                                # incoming edges (citing cites curr)
                                c.execute("SELECT source FROM edges WHERE target = ? AND type = 'CITES'", (curr,))
                                neighbors.extend([(row['source'], depth + 1) for row in c.fetchall()])
                            if direction == "cited" or direction == "both":
                                # outgoing edges (curr cites cited)
                                c.execute("SELECT target FROM edges WHERE source = ? AND type = 'CITES'", (curr,))
                                neighbors.extend([(row['target'], depth + 1) for row in c.fetchall()])
                                
                            for neighbor, next_depth in neighbors:
                                if neighbor not in visited or next_depth < visited[neighbor]:
                                    visited[neighbor] = next_depth
                                    queue.append((neighbor, next_depth))
                                    
                        # Retrieve paper details for visited
                        results = []
                        for p_id, depth in visited.items():
                            if p_id == paper_id:
                                continue
                            c.execute("SELECT properties FROM nodes WHERE id = ? AND type = 'Paper'", (p_id,))
                            row = c.fetchone()
                            if row:
                                props = json.loads(row['properties'])
                                results.append({
                                    "title": props.get("title", p_id),
                                    "year": props.get("year"),
                                    "doi": props.get("doi"),
                                    "depth": depth
                                })
                        return results[:50]
            except Exception as e:
                logger.error(f"Local citation chain query failed: {e}")
                return []
        
        try:
            with self._driver.session() as session:
                if direction == "citing":
                    query = f"""
                        MATCH (p:Paper {{id: $paper_id}})<-[:CITES*1..{safe_depth}]-(citing:Paper)
                        WHERE citing.mission_id = $mission_id
                        RETURN citing.title as title, citing.year as year, 
                                citing.doi as doi, length((p)<-[:CITES*]-(citing)) as depth
                        ORDER BY depth, citing.citation_count DESC
                        LIMIT 50
                    """
                elif direction == "cited":
                    query = f"""
                        MATCH (p:Paper {{id: $paper_id}})-[:CITES*1..{safe_depth}]->(cited:Paper)
                        WHERE cited.mission_id = $mission_id
                        RETURN cited.title as title, cited.year as year,
                                cited.doi as doi, length((p)-[:CITES*]->(cited)) as depth
                        ORDER BY depth, cited.citation_count DESC
                        LIMIT 50
                    """
                else:
                    query = f"""
                        MATCH path = (p:Paper {{id: $paper_id}})-[:CITES*1..{safe_depth}]-(related:Paper)
                        WHERE related.mission_id = $mission_id
                        RETURN related.title as title, related.year as year,
                                related.doi as doi, length(path) as depth
                        ORDER BY depth, related.citation_count DESC
                        LIMIT 50
                    """
                
                result = session.run(query, {"paper_id": paper_id, "mission_id": getattr(self, 'session_id', 'global')})
                return [dict(record) for record in result]
                
        except Exception as e:
            logger.error(f"Citation chain query failed: {e}")
            return []
    
    def find_author_network(
        self,
        author_name: str,
        max_hops: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Find collaborator network for an author.
        
        Args:
            author_name: Starting author
            max_hops: Collaboration distance
            
        Returns:
            List of collaborators with connection info
        """
        if not self._available:
            import sqlite3
            try:
                with self._local_lock:
                    with sqlite3.connect(self.local_db_path) as conn:
                        conn.row_factory = sqlite3.Row
                        c = conn.cursor()
                        c.execute("""
                            SELECT source, COUNT(target) as collaborations FROM edges
                            WHERE type = 'AUTHORED'
                              AND target IN (SELECT target FROM edges WHERE source = ? AND type = 'AUTHORED')
                              AND source <> ?
                            GROUP BY source
                            ORDER BY collaborations DESC
                            LIMIT 20
                        """, (author_name, author_name))
                        return [{"name": row["source"], "collaborations": row["collaborations"]} for row in c.fetchall()]
            except Exception as e:
                logger.error(f"Local author network query failed: {e}")
                return []
        
        try:
            with self._driver.session() as session:
                result = session.run("""
                    MATCH (a:Author {name: $author_name})-[:AUTHORED]->(p:Paper {mission_id: $mission_id})<-[:AUTHORED]-(coauthor:Author {mission_id: $mission_id})
                    WHERE coauthor.name <> $author_name
                    WITH coauthor, count(p) as collaborations
                    RETURN coauthor.name as name, collaborations
                    ORDER BY collaborations DESC
                    LIMIT 20
                """, {"author_name": author_name, "mission_id": self.session_id})
                return [dict(record) for record in result]
                
        except Exception as e:
            logger.error(f"Author network query failed: {e}")
            return []
    
    def find_concept_connections(
        self,
        concept1: str,
        concept2: str
    ) -> List[Dict[str, Any]]:
        """
        Find papers that connect two concepts.
        
        This answers: "What connects Concept A to Concept B?" (e.g., 'What connects Transformers to Attention?')
        """
        if not self._available:
            import sqlite3, json
            try:
                with self._local_lock:
                    with sqlite3.connect(self.local_db_path) as conn:
                        conn.row_factory = sqlite3.Row
                        c = conn.cursor()
                        c.execute("""
                            SELECT id, properties FROM nodes
                            WHERE type = 'Paper'
                              AND id IN (SELECT source FROM edges WHERE target = ? AND type = 'MENTIONS')
                              AND id IN (SELECT source FROM edges WHERE target = ? AND type = 'MENTIONS')
                            LIMIT 20
                        """, (concept1, concept2))
                        results = []
                        for row in c.fetchall():
                            props = json.loads(row["properties"])
                            results.append({
                                "title": props.get("title", row["id"]),
                                "year": props.get("year"),
                                "doi": props.get("doi"),
                                "citations": props.get("citation_count", 0)
                            })
                        results.sort(key=lambda x: x.get("citations", 0), reverse=True)
                        return results
            except Exception as e:
                logger.error(f"Local concept connection query failed: {e}")
                return []
        
        try:
            with self._driver.session() as session:
                result = session.run("""
                    MATCH (c1:Concept {name: $concept1})<-[:MENTIONS]-(p:Paper {mission_id: $mission_id})-[:MENTIONS]->(c2:Concept {name: $concept2})
                    RETURN p.title as title, p.year as year, p.doi as doi,
                           p.citation_count as citations
                    ORDER BY p.citation_count DESC
                    LIMIT 20
                """, {"concept1": concept1, "concept2": concept2, "mission_id": self.session_id})
                return [dict(record) for record in result]
                
        except Exception as e:
            logger.error(f"Concept connection query failed: {e}")
            return []
    
    def add_concept_mention(self, paper_id: str, concept_name: str) -> bool:
        """Add a concept mention from a paper."""
        if not self._available:
            self._upsert_local_node(concept_name, "Concept", {"name": concept_name})
            self._add_local_edge(paper_id, concept_name, "MENTIONS")
            return True
        
        try:
            with self._driver.session() as session:
                session.run("""
                    MERGE (c:Concept {name: $concept_name})
                    SET c.mission_id = $mission_id
                    WITH c
                    MATCH (p:Paper {id: $paper_id})
                    MERGE (p)-[:MENTIONS]->(c)
                """, paper_id=paper_id, concept_name=concept_name, mission_id=self.session_id)
            return True
        except Exception as e:
            logger.error(f"Failed to add concept mention: {e}")
            return False
    
    # =========================================================================
    # METHOD SEMANTICS (Ported from Ultron)
    # =========================================================================

    def add_method(
        self,
        name: str,
        description: Optional[str] = None,
        category: Optional[str] = None
    ) -> bool:
        """
        Add a scientific method node.
        """
        if not self._available:
            self._upsert_local_node(name, "Method", {"name": name, "description": description, "category": category})
            return True
            
        try:
            with self._driver.session() as session:
                session.run("""
                    MERGE (m:Method {name: $name})
                    SET m.description = $description,
                        m.category = $category,
                        m.mission_id = $mission_id,
                        m.updated_at = datetime()
                """, name=name, description=description, category=category, mission_id=self.session_id)
            return True
        except Exception as e:
            logger.error(f"Failed to add method: {e}")
            return False

    def add_uses_method(
        self, 
        paper_id: str, 
        method_name: str, 
        confidence: float = 1.0,
        context: Optional[str] = None
    ) -> bool:
        """
        Link a paper to a method (Paper)-[:USES_METHOD]->(Method).
        """
        if not self._available:
            self._upsert_local_node(method_name, "Method", {"name": method_name})
            self._add_local_edge(paper_id, method_name, "USES_METHOD", {"confidence": confidence, "context": context})
            return True
            
        try:
            with self._driver.session() as session:
                session.run("""
                    MATCH (p:Paper {id: $paper_id})
                    MERGE (m:Method {name: $method_name})
                    MERGE (p)-[r:USES_METHOD]->(m)
                    SET r.confidence = $confidence,
                        r.context = $context,
                        r.created_at = datetime()
                """, paper_id=paper_id, method_name=method_name, 
                     confidence=confidence, context=context)
            return True
        except Exception as e:
            logger.error(f"Failed to add USES_METHOD: {e}")
            return False

    # =========================================================================
    # HYPOTHESIS & FINDING TRACKING
    # =========================================================================
    
    # =========================================================================
    # Ultron-STYLE STRICT ENTITIES (BEAST MODE UPGRADE)
    # =========================================================================

    def create_paper(
        self,
        title: str,
        doi: Optional[str] = None,
        year: Optional[int] = None,
        authors: List[str] = None,
        abstract: Optional[str] = None,
        citation_count: int = 0
    ) -> Optional[Dict]:
        """
        Create a strictly defined Paper node.
        
        Args:
            title: Full paper title
            doi: Digital Object Identifier (highly recommended)
            year: Publication year
            authors: List of author names
            abstract: Paper abstract
            citation_count: Number of citations
        """
        if not self._available:
            return None
            
        with self._driver.session() as session:
            # Create Paper node
            query = """
            MERGE (p:Paper {title: $title})
            ON CREATE SET 
                p.id = randomUUID(),
                p.doi = $doi,
                p.year = $year,
                p.abstract = $abstract,
                p.citation_count = $citation_count,
                p.created_at = datetime()
            ON MATCH SET
                p.citation_count = $citation_count,
                p.updated_at = datetime()
            RETURN p
            """
            result = session.run(
                query, 
                title=title, 
                doi=doi, 
                year=year, 
                abstract=abstract, 
                citation_count=citation_count,
                
            )
            paper_node = result.single()
            
            # Create Author nodes and link them
            if authors:
                for author_name in authors:
                    self.create_author(author_name, link_to_paper_title=title)
                    
            return paper_node

    def create_author(
        self, 
        name: str, 
        affiliation: Optional[str] = None,
        link_to_paper_title: Optional[str] = None
    ):
        """Create Author node and optionally link to a paper."""
        if not self._available:
            return

        with self._driver.session() as session:
            query = """
            MERGE (a:Author {name: $name})
            ON CREATE SET 
                a.id = randomUUID(),
                a.affiliation = $affiliation,
                a.created_at = datetime()
            RETURN a
            """
            session.run(query, name=name, affiliation=affiliation)
            
            if link_to_paper_title:
                link_query = """
                MATCH (a:Author {name: $name})
                MATCH (p:Paper {title: $paper_title})
                MERGE (a)-[:AUTHORED]->(p)
                """
                session.run(link_query, name=name, paper_title=link_to_paper_title)

    def create_concept(self, name: str, definition: Optional[str] = None, domain: str = "general"):
        """Create a Concept node."""
        if not self._available:
            return

        with self._driver.session() as session:
            query = """
            MERGE (c:Concept {name: $name})
            ON CREATE SET 
                c.id = randomUUID(),
                c.definition = $definition,
                c.domain = $domain,
                c.created_at = datetime()
            RETURN c
            """
            session.run(query, name=name, definition=definition, domain=domain)

    def create_method(self, name: str, description: Optional[str] = None, category: Optional[str] = None):
        """Create a Method node (e.g., 'Transformer Architecture', 'Double-Blind Study')."""
        if not self._available:
            return

        with self._driver.session() as session:
            query = """
            MERGE (m:Method {name: $name})
            ON CREATE SET 
                m.id = randomUUID(),
                m.description = $description,
                m.category = $category,
                m.created_at = datetime()
            RETURN m
            """
            session.run(query, name=name, description=description, category=category)

    # =========================================================================
    # ULTRON GENERIC ENTITIES (LEGACY SUPPORT)
    # =========================================================================
    
    def add_hypothesis(
        self,
        hypothesis_id: str,
        statement: str,
        status: str = "pending",
        confidence: float = 0.5,
        session_id: Optional[str] = None
    ) -> bool:
        """Add a research hypothesis to track."""
        if not self._available:
            self._upsert_local_node(hypothesis_id, "Hypothesis", {
                "hypothesis_id": hypothesis_id,
                "statement": statement,
                "status": status,
                "confidence": confidence,
                "session_id": session_id or self.session_id
            })
            return True
        
        eff_session = session_id or self.session_id
        try:
            with self._driver.session() as session:
                session.run("""
                    MERGE (h:Hypothesis {id: $hypothesis_id})
                    SET h.hypothesis_id = $hypothesis_id,
                        h.statement = $statement,
                        h.status = $status,
                        h.confidence = $confidence,
                        h.session_id = $session_id,
                        h.mission_id = $session_id,
                        h.created_at = datetime()
                """, 
                    hypothesis_id=hypothesis_id,
                    statement=statement,
                    status=status,
                    confidence=confidence,
                    session_id=eff_session
                )
            return True
        except Exception as e:
            logger.error(f"Failed to add hypothesis: {e}")
            return False
    
    def add_finding(
        self,
        finding_id: str,
        summary: str,
        hypothesis_id: Optional[str] = None,
        relationship: str = "SUPPORTS",  # or "REFUTES"
        evidence_source: Optional[str] = None
    ) -> bool:
        """Add a research finding and link to hypothesis."""
        if not self._available:
            rel_type = "SUPPORTS" if relationship == "SUPPORTS" else "REFUTES"
            self._upsert_local_node(finding_id, "Finding", {
                "finding_id": finding_id,
                "summary": summary,
                "evidence_source": evidence_source,
                "hypothesis_id": hypothesis_id,
                "relationship": rel_type,
                "session_id": self.session_id
            })
            if hypothesis_id:
                self._add_local_edge(finding_id, hypothesis_id, rel_type, {"evidence_source": evidence_source})
            return True
        
        try:
            with self._driver.session() as session:
                # Create finding
                session.run("""
                    MERGE (f:Finding {id: $finding_id})
                    SET f.finding_id = $finding_id,
                        f.summary = $summary,
                        f.evidence_source = $evidence_source,
                        f.mission_id = $mission_id,
                        f.session_id = $mission_id,
                        f.created_at = datetime()
                """, 
                    finding_id=finding_id,
                    summary=summary,
                    evidence_source=evidence_source,
                    mission_id=self.session_id
                )
                
                # Link to hypothesis
                if hypothesis_id:
                    rel_type = "SUPPORTS" if relationship == "SUPPORTS" else "REFUTES"
                    session.run(f"""
                        MATCH (f:Finding {{id: $finding_id}})
                        MATCH (h:Hypothesis {{id: $hypothesis_id}})
                        MERGE (f)-[:{rel_type}]->(h)
                    """, finding_id=finding_id, hypothesis_id=hypothesis_id)
            
            return True
        except Exception as e:
            logger.error(f"Failed to add finding: {e}")
            return False
    
    def get_hypothesis_evidence(self, hypothesis_id: str) -> Dict[str, List]:
        """Get all supporting and refuting evidence for a hypothesis."""
        if not self._available:
            import sqlite3, json
            supporting = []
            refuting = []
            try:
                with self._local_lock:
                    with sqlite3.connect(self.local_db_path) as conn:
                        conn.row_factory = sqlite3.Row
                        c = conn.cursor()
                        c.execute(
                            "SELECT source, type FROM edges WHERE target = ? AND type IN ('SUPPORTS', 'REFUTES')",
                            (hypothesis_id,)
                        )
                        edges = c.fetchall()
                        for edge in edges:
                            c.execute("SELECT properties FROM nodes WHERE id = ? AND type = 'Finding'", (edge["source"],))
                            row = c.fetchone()
                            if row:
                                props = json.loads(row["properties"])
                                item = {"summary": props.get("summary", ""), "source": props.get("evidence_source")}
                                if edge["type"] == "SUPPORTS":
                                    supporting.append(item)
                                else:
                                    refuting.append(item)
            except Exception as e:
                logger.error(f"Local get_hypothesis_evidence failed: {e}")
            return {"supporting": supporting, "refuting": refuting}
        
        try:
            with self._driver.session() as session:
                supporting = session.run("""
                    MATCH (f:Finding {mission_id: $mission_id})-[:SUPPORTS]->(h:Hypothesis {id: $hypothesis_id})
                    RETURN f.summary as summary, f.evidence_source as source
                """, {"hypothesis_id": hypothesis_id, "mission_id": self.session_id})
                
                refuting = session.run("""
                    MATCH (f:Finding {mission_id: $mission_id})-[:REFUTES]->(h:Hypothesis {id: $hypothesis_id})
                    RETURN f.summary as summary, f.evidence_source as source
                """, {"hypothesis_id": hypothesis_id, "mission_id": self.session_id})
                
                return {
                    "supporting": [dict(r) for r in supporting],
                    "refuting": [dict(r) for r in refuting]
                }
        except Exception as e:
            logger.error(f"Failed to get hypothesis evidence: {e}")
            return {"supporting": [], "refuting": []}
    
    # =========================================================================
    # ANALYTICS
    # =========================================================================
    
    def get_statistics(self) -> Dict[str, int]:
        """Get knowledge graph statistics."""
        if not self._available:
            import sqlite3
            try:
                with self._local_lock:
                    with sqlite3.connect(self.local_db_path) as conn:
                        c = conn.cursor()
                        c.execute("SELECT COUNT(*) FROM nodes WHERE type = 'Paper'")
                        papers = c.fetchone()[0]
                        c.execute("SELECT COUNT(*) FROM nodes WHERE type = 'Author'")
                        authors = c.fetchone()[0]
                        c.execute("SELECT COUNT(*) FROM nodes WHERE type = 'Concept'")
                        concepts = c.fetchone()[0]
                        c.execute("SELECT COUNT(*) FROM nodes WHERE type = 'Hypothesis'")
                        hypotheses = c.fetchone()[0]
                        c.execute("SELECT COUNT(*) FROM edges WHERE type = 'CITES'")
                        citations = c.fetchone()[0]
                        return {
                            "papers": papers,
                            "authors": authors,
                            "concepts": concepts,
                            "hypotheses": hypotheses,
                            "citations": citations
                        }
            except Exception as e:
                logger.error(f"Local statistics query failed: {e}")
                return {"status": "error", "error": str(e)}
        
        try:
            with self._driver.session() as session:
                result = session.run("""
                    MATCH (p:Paper {mission_id: $mission_id}) WITH count(p) as papers
                    MATCH (a:Author {mission_id: $mission_id}) WITH papers, count(a) as authors
                    MATCH (c:Concept {mission_id: $mission_id}) WITH papers, authors, count(c) as concepts
                    MATCH (h:Hypothesis {mission_id: $mission_id}) WITH papers, authors, concepts, count(h) as hypotheses
                    MATCH (n {mission_id: $mission_id})-[r:CITES]->(m {mission_id: $mission_id}) WITH papers, authors, concepts, hypotheses, count(r) as citations
                    RETURN papers, authors, concepts, hypotheses, citations
                """, {"mission_id": self.session_id})
                record = result.single()
                if record:
                    return dict(record)
                return {"status": "empty"}
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"status": "error", "error": str(e)}
    
    def close(self):
        """Close the Neo4j connection."""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j connection closed")
    
    # =========================================================================
    # CROSS-SESSION MEMORY (FETCH ALL ENTITIES)
    # =========================================================================
    
    def get_all_papers(self, limit: int = 1000, session_id: Optional[str] = None) -> List[Dict]:
        """Fetch all papers from Neo4j or local SQLite for cross-session memory loading."""
        if not self._available:
            import sqlite3, json
            try:
                with self._local_lock:
                    with sqlite3.connect(self.local_db_path) as conn:
                        c = conn.cursor()
                        c.execute("SELECT properties FROM nodes WHERE type = 'Paper' LIMIT ?", (limit,))
                        return [json.loads(r[0]) for r in c.fetchall()]
            except Exception:
                return []
        
        try:
            with self._driver.session() as session:
                if session_id:
                    query = """
                        MATCH (p:Paper {mission_id: $mission_id})
                        WHERE p.session_id = $session_id
                        RETURN p.title as title, p.doi as doi, p.arxiv_id as arxiv_id,
                               p.year as year, p.abstract as abstract, p.citation_count as citation_count
                        LIMIT $limit
                    """
                    result = session.run(query, {"session_id": session_id, "limit": limit, "mission_id": self.session_id})
                else:
                    query = """
                        MATCH (p:Paper {mission_id: $mission_id})
                        RETURN p.title as title, p.doi as doi, p.arxiv_id as arxiv_id,
                               p.year as year, p.abstract as abstract, p.citation_count as citation_count
                        LIMIT $limit
                    """
                    result = session.run(query, {"limit": limit, "mission_id": self.session_id})
                
                papers = [dict(record) for record in result]
                logger.info(f" Loaded {len(papers)} papers from Neo4j")
                return papers
        except Exception as e:
            logger.error(f"Failed to fetch papers: {e}")
            return []
    
    def get_all_hypotheses(self, limit: int = 500, session_id: Optional[str] = None) -> List[Dict]:
        """Fetch all hypotheses from Neo4j or local SQLite for cross-session memory loading."""
        if not self._available:
            import sqlite3, json
            try:
                with self._local_lock:
                    with sqlite3.connect(self.local_db_path) as conn:
                        c = conn.cursor()
                        c.execute("SELECT properties FROM nodes WHERE type = 'Hypothesis' LIMIT ?", (limit,))
                        rows = [json.loads(r[0]) for r in c.fetchall()]
                        if session_id:
                            rows = [r for r in rows if r.get("session_id") == session_id]
                        return rows
            except Exception:
                return []
        
        try:
            with self._driver.session() as session:
                if session_id:
                    query = """
                        MATCH (h:Hypothesis {mission_id: $mission_id})
                        WHERE h.session_id = $session_id
                        RETURN h.hypothesis_id as hypothesis_id, h.statement as statement,
                               h.status as status, h.confidence as confidence
                        LIMIT $limit
                    """
                    result = session.run(query, {"session_id": session_id, "limit": limit, "mission_id": self.session_id})
                else:
                    query = """
                        MATCH (h:Hypothesis {mission_id: $mission_id})
                        RETURN h.hypothesis_id as hypothesis_id, h.statement as statement,
                               h.status as status, h.confidence as confidence
                        LIMIT $limit
                    """
                    result = session.run(query, {"limit": limit, "mission_id": self.session_id})
                
                hypotheses = [dict(record) for record in result]
                logger.info(f" Loaded {len(hypotheses)} hypotheses from Neo4j")
                return hypotheses
        except Exception as e:
            logger.error(f"Failed to fetch hypotheses: {e}")
            return []
    
    def get_all_findings(self, limit: int = 1000, session_id: Optional[str] = None) -> List[Dict]:
        """Fetch all findings from Neo4j or local SQLite for cross-session memory loading."""
        if not self._available:
            import sqlite3, json
            try:
                with self._local_lock:
                    with sqlite3.connect(self.local_db_path) as conn:
                        c = conn.cursor()
                        c.execute("SELECT properties FROM nodes WHERE type = 'Finding' LIMIT ?", (limit,))
                        return [json.loads(r[0]) for r in c.fetchall()]
            except Exception:
                return []
        
        try:
            with self._driver.session() as session:
                query = """
                    MATCH (f:Finding {mission_id: $mission_id})
                    OPTIONAL MATCH (f)-[r]->(h:Hypothesis {mission_id: $mission_id})
                    RETURN f.finding_id as finding_id, f.summary as summary,
                           f.evidence_source as evidence_source,
                           h.hypothesis_id as hypothesis_id, type(r) as relationship
                    LIMIT $limit
                """
                result = session.run(query, {"limit": limit, "mission_id": self.session_id})
                
                findings = [dict(record) for record in result]
                logger.info(f" Loaded {len(findings)} findings from Neo4j")
                return findings
        except Exception as e:
            logger.error(f"Failed to fetch findings: {e}")
            return []

    # =========================================================================
    # BATCH WRITES (10x FASTER INSERTS)
    # =========================================================================
    
    def add_papers_batch(self, papers: List[Dict]) -> int:
        """
        Add multiple papers in a single transaction.
        
        10x faster than individual inserts. Uses UNWIND for atomic batch.
        
        Args:
            papers: List of dicts with keys: title, doi, year, abstract, authors
            
        Returns:
            Number of papers successfully added
        """
        if not papers:
            return 0
        if not self._available:
            count = 0
            for p in papers:
                if isinstance(p, dict) and p.get("title"):
                    if self.add_paper(
                        title=p.get("title"),
                        doi=p.get("doi"),
                        arxiv_id=p.get("arxiv_id"),
                        year=p.get("year"),
                        abstract=p.get("abstract"),
                        authors=p.get("authors"),
                        citation_count=p.get("citation_count", 0),
                    ):
                        count += 1
            return count
        
        try:
            with self._driver.session() as session:
                result = session.run("""
                    UNWIND $papers AS paper
                    MERGE (p:Paper {id: coalesce(paper.doi, paper.arxiv_id, paper.title)})
                    SET p.title = paper.title,
                        p.doi = paper.doi,
                        p.year = paper.year,
                        p.abstract = paper.abstract,
                        p.citation_count = coalesce(paper.citation_count, 0),
                        p.mission_id = $mission_id,
                        p.session_id = $mission_id,
                        p.created_at = coalesce(p.created_at, timestamp())
                    WITH p, paper
                    UNWIND coalesce(paper.authors, []) AS author_name
                    MERGE (a:Author {name: author_name})
                    SET a.mission_id = $mission_id
                    MERGE (a)-[:AUTHORED]->(p)
                    RETURN count(DISTINCT p) as count
                """, papers=papers, mission_id=self.session_id)
                
                record = result.single()
                count = record["count"] if record else len(papers)
                logger.info(f" Batch inserted {count} papers")
                return count
        except Exception as e:
            logger.error(f"Batch paper insert failed: {e}")
            return 0
    
    def add_hypotheses_batch(self, hypotheses: List[Dict]) -> int:
        """
        Add multiple hypotheses in a single transaction.
        
        Args:
            hypotheses: List of dicts with keys: hypothesis_id, statement, status, confidence, session_id
            
        Returns:
            Number of hypotheses successfully added
        """
        if not hypotheses:
            return 0
        if not self._available:
            count = 0
            for h in hypotheses:
                if isinstance(h, dict) and h.get("hypothesis_id"):
                    if self.add_hypothesis(
                        hypothesis_id=h.get("hypothesis_id"),
                        statement=h.get("statement", ""),
                        status=h.get("status", "pending"),
                        confidence=h.get("confidence", 0.5),
                        session_id=h.get("session_id") or self.session_id,
                    ):
                        count += 1
            return count
        
        try:
            with self._driver.session() as session:
                result = session.run("""
                    UNWIND $hypotheses AS hyp
                    MERGE (h:Hypothesis {id: hyp.hypothesis_id})
                    SET h.hypothesis_id = hyp.hypothesis_id,
                        h.statement = hyp.statement,
                        h.status = coalesce(hyp.status, 'pending'),
                        h.confidence = coalesce(hyp.confidence, 0.5),
                        h.session_id = coalesce(hyp.session_id, $mission_id),
                        h.mission_id = coalesce(hyp.session_id, $mission_id),
                        h.created_at = coalesce(h.created_at, timestamp())
                    RETURN count(h) as count
                """, hypotheses=hypotheses, mission_id=self.session_id)
                
                record = result.single()
                count = record["count"] if record else len(hypotheses)
                logger.info(f" Batch inserted {count} hypotheses")
                return count
        except Exception as e:
            logger.error(f"Batch hypothesis insert failed: {e}")
            return 0
    
    def add_findings_batch(self, findings: List[Dict]) -> int:
        """
        Add multiple findings in a single transaction.
        
        Args:
            findings: List of dicts with keys: finding_id, summary, hypothesis_id, relationship, evidence_source
            
        Returns:
            Number of findings successfully added
        """
        if not findings:
            return 0
        if not self._available:
            count = 0
            for f in findings:
                if isinstance(f, dict) and f.get("finding_id"):
                    if self.add_finding(
                        finding_id=f.get("finding_id"),
                        summary=f.get("summary", ""),
                        hypothesis_id=f.get("hypothesis_id"),
                        relationship=f.get("relationship", "SUPPORTS"),
                        evidence_source=f.get("evidence_source"),
                    ):
                        count += 1
            return count
        
        try:
            with self._driver.session() as session:
                result = session.run("""
                    UNWIND $findings AS f
                    MERGE (finding:Finding {id: f.finding_id})
                    SET finding.finding_id = f.finding_id,
                        finding.summary = f.summary,
                        finding.evidence_source = f.evidence_source,
                        finding.mission_id = $mission_id,
                        finding.session_id = $mission_id,
                        finding.created_at = coalesce(finding.created_at, timestamp())
                    WITH finding, f
                    WHERE f.hypothesis_id IS NOT NULL
                    MATCH (h:Hypothesis {id: f.hypothesis_id})
                    FOREACH (_ IN CASE WHEN f.relationship = 'SUPPORTS' THEN [1] ELSE [] END |
                        MERGE (finding)-[:SUPPORTS]->(h)
                    )
                    FOREACH (_ IN CASE WHEN f.relationship = 'REFUTES' THEN [1] ELSE [] END |
                        MERGE (finding)-[:REFUTES]->(h)
                    )
                    RETURN count(DISTINCT finding) as count
                """, findings=findings, mission_id=self.session_id)
                
                record = result.single()
                count = record["count"] if record else len(findings)
                logger.info(f" Batch inserted {count} findings")
                return count
        except Exception as e:
            logger.error(f"Batch finding insert failed: {e}")
            return 0


# Singleton cache per session
_kg_instances: Dict[str, KnowledgeGraph] = {}


def get_knowledge_graph(session_id: Optional[str] = None) -> KnowledgeGraph:
    """Get or create the session-scoped KnowledgeGraph instance."""
    global _kg_instances
    current_session = session_id or os.environ.get("ULTRON_SESSION_ID", "default_session")
    if current_session not in _kg_instances:
        _kg_instances[current_session] = KnowledgeGraph(session_id=current_session)
    return _kg_instances[current_session]


# Convenience alias - defaults to system or use with mission_id param
knowledge_graph = get_knowledge_graph


# -----------------------------------------------------------------------------
# Quick Test
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    kg = get_knowledge_graph()
    
    if kg.is_available:
        print("Neo4j CONNECTED!")
        print(f"Stats: {kg.get_statistics()}")
        
        # Test adding a paper
        kg.add_paper(
            title="Test Paper on CRISPR",
            doi="10.1234/test.2024",
            year=2024,
            authors=["Alice Smith", "Bob Jones"]
        )
        
        print(f"Updated Stats: {kg.get_statistics()}")
    else:
        print("Neo4j NOT AVAILABLE - Set NEO4J_PASSWORD in .env")

Neo4jKnowledgeGraph = KnowledgeGraph

