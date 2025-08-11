"""
Test script for image continuity evaluator and persistence system.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_image_continuity_evaluator():
    """Test the image continuity evaluator."""
    try:
        from src.agentic_flow.image_continuity_evaluator import create_image_continuity_evaluator
        
        logger.info("Testing image continuity evaluator...")
        evaluator = create_image_continuity_evaluator()
        
        # Test with mock data
        image_paths = ["test1.jpg", "test2.jpg"]
        prompts = ["A red apple on a table", "The same red apple being eaten"]
        
        result = evaluator.evaluate_panel_continuity(image_paths, prompts)
        logger.info(f"Evaluation result: {result.verdict} (score: {result.overall_score:.2f})")
        
        return True
        
    except Exception as e:
        logger.error(f"Image continuity evaluator test failed: {e}")
        return False

def test_persistence_database():
    """Test the SQLite persistence system."""
    try:
        from src.agentic_flow.persistence import get_database
        import uuid
        
        logger.info("Testing persistence database...")
        db = get_database("test_runs.db")
        
        # Test creating a run with a unique ID
        test_run_id = f"test_run_{uuid.uuid4().hex[:8]}"
        db.create_run(
            run_id=test_run_id,
            year="Year 1",
            subject="mathematics",
            user_prompt="Test prompt for addition",
            topic_id="add_within_20",
            topic_title="Addition within 20"
        )
        
        # Test retrieving the run
        run = db.get_run(test_run_id)
        if run:
            logger.info(f"Retrieved run: {run.run_id} - {run.topic_title}")
        
        # Test listing runs
        runs = db.list_runs(limit=5)
        logger.info(f"Found {len(runs)} runs in database")
        
        # Cleanup
        db.delete_run(test_run_id)
        logger.info("Test run cleaned up")
        
        return True
        
    except Exception as e:
        logger.error(f"Persistence database test failed: {e}")
        return False

def test_pipeline_integration():
    """Test the pipeline with image continuity and persistence."""
    try:
        from src.agentic_flow.pipeline import run_demo
        
        logger.info("Testing pipeline integration...")
        
        # Set up test directories
        kb_dir = str(project_root / "kb")
        out_dir = str(project_root / "test_output")
        Path(out_dir).mkdir(exist_ok=True)
        
        # Run the pipeline
        result = run_demo(
            year="Year 1",
            subject="mathematics", 
            user_prompt="Simple addition with fruits",
            kb_dir=kb_dir,
            out_dir=out_dir
        )
        
        logger.info(f"Pipeline completed successfully: {result['run_id']}")
        
        if 'continuity_result' in result:
            continuity = result['continuity_result']
            logger.info(f"Image continuity: {continuity.verdict if continuity else 'N/A'}")
        
        return True
        
    except Exception as e:
        logger.error(f"Pipeline integration test failed: {e}")
        return False

def check_dependencies():
    """Check if optional dependencies are available."""
    dependencies = {
        "torch": "PyTorch for CLIP and LPIPS",
        "clip": "OpenAI CLIP for image-text alignment",
        "lpips": "LPIPS for perceptual similarity", 
        "skimage": "scikit-image for SSIM",
        "PIL": "Pillow for image processing",
        "numpy": "NumPy for numerical operations"
    }
    
    available = []
    missing = []
    
    for dep, description in dependencies.items():
        try:
            if dep == "clip":
                import clip
            elif dep == "skimage":
                from skimage.metrics import structural_similarity
            else:
                __import__(dep)
            available.append(f"✅ {dep}: {description}")
        except ImportError:
            missing.append(f"❌ {dep}: {description}")
    
    logger.info("Dependency Status:")
    for item in available:
        logger.info(item)
    for item in missing:
        logger.warning(item)
    
    if missing:
        logger.info("\nTo install missing dependencies:")
        logger.info("pip install torch torchvision")
        logger.info("pip install git+https://github.com/openai/CLIP.git")
        logger.info("pip install lpips")
        logger.info("pip install scikit-image")
        logger.info("pip install pillow numpy")
    
    return len(missing) == 0

def main():
    """Run all tests."""
    logger.info("🧪 Testing StAnify Image Continuity and Persistence Systems")
    logger.info("=" * 60)
    
    # Check dependencies
    logger.info("1. Checking dependencies...")
    deps_ok = check_dependencies()
    
    # Test persistence (should always work)
    logger.info("\n2. Testing persistence database...")
    persistence_ok = test_persistence_database()
    
    # Test image continuity (may use mocks if deps missing)
    logger.info("\n3. Testing image continuity evaluator...")
    continuity_ok = test_image_continuity_evaluator()
    
    # Test pipeline integration
    logger.info("\n4. Testing pipeline integration...")
    pipeline_ok = test_pipeline_integration()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("🎯 Test Summary:")
    logger.info(f"Dependencies: {'✅ All available' if deps_ok else '⚠️ Some missing (will use fallbacks)'}")
    logger.info(f"Persistence: {'✅ Working' if persistence_ok else '❌ Failed'}")
    logger.info(f"Image Continuity: {'✅ Working' if continuity_ok else '❌ Failed'}")
    logger.info(f"Pipeline Integration: {'✅ Working' if pipeline_ok else '❌ Failed'}")
    
    if persistence_ok and continuity_ok and pipeline_ok:
        logger.info("\n🎉 All systems operational! Your StAnify setup is ready.")
    else:
        logger.warning("\n⚠️ Some systems need attention. Check the logs above.")

if __name__ == "__main__":
    main()
