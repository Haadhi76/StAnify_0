# Sample data for testing Pydantic contracts
SAMPLE_CHUNK_DATA = {
    "chunk_id": "test_chunk_001",
    "content": "This is a test chunk about photosynthesis in plants.",
    "metadata": {
        "source": "biology_textbook",
        "page": 42,
        "topic": "photosynthesis"
    }
}

SAMPLE_REFINED_PROMPT_DATA = {
    "original_prompt": "Create a visual sequence about photosynthesis",
    "refined_prompt": "Create a detailed visual sequence showing the process of photosynthesis in plants, including sunlight absorption, carbon dioxide intake, and oxygen production",
    "refinement_rationale": "Added specific details about the photosynthesis process to make the visual sequence more educational and comprehensive"
}

SAMPLE_IMAGE_PANEL_DATA = {
    "panel_id": "panel_001",
    "description": "A green leaf absorbing sunlight with visible light rays",
    "image_prompt": "Professional educational illustration of a green plant leaf with golden sunlight rays shining on it, showing light absorption process, clean white background, high detail",
    "generated_image_path": "/path/to/generated/image.png"
}

SAMPLE_MANIFEST_DATA = {
    "run_id": "test_run_123",
    "title": "Photosynthesis Process",
    "description": "Visual sequence explaining how plants convert sunlight into energy",
    "panels": [
        {
            "panel_id": "panel_001",
            "description": "Sunlight absorption",
            "image_prompt": "Leaf absorbing sunlight",
            "generated_image_path": "/path/to/image1.png"
        },
        {
            "panel_id": "panel_002",
            "description": "CO2 intake",
            "image_prompt": "Plant taking in carbon dioxide",
            "generated_image_path": "/path/to/image2.png"
        }
    ],
    "metadata": {
        "created_at": "2025-08-11T12:00:00Z",
        "total_panels": 2,
        "topic": "biology"
    }
}

SAMPLE_CRITIQUE_DATA = {
    "original_prompt": "Show photosynthesis",
    "critique": "The prompt is too brief and lacks educational context. It should specify the key stages of photosynthesis and target audience.",
    "suggestions": [
        "Add details about chlorophyll and light absorption",
        "Include carbon dioxide and oxygen exchange",
        "Specify if this is for elementary or high school students"
    ],
    "severity": "medium"
}
