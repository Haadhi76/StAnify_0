"""
SQLite Persistence Layer for StAnify Pipeline

Stores run metadata, panel URIs, critiques, and verdicts for historical tracking
and re-export capabilities.
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from contextlib import contextmanager

from .manifest_contracts import RunManifest
from .image_continuity_evaluator import ImageContinuityResult

logger = logging.getLogger(__name__)


@dataclass
class RunRecord:
    """Database record for a pipeline run."""
    run_id: str
    created_at: datetime
    user_id: Optional[str]
    year: str
    subject: str
    user_prompt: str
    topic_id: str
    topic_title: str
    
    # File paths
    pdf_path: Optional[str]
    pptx_path: Optional[str]
    manifest_path: Optional[str]
    
    # Panel information
    panel_count: int
    panel_uris: List[str]  # JSON serialized list
    
    # Evaluation results
    overall_critique_verdict: str
    overall_critique_score: float
    image_continuity_verdict: str
    image_continuity_score: float
    
    # Metadata
    model_notes: str
    status: str  # "completed", "failed", "in_progress"


class StAnifyDatabase:
    """SQLite database interface for StAnify pipeline runs."""
    
    def __init__(self, db_path: str = "stanify_runs.db"):
        """
        Initialize the database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._init_database()
        logger.info(f"StAnify database initialized: {self.db_path}")
    
    def _init_database(self):
        """Create database tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Main runs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT,
                    year TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    user_prompt TEXT NOT NULL,
                    topic_id TEXT NOT NULL,
                    topic_title TEXT NOT NULL,
                    
                    pdf_path TEXT,
                    pptx_path TEXT,
                    manifest_path TEXT,
                    
                    panel_count INTEGER DEFAULT 0,
                    panel_uris TEXT,  -- JSON array
                    
                    overall_critique_verdict TEXT,
                    overall_critique_score REAL,
                    image_continuity_verdict TEXT,
                    image_continuity_score REAL,
                    
                    model_notes TEXT,
                    status TEXT DEFAULT 'in_progress'
                )
            """)
            
            # Panel details table (for detailed tracking)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS panels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    panel_index INTEGER NOT NULL,
                    chunk_id TEXT NOT NULL,
                    image_uri TEXT,
                    caption TEXT,
                    positive_prompt TEXT,
                    clip_score REAL,
                    
                    FOREIGN KEY (run_id) REFERENCES runs (run_id),
                    UNIQUE(run_id, panel_index)
                )
            """)
            
            # Critique details table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS critiques (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    critique_type TEXT NOT NULL,  -- 'overall', 'image_continuity'
                    verdict TEXT NOT NULL,
                    score REAL,
                    recommendations TEXT,  -- JSON array
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (run_id) REFERENCES runs (run_id)
                )
            """)
            
            # Index for faster queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs (created_at DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_runs_status ON runs (status)")
            
            conn.commit()
            logger.debug("Database tables initialized successfully")
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(
            self.db_path, 
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()
    
    def create_run(
        self, 
        run_id: str, 
        year: str, 
        subject: str, 
        user_prompt: str,
        topic_id: str,
        topic_title: str,
        user_id: Optional[str] = None
    ) -> None:
        """
        Create a new run record in the database.
        
        Args:
            run_id: Unique identifier for the run
            year: Target year level
            subject: Subject area
            user_prompt: Original user prompt
            topic_id: Curriculum topic ID
            topic_title: Curriculum topic title
            user_id: Optional user identifier
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO runs (
                    run_id, user_id, year, subject, user_prompt, 
                    topic_id, topic_title, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'in_progress')
            """, (run_id, user_id, year, subject, user_prompt, topic_id, topic_title))
            conn.commit()
            
        logger.info(f"Created run record: {run_id}")
    
    def update_run_files(
        self, 
        run_id: str, 
        manifest_path: str,
        pdf_path: Optional[str] = None,
        pptx_path: Optional[str] = None
    ) -> None:
        """Update file paths for a run."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE runs 
                SET manifest_path = ?, pdf_path = ?, pptx_path = ?
                WHERE run_id = ?
            """, (manifest_path, pdf_path, pptx_path, run_id))
            conn.commit()
            
        logger.debug(f"Updated file paths for run: {run_id}")
    
    def update_run_panels(
        self, 
        run_id: str, 
        panel_uris: List[str],
        panel_details: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        Update panel information for a run.
        
        Args:
            run_id: Run identifier
            panel_uris: List of image URIs
            panel_details: Optional detailed panel information
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Update main run record
            cursor.execute("""
                UPDATE runs 
                SET panel_count = ?, panel_uris = ?
                WHERE run_id = ?
            """, (len(panel_uris), json.dumps(panel_uris), run_id))
            
            # Insert detailed panel records if provided
            if panel_details:
                cursor.execute("DELETE FROM panels WHERE run_id = ?", (run_id,))
                for i, panel in enumerate(panel_details):
                    cursor.execute("""
                        INSERT INTO panels (
                            run_id, panel_index, chunk_id, image_uri, 
                            caption, positive_prompt, clip_score
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        run_id, i, panel.get('chunk_id', ''), 
                        panel.get('image_uri', ''), panel.get('caption', ''),
                        panel.get('positive_prompt', ''), panel.get('clip_score', 0.0)
                    ))
            
            conn.commit()
            
        logger.debug(f"Updated panels for run: {run_id} ({len(panel_uris)} panels)")
    
    def store_critique(
        self, 
        run_id: str, 
        critique_type: str,
        verdict: str, 
        score: float,
        recommendations: List[str]
    ) -> None:
        """
        Store critique results for a run.
        
        Args:
            run_id: Run identifier
            critique_type: Type of critique ('overall', 'image_continuity')
            verdict: Critique verdict
            score: Numerical score
            recommendations: List of recommendations
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Store in critiques table
            cursor.execute("""
                INSERT INTO critiques (
                    run_id, critique_type, verdict, score, recommendations
                ) VALUES (?, ?, ?, ?, ?)
            """, (run_id, critique_type, verdict, score, json.dumps(recommendations)))
            
            # Update main runs table
            if critique_type == 'overall':
                cursor.execute("""
                    UPDATE runs 
                    SET overall_critique_verdict = ?, overall_critique_score = ?
                    WHERE run_id = ?
                """, (verdict, score, run_id))
            elif critique_type == 'image_continuity':
                cursor.execute("""
                    UPDATE runs 
                    SET image_continuity_verdict = ?, image_continuity_score = ?
                    WHERE run_id = ?
                """, (verdict, score, run_id))
            
            conn.commit()
            
        logger.debug(f"Stored {critique_type} critique for run: {run_id}")
    
    def complete_run(self, run_id: str, status: str = "completed", model_notes: str = "") -> None:
        """Mark a run as completed."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE runs 
                SET status = ?, model_notes = ?
                WHERE run_id = ?
            """, (status, model_notes, run_id))
            conn.commit()
            
        logger.info(f"Completed run: {run_id} with status: {status}")
    
    def get_run(self, run_id: str) -> Optional[RunRecord]:
        """Retrieve a run record by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_run_record(row)
            return None
    
    def list_runs(
        self, 
        limit: int = 50, 
        status: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[RunRecord]:
        """
        List recent runs with optional filtering.
        
        Args:
            limit: Maximum number of runs to return
            status: Filter by status ('completed', 'failed', 'in_progress')
            user_id: Filter by user ID
            
        Returns:
            List of RunRecord objects
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM runs WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_run_record(row) for row in rows]
    
    def get_run_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total runs
            cursor.execute("SELECT COUNT(*) FROM runs")
            total_runs = cursor.fetchone()[0]
            
            # Status breakdown
            cursor.execute("""
                SELECT status, COUNT(*) 
                FROM runs 
                GROUP BY status
            """)
            status_counts = dict(cursor.fetchall())
            
            # Recent activity (last 24 hours)
            cursor.execute("""
                SELECT COUNT(*) 
                FROM runs 
                WHERE created_at > datetime('now', '-1 day')
            """)
            recent_runs = cursor.fetchone()[0]
            
            # Average scores
            cursor.execute("""
                SELECT 
                    AVG(overall_critique_score) as avg_critique,
                    AVG(image_continuity_score) as avg_continuity
                FROM runs 
                WHERE status = 'completed'
            """)
            row = cursor.fetchone()
            avg_critique = row[0] if row[0] else 0.0
            avg_continuity = row[1] if row[1] else 0.0
            
            return {
                'total_runs': total_runs,
                'status_counts': status_counts,
                'recent_runs_24h': recent_runs,
                'avg_critique_score': avg_critique,
                'avg_continuity_score': avg_continuity
            }
    
    def delete_run(self, run_id: str) -> bool:
        """
        Delete a run and all associated records.
        
        Args:
            run_id: Run identifier
            
        Returns:
            True if run was deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if run exists
            cursor.execute("SELECT 1 FROM runs WHERE run_id = ?", (run_id,))
            if not cursor.fetchone():
                return False
            
            # Delete from all tables (cascading delete)
            cursor.execute("DELETE FROM critiques WHERE run_id = ?", (run_id,))
            cursor.execute("DELETE FROM panels WHERE run_id = ?", (run_id,))
            cursor.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
            
            conn.commit()
            
        logger.info(f"Deleted run: {run_id}")
        return True
    
    def _row_to_run_record(self, row: sqlite3.Row) -> RunRecord:
        """Convert database row to RunRecord."""
        return RunRecord(
            run_id=row['run_id'],
            created_at=row['created_at'],
            user_id=row['user_id'],
            year=row['year'],
            subject=row['subject'],
            user_prompt=row['user_prompt'],
            topic_id=row['topic_id'],
            topic_title=row['topic_title'],
            pdf_path=row['pdf_path'],
            pptx_path=row['pptx_path'],
            manifest_path=row['manifest_path'],
            panel_count=row['panel_count'],
            panel_uris=json.loads(row['panel_uris']) if row['panel_uris'] else [],
            overall_critique_verdict=row['overall_critique_verdict'] or '',
            overall_critique_score=row['overall_critique_score'] or 0.0,
            image_continuity_verdict=row['image_continuity_verdict'] or '',
            image_continuity_score=row['image_continuity_score'] or 0.0,
            model_notes=row['model_notes'] or '',
            status=row['status']
        )


# Global database instance
_db_instance: Optional[StAnifyDatabase] = None


def get_database(db_path: str = "stanify_runs.db") -> StAnifyDatabase:
    """Get or create the global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = StAnifyDatabase(db_path)
    return _db_instance


def store_manifest_run(
    manifest: RunManifest, 
    result_paths: Dict[str, str],
    user_prompt: str,
    image_continuity_result: Optional[ImageContinuityResult] = None
) -> None:
    """
    Store a completed manifest run in the database.
    
    Args:
        manifest: The generated manifest
        result_paths: Dictionary with 'pdf', 'pptx', 'manifest' paths
        user_prompt: The original user prompt
        image_continuity_result: Optional image continuity evaluation results
    """
    db = get_database()
    
    # Extract basic information
    run_id = manifest.task.run_id
    task = manifest.task
    
    # Create run record
    db.create_run(
        run_id=run_id,
        year=task.year,
        subject=task.subject,
        user_prompt=user_prompt,
        topic_id=manifest.refined_prompt.topic_id,
        topic_title=manifest.refined_prompt.topic_title,
        user_id=task.user_id
    )
    
    # Update file paths
    db.update_run_files(
        run_id=run_id,
        manifest_path=result_paths.get('manifest', ''),
        pdf_path=result_paths.get('pdf'),
        pptx_path=result_paths.get('pptx')
    )
    
    # Store panel information
    panel_uris = []
    panel_details = []
    
    for i, panel in enumerate(manifest.panels):
        uri = result_paths.get('images', {}).get(panel.chunk_id, '')
        panel_uris.append(uri)
        
        panel_details.append({
            'chunk_id': panel.chunk_id,
            'image_uri': uri,
            'caption': panel.caption,
            'positive_prompt': panel.provenance.prompt_text,
            'clip_score': 0.0  # Will be updated if image continuity is evaluated
        })
    
    db.update_run_panels(run_id, panel_uris, panel_details)
    
    # Store overall critique
    if manifest.overall_critique:
        critique = manifest.overall_critique
        # Convert scores to 0-10 range for storage
        avg_score = (
            getattr(critique.scores, 'alignment', 5) +
            getattr(critique.scores, 'vocab', 5) +
            getattr(critique.scores, 'scope', 5) +
            getattr(critique.scores, 'cognitive_load', 5)
        ) / 4.0
        
        db.store_critique(
            run_id=run_id,
            critique_type='overall',
            verdict=critique.verdict,
            score=avg_score,
            recommendations=critique.evidence
        )
    
    # Store image continuity results if available
    if image_continuity_result:
        db.store_critique(
            run_id=run_id,
            critique_type='image_continuity',
            verdict=image_continuity_result.verdict,
            score=image_continuity_result.overall_score * 10,  # Convert to 0-10 scale
            recommendations=image_continuity_result.recommendations
        )
    
    # Mark as completed
    db.complete_run(
        run_id=run_id,
        status="completed",
        model_notes=manifest.summary_notes
    )
    
    logger.info(f"Stored manifest run in database: {run_id}")
