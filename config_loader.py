"""
Configuration loader for comedy clipper
Loads and validates rules from YAML config file
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class TransitionRule:
    """Represents a single transition rule"""
    from_count: Any  # int or "any"
    to_count: Any    # int, "any", or "2+" or "1-"
    action: str      # "start_segment" or "end_segment"
    description: str

    def matches(self, from_count: int, to_count: int) -> bool:
        """Check if this rule matches a transition"""
        # Check from_count
        if self.from_count == "any":
            from_matches = True
        else:
            from_matches = (from_count == self.from_count)

        # Check to_count
        if self.to_count == "any":
            to_matches = True
        elif isinstance(self.to_count, str):
            if self.to_count == "2+":
                to_matches = (to_count >= 2)
            elif self.to_count == "1-":
                to_matches = (to_count <= 1)
            else:
                to_matches = False
        else:
            to_matches = (to_count == self.to_count)

        return from_matches and to_matches


class ClipperConfig:
    """Loaded and validated configuration"""

    def __init__(self, config_dict: Dict[str, Any]):
        """Initialize from loaded YAML dict"""
        self.raw = config_dict

        # Parse transition rules
        self.transition_rules: List[TransitionRule] = []
        if config_dict.get("transition_detection", {}).get("enabled", True):
            for rule_dict in config_dict.get("transition_detection", {}).get("rules", []):
                self.transition_rules.append(TransitionRule(
                    from_count=rule_dict["from"],
                    to_count=rule_dict["to"],
                    action=rule_dict["action"],
                    description=rule_dict.get("description", "")
                ))

    def get(self, path: str, default: Any = None) -> Any:
        """Get config value by dot-separated path"""
        keys = path.split(".")
        value = self.raw
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        return value

    def get_transition_action(self, from_count: int, to_count: int) -> Optional[str]:
        """
        Get action for a person count transition.

        Returns:
            "start_segment", "end_segment", or None
        """
        for rule in self.transition_rules:
            if rule.matches(from_count, to_count):
                return rule.action
        return None

    def should_start_segment(self, from_count: int, to_count: int) -> bool:
        """Check if transition should start a segment"""
        return self.get_transition_action(from_count, to_count) == "start_segment"

    def should_end_segment(self, from_count: int, to_count: int) -> bool:
        """Check if transition should end a segment"""
        return self.get_transition_action(from_count, to_count) == "end_segment"


def load_config(config_path: Optional[str] = None) -> ClipperConfig:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to config file. If None, uses default clipper_rules.yaml

    Returns:
        ClipperConfig object
    """
    if config_path is None:
        # Use default config in same directory as this script
        config_path = Path(__file__).parent / "clipper_rules.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        config_dict = yaml.safe_load(f)

    return ClipperConfig(config_dict)


def create_default_config(output_path: str):
    """Create a default config file"""
    default_config = {
        "transition_detection": {
            "enabled": True,
            "rules": [
                {"from": 2, "to": 1, "action": "end_segment", "description": "Comedian exits"},
                {"from": 1, "to": 2, "action": "start_segment", "description": "Comedian enters"},
                {"from": 0, "to": 1, "action": "start_segment", "description": "Person appears"},
                {"from": 1, "to": 0, "action": "end_segment", "description": "Person disappears"},
            ],
            "transition_stability_frames": 3,
            "person_count_method": "min"
        },
        "position_detection": {
            "enabled": True,
            "exit_threshold": 0.15,
            "exit_stability_frames": 2,
            "tracking_point": "torso"
        },
        "confidence": {
            "face_detection": {
                "min_detection_confidence": 0.5,
                "model_selection": 1
            },
            "pose_detection": {
                "min_detection_confidence": 0.5,
                "min_tracking_confidence": 0.5,
                "model_complexity": 1,
                "smooth_landmarks": True
            }
        },
        "filtering": {
            "min_duration": 180.0,
            "max_duration": 0,
            "min_gap": 5.0,
            "merge_close_segments": True
        },
        "debug": {
            "export_frames": True,
            "export_first_frame": True,
            "export_last_frame": True
        }
    }

    with open(output_path, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)

    print(f"Created default config: {output_path}")


if __name__ == "__main__":
    # Test config loading
    config = load_config()
    print("Config loaded successfully!")
    print(f"Transition detection enabled: {config.get('transition_detection.enabled')}")
    print(f"Min duration: {config.get('filtering.min_duration')}s")

    # Test transition matching
    print("\nTransition rule tests:")
    print(f"2→1: {config.get_transition_action(2, 1)}")  # Should be end_segment
    print(f"1→2: {config.get_transition_action(1, 2)}")  # Should be start_segment
    print(f"0→1: {config.get_transition_action(0, 1)}")  # Should be start_segment
    print(f"1→0: {config.get_transition_action(1, 0)}")  # Should be end_segment
