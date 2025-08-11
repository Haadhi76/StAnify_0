"""
Export Validator: Pre-export quality assurance checks
Ensures manifests are ready for export and meet quality standards.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from .manifest_contracts import RunManifest

logger = logging.getLogger(__name__)


class ExportValidationError(Exception):
    """Raised when manifest fails validation checks."""
    pass


class ExportValidator:
    """Validates manifests before export to catch common issues."""
    
    def __init__(self, min_image_size: int = 1024):
        self.min_image_size = min_image_size
    
    def validate_manifest(self, manifest: RunManifest) -> Dict[str, bool]:
        """
        Run comprehensive validation checks on a manifest.
        
        Args:
            manifest: The manifest to validate
            
        Returns:
            Dict with validation results for each check
            
        Raises:
            ExportValidationError: If critical validations fail
        """
        results = {}
        
        # 1. Assert counts match
        results['counts_match'] = self._check_counts_match(manifest)
        
        # 2. Assert image files exist and are non-trivial
        results['images_valid'] = self._check_images_valid(manifest)
        
        # 3. Assert objectives present
        results['objectives_present'] = self._check_objectives_present(manifest)
        
        # 4. Assert scores available
        results['scores_available'] = self._check_scores_available(manifest)
        
        # 5. Additional quality checks
        results['chunks_have_text'] = self._check_chunks_have_text(manifest)
        results['panels_have_captions'] = self._check_panels_have_captions(manifest)
        
        # Log results
        passed = sum(results.values())
        total = len(results)
        logger.info(f"Export validation: {passed}/{total} checks passed")
        
        for check, passed in results.items():
            if not passed:
                logger.warning(f"Validation failed: {check}")
        
        # Fail on critical issues
        critical_checks = ['counts_match', 'images_valid', 'chunks_have_text']
        failed_critical = [check for check in critical_checks if not results.get(check, False)]
        
        if failed_critical:
            raise ExportValidationError(f"Critical validation failures: {failed_critical}")
        
        return results
    
    def _check_counts_match(self, manifest: RunManifest) -> bool:
        """Check that panel count matches chunk count."""
        panel_count = len(manifest.panels)
        chunk_count = len(manifest.chunks)
        
        if panel_count != chunk_count:
            logger.warning(f"Count mismatch: {panel_count} panels vs {chunk_count} chunks")
            return False
        
        logger.debug(f"Counts match: {panel_count} panels = {chunk_count} chunks")
        return True
    
    def _check_images_valid(self, manifest: RunManifest) -> bool:
        """Check that all panel images exist and are non-trivial size."""
        invalid_images = []
        
        for panel in manifest.panels:
            if not panel.image_uri:
                invalid_images.append(f"{panel.chunk_id}: no image_uri")
                continue
            
            image_path = Path(panel.image_uri)
            if not image_path.exists():
                invalid_images.append(f"{panel.chunk_id}: file not found")
                continue
            
            file_size = image_path.stat().st_size
            if file_size < self.min_image_size:
                invalid_images.append(f"{panel.chunk_id}: file too small ({file_size} bytes)")
                continue
        
        if invalid_images:
            logger.warning(f"Invalid images: {invalid_images}")
            return False
        
        logger.debug(f"All {len(manifest.panels)} panel images are valid")
        return True
    
    def _check_objectives_present(self, manifest: RunManifest) -> bool:
        """Check that learning objectives are present."""
        objectives = getattr(manifest.refined_prompt, 'learning_objectives', None)
        
        if not objectives:
            logger.warning("No learning_objectives found in refined_prompt")
            return False
        
        if not isinstance(objectives, list) or len(objectives) == 0:
            logger.warning("learning_objectives is empty or invalid")
            return False
        
        logger.debug(f"Found {len(objectives)} learning objectives")
        return True
    
    def _check_scores_available(self, manifest: RunManifest) -> bool:
        """Check that critique scores are available."""
        if not manifest.overall_critique:
            logger.warning("No overall_critique found")
            return False
        
        if not hasattr(manifest.overall_critique, 'scores') or not manifest.overall_critique.scores:
            logger.warning("No scores found in overall_critique")
            return False
        
        scores = manifest.overall_critique.scores
        required_fields = ['alignment', 'vocab', 'scope', 'cognitive_load']
        missing_fields = []
        
        for field in required_fields:
            if not hasattr(scores, field) or getattr(scores, field) is None:
                missing_fields.append(field)
        
        if missing_fields:
            logger.warning(f"Missing score fields: {missing_fields}")
            return False
        
        logger.debug("All required score fields present")
        return True
    
    def _check_chunks_have_text(self, manifest: RunManifest) -> bool:
        """Check that all chunks have meaningful text content."""
        empty_chunks = []
        
        for chunk in manifest.chunks:
            # Handle both dict and ChunkSpec objects
            text = chunk.get('text') if isinstance(chunk, dict) else getattr(chunk, 'text', '')
            
            if not text or len(text.strip()) < 10:
                chunk_id = chunk.get('chunk_id') if isinstance(chunk, dict) else getattr(chunk, 'chunk_id', 'unknown')
                empty_chunks.append(chunk_id)
        
        if empty_chunks:
            logger.warning(f"Chunks with insufficient text: {empty_chunks}")
            return False
        
        logger.debug(f"All {len(manifest.chunks)} chunks have meaningful text")
        return True
    
    def _check_panels_have_captions(self, manifest: RunManifest) -> bool:
        """Check that all panels have captions."""
        missing_captions = []
        
        for panel in manifest.panels:
            if not panel.caption or len(panel.caption.strip()) < 5:
                missing_captions.append(panel.chunk_id)
        
        if missing_captions:
            logger.warning(f"Panels missing captions: {missing_captions}")
            return False
        
        logger.debug(f"All {len(manifest.panels)} panels have captions")
        return True


# Global validator instance
export_validator = ExportValidator()


def validate_before_export(manifest: RunManifest) -> Dict[str, bool]:
    """
    Convenience function to validate a manifest before export.
    
    Args:
        manifest: The manifest to validate
        
    Returns:
        Dict with validation results
        
    Raises:
        ExportValidationError: If critical validations fail
    """
    return export_validator.validate_manifest(manifest)
