from modules.quest_image_processor import QuestImageProcessor
import os

def test_process_quest_frame_returns_3_values():
    print("Testing process_quest_frame return values...")
    
    # Mock paths that don't exist to trigger early returns
    # This should hit the first 'if not format_json.exists(): return None, None, None'
    res = QuestImageProcessor.process_quest_frame("non_existent_path", {}, camera='left')
    print(f"Result for non-existent path: {res}")
    
    if len(res) != 3:
        print(f"FAIL: Expected 3 values, got {len(res)}")
        exit(1)
    
    print("✓ process_quest_frame returns 3 values on failure.")

if __name__ == "__main__":
    test_process_quest_frame_returns_3_values()
