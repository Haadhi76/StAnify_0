
import streamlit as st
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agentic_flow.pipeline import run_demo
from src.agentic_flow.persistence import get_database, RunRecord
from src.agentic_flow.manifest_contracts import RunManifest
from src.agentic_flow.exporters.pdf_exporter import export_manifest_to_pdf
from src.agentic_flow.exporters.pptx_exporter import export_manifest_to_pptx
from src.agentic_flow.image_service import image_service

st.set_page_config(
    page_title="StAnify - Educational Content Generator", 
    page_icon="🎨", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "selected_run" not in st.session_state:
    st.session_state.selected_run = None
if "show_runs" not in st.session_state:
    st.session_state.show_runs = False

def load_manifest_from_file(manifest_path: str) -> Optional[RunManifest]:
    """Load manifest from JSON file."""
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return RunManifest.parse_obj(data)
    except Exception as e:
        st.error(f"Error loading manifest: {e}")
        return None

def export_manifest_files(manifest: RunManifest, run_id: str) -> Dict[str, str]:
    """Export manifest to various formats."""
    from src.agentic_flow.exporters.pdf_exporter import export_manifest_to_pdf
    from src.agentic_flow.exporters.pptx_exporter import export_manifest_to_pptx
    from src.agentic_flow.exporters.zip_exporter import create_export_package
    
    try:
        BASE_DIR = Path(__file__).resolve().parents[1]
        out_dir = BASE_DIR / "exports"
        out_dir.mkdir(exist_ok=True)
        
        # Use the new comprehensive export package
        exports = create_export_package(manifest, str(out_dir))
        
        return exports
    except Exception as e:
        st.error(f"Failed to re-export files: {e}")
        return {}

def render_runs_sidebar():
    """Render the runs history sidebar."""
    st.sidebar.header("📁 Runs History")
    
    # Get database instance
    try:
        db = get_database()
        stats = db.get_run_statistics()
        
        # Show statistics
        st.sidebar.metric("Total Runs", stats['total_runs'])
        st.sidebar.metric("Recent (24h)", stats['recent_runs_24h'])
        
        if stats['total_runs'] > 0:
            col1, col2 = st.sidebar.columns(2)
            with col1:
                st.metric("Avg Critique", f"{stats['avg_critique_score']:.1f}")
            with col2:
                st.metric("Avg Continuity", f"{stats['avg_continuity_score']:.1f}")
        
        # Status filter
        status_filter = st.sidebar.selectbox(
            "Filter by Status",
            ["All", "completed", "failed", "in_progress"],
            index=0
        )
        
        # Get runs list
        runs = db.list_runs(
            limit=20,
            status=None if status_filter == "All" else status_filter
        )
        
        if runs:
            st.sidebar.subheader("Recent Runs")
            
            for run in runs:
                # Create a compact run display
                run_display = f"**{run.run_id[:8]}...** - {run.year} {run.subject}"
                
                if st.sidebar.button(
                    run_display,
                    key=f"run_{run.run_id}",
                    help=f"Created: {run.created_at}\nPrompt: {run.user_prompt[:50]}..."
                ):
                    st.session_state.selected_run = run.run_id
                    st.session_state.show_runs = True
                    st.rerun()
                
                # Show status and scores inline
                status_color = {
                    "completed": "🟢",
                    "failed": "🔴", 
                    "in_progress": "🟡"
                }.get(run.status, "⚪")
                
                st.sidebar.caption(
                    f"{status_color} {run.status} | "
                    f"Critique: {run.overall_critique_score:.1f} | "
                    f"Continuity: {run.image_continuity_score:.1f}"
                )
                st.sidebar.divider()
        else:
            st.sidebar.info("No runs found")
            
    except Exception as e:
        st.sidebar.error(f"Database error: {e}")

def render_run_details(run_id: str):
    """Render detailed view of a specific run."""
    try:
        db = get_database()
        run = db.get_run(run_id)
        
        if not run:
            st.error(f"Run {run_id} not found")
            return
        
        st.header(f"📋 Run Details: {run.run_id}")
        
        # Basic information
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Year", run.year)
        with col2:
            st.metric("Subject", run.subject)
        with col3:
            st.metric("Status", run.status)
        with col4:
            st.metric("Created", run.created_at.strftime("%Y-%m-%d %H:%M"))
        
        # Prompt and topic
        st.subheader("📝 Content Details")
        st.text_area("User Prompt", run.user_prompt, disabled=True)
        st.text_input("Topic", f"{run.topic_title} ({run.topic_id})", disabled=True)
        
        # Evaluation scores
        st.subheader("📊 Evaluation Results")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Overall Critique", 
                f"{run.overall_critique_score:.1f}/10",
                help=f"Verdict: {run.overall_critique_verdict}"
            )
        
        with col2:
            st.metric(
                "Image Continuity", 
                f"{run.image_continuity_score:.1f}/10",
                help=f"Verdict: {run.image_continuity_verdict}"
            )
        
        # File operations
        st.subheader("📂 Files & Export")
        
        if run.manifest_path and Path(run.manifest_path).exists():
            col1, col2, col3 = st.columns(3)
            
            # Load manifest for re-export
            manifest = load_manifest_from_file(run.manifest_path)
            
            if manifest:
                with col1:
                    if st.button("🔄 Re-export PDF"):
                        with st.spinner("Generating PDF..."):
                            exports = export_manifest_files(manifest, run.run_id)
                            if exports.get("pdf"):
                                st.success("PDF re-exported!")
                                st.download_button(
                                    "Download PDF",
                                    data=open(exports["pdf"], "rb").read(),
                                    file_name=f"{run.run_id}_reexport.pdf"
                                )
                
                with col2:
                    if st.button("🔄 Re-export PowerPoint"):
                        with st.spinner("Generating PowerPoint..."):
                            exports = export_manifest_files(manifest, run.run_id)
                            if exports.get("pptx"):
                                st.success("PowerPoint re-exported!")
                                st.download_button(
                                    "Download PPTX",
                                    data=open(exports["pptx"], "rb").read(),
                                    file_name=f"{run.run_id}_reexport.pptx"
                                )
                
                with col3:
                    st.download_button(
                        "Download Manifest",
                        data=open(run.manifest_path, "rb").read(),
                        file_name=f"{run.run_id}_manifest.json"
                    )
            
            # Display original files if they exist
            st.subheader("📁 Original Files")
            file_cols = st.columns(3)
            
            if run.pdf_path and Path(run.pdf_path).exists():
                with file_cols[0]:
                    st.download_button(
                        "Original PDF",
                        data=open(run.pdf_path, "rb").read(),
                        file_name=Path(run.pdf_path).name
                    )
            
            if run.pptx_path and Path(run.pptx_path).exists():
                with file_cols[1]:
                    st.download_button(
                        "Original PPTX", 
                        data=open(run.pptx_path, "rb").read(),
                        file_name=Path(run.pptx_path).name
                    )
        
        # Panel preview
        if run.panel_uris:
            st.subheader("🖼️ Generated Panels")
            panel_cols = st.columns(min(len(run.panel_uris), 3))
            
            for i, panel_uri in enumerate(run.panel_uris):
                if Path(panel_uri).exists():
                    with panel_cols[i % 3]:
                        st.image(panel_uri, caption=f"Panel {i+1}")
                else:
                    with panel_cols[i % 3]:
                        st.error(f"Panel {i+1} not found")
        
        # Model notes
        if run.model_notes:
            st.subheader("📋 Model Notes")
            st.text_area("Notes", run.model_notes, disabled=True)
        
        # Back button
        if st.button("← Back to New Run"):
            st.session_state.show_runs = False
            st.session_state.selected_run = None
            st.rerun()
            
    except Exception as e:
        st.error(f"Error loading run details: {e}")

def get_available_years_and_subjects():
    """Get available years and subjects from KB files."""
    BASE_DIR = Path(__file__).resolve().parents[1]
    kb_dir = BASE_DIR / "kb"
    
    years_subjects = {}
    
    try:
        # Load all YAML files in kb directory
        import yaml
        
        for yaml_file in kb_dir.glob("year*.yaml"):
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            year = data.get('year', '')
            subjects = data.get('subjects', {})
            
            if year and subjects:
                years_subjects[year] = list(subjects.keys())
                
    except Exception as e:
        st.error(f"Error loading KB files: {e}")
        # Fallback
        years_subjects = {"Year 1": ["mathematics"]}
    
    return years_subjects

def resolve_topic_from_prompt(year: str, subject: str, prompt: str):
    """Resolve topic from user prompt using KB."""
    try:
        from src.agentic_flow.kb_loader import load_curriculum_kb, get_year_slice
        from src.agentic_flow.pipeline import resolve_topic
        
        BASE_DIR = Path(__file__).resolve().parents[1]
        kb_dir = str((BASE_DIR / "kb").resolve())
        
        # Load KB and resolve topic
        kb = load_curriculum_kb(kb_dir)
        ykb = get_year_slice(kb, year)
        subj, topic, confidence = resolve_topic(ykb, subject, prompt)
        
        return {
            'topic_id': topic.id,
            'topic_title': topic.title,
            'confidence': confidence,
            'subject_name': subj.name
        }
    except Exception as e:
        return {
            'topic_id': 'unknown',
            'topic_title': 'Could not resolve topic',
            'confidence': 0.0,
            'subject_name': subject,
            'error': str(e)
        }

def render_backend_status():
    """Render backend status indicator in the UI."""
    try:
        # Import settings here to get latest values
        from src.agentic_flow.settings import settings
        
        # Show detailed configuration at the top
        st.caption(f"🖼️ Backend: **{settings.image_backend}** | Model: **{settings.stability_model}** | API: {settings.stability_base_url} | Mode: **{settings.stability_api_mode}**")
        
        status = image_service.get_status()
        active = status["active"]
        configured = status["configured"]
        a1111_ok = status["a1111_ok"]
        
        # Choose emoji and color based on status
        if active == "stability":
            badge = "🟢" 
            message = f"**{active}** (Cloud AI generation active)"
        elif a1111_ok and active == "sdxl-a1111":
            badge = "🟢"
            message = f"**{active}** (Local AI generation active)"
        elif active == "placeholder" and configured == "auto":
            badge = "🟡"
            message = f"**{active}** (AI services offline - using placeholders)"
        elif active == "placeholder":
            badge = "🔵"
            message = f"**{active}** (configured)"
        else:
            badge = "🔴"
            message = f"**{active}** (unknown status)"
        
        # Display status
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption(f"{badge} Image backend: {message}")
        with col2:
            if configured == "auto" and active == "placeholder":
                if st.button("🔄 Recheck Services", help="Force recheck AI service connections"):
                    # Force a synchronous recheck
                    image_service._health.last_check_ts = 0
                    image_service._health.cb_open_until = 0
                    st.rerun()
    except Exception as e:
        st.caption(f"🔴 Backend status: Error ({str(e)})")

def render_new_run_interface():
    """Render the interface for creating new runs."""
    st.title("🎨 StAnify - Educational Content Generator")
    st.caption("AI-powered visual educational content with continuity checks and LLM agents")
    
    # Backend status indicator
    render_backend_status()
    
    # Get available years and subjects
    years_subjects = get_available_years_and_subjects()
    available_years = list(years_subjects.keys())
    
    # Input form
    with st.form("content_generation"):
        col1, col2 = st.columns(2)
        
        with col1:
            year = st.selectbox("Year Level", available_years, index=0)
            
        with col2:
            # Update subjects based on selected year
            available_subjects = years_subjects.get(year, ["mathematics"])
            subject = st.selectbox("Subject", available_subjects, index=0)
        
        prompt = st.text_area(
            "Educational Content Prompt",
            "Teach addition up to 20 using fruit and a number line.",
            help="Describe what you want to teach and how"
        )
        
        # Topic resolution preview
        if prompt.strip():
            with st.expander("🎯 Topic Resolution Preview", expanded=True):
                topic_info = resolve_topic_from_prompt(year, subject, prompt)
                
                if 'error' not in topic_info:
                    # Success case
                    confidence_color = "🟢" if topic_info['confidence'] > 0.8 else "🟡" if topic_info['confidence'] > 0.5 else "🔴"
                    
                    st.markdown(f"""
                    **Resolved Topic:** {confidence_color} `{topic_info['topic_title']}`  
                    **Subject:** {topic_info['subject_name']}  
                    **Confidence:** {topic_info['confidence']:.1%}  
                    **Topic ID:** `{topic_info['topic_id']}`
                    """)
                    
                    if topic_info['confidence'] < 0.7:
                        st.warning("⚠️ Low confidence in topic resolution. Consider refining your prompt.")
                else:
                    st.error(f"❌ Topic resolution failed: {topic_info.get('error', 'Unknown error')}")
        
        submitted = st.form_submit_button("🚀 Generate Content", use_container_width=True)
    
    if submitted:
        if not prompt.strip():
            st.error("Please enter a prompt")
            return
        
        # Set up directories
        BASE_DIR = Path(__file__).resolve().parents[1]
        kb_dir = str((BASE_DIR / "kb").resolve())
        out_dir = str((BASE_DIR / "exports").resolve())
        
        # Run pipeline with progress tracking
        with st.spinner("🔄 Running AI pipeline..."):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Update progress
                progress_bar.progress(20)
                status_text.text("🧠 Loading curriculum knowledge...")
                
                progress_bar.progress(40)
                status_text.text("✨ Generating content with LLM agents...")
                
                progress_bar.progress(60)
                status_text.text("🎨 Creating visual panels...")
                
                progress_bar.progress(80)
                status_text.text("🔍 Evaluating content quality and continuity...")
                
                # Run the actual pipeline
                result = run_demo(year, subject, prompt, kb_dir, out_dir)
                
                progress_bar.progress(100)
                status_text.text("✅ Content generation complete!")
                
                # Show results
                st.success(f"🎉 Content generated successfully! Run ID: {result['run_id']}")
                
                # Display metrics if available
                if 'continuity_result' in result and result['continuity_result']:
                    continuity = result['continuity_result']
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Content Quality", "Generated")
                    with col2:
                        st.metric(
                            "Image Continuity", 
                            continuity.verdict,
                            help=f"Score: {continuity.overall_score:.2f}"
                        )
                    with col3:
                        st.metric("Status", "Completed")
                
                # Download buttons
                st.subheader("📥 Download Results")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.download_button(
                        "📄 Download PDF",
                        data=open(result["pdf"], "rb").read(),
                        file_name=Path(result["pdf"]).name,
                        use_container_width=True
                    )
                
                with col2:
                    st.download_button(
                        "📊 Download PowerPoint",
                        data=open(result["pptx"], "rb").read(),
                        file_name=Path(result["pptx"]).name,
                        use_container_width=True
                    )
                
                with col3:
                    st.download_button(
                        "📋 Download Manifest",
                        data=open(result["manifest"], "rb").read(),
                        file_name=Path(result["manifest"]).name,
                        use_container_width=True
                    )
                
                # Preview panels
                st.subheader("🖼️ Generated Panels")
                if result.get("images"):
                    panel_cols = st.columns(min(len(result["images"]), 3))
                    for i, (chunk_id, img_path) in enumerate(result["images"].items()):
                        with panel_cols[i % 3]:
                            if Path(img_path).exists():
                                st.image(img_path, caption=f"Panel {i+1} ({chunk_id})")
                            else:
                                st.error(f"Panel {i+1} not found")
                
            except Exception as e:
                progress_bar.progress(100)
                status_text.text("❌ Generation failed")
                st.error(f"Content generation failed: {e}")
                st.exception(e)

# Main app logic
def main():
    """Main application entry point."""
    
    # Render sidebar with runs
    render_runs_sidebar()
    
    # Main content area
    if st.session_state.show_runs and st.session_state.selected_run:
        render_run_details(st.session_state.selected_run)
    else:
        render_new_run_interface()

if __name__ == "__main__":
    main()
