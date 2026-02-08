"""Evaluation dataset management."""

import json
from typing import List, Optional
from dataclasses import dataclass, field, asdict

import structlog

logger = structlog.get_logger()


@dataclass
class TestCase:
    """A single test case for RAG evaluation."""
    
    id: str
    query: str
    expected_answer: Optional[str] = None
    relevant_doc_ids: List[str] = field(default_factory=list)
    relevant_sources: List[str] = field(default_factory=list)
    category: str = "general"
    difficulty: str = "medium"  # easy, medium, hard
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "TestCase":
        return cls(**data)


class EvaluationDataset:
    """Manage evaluation test datasets."""
    
    def __init__(self, name: str = "default"):
        self.name = name
        self.test_cases: List[TestCase] = []
    
    def add_test_case(self, test_case: TestCase):
        """Add a test case to the dataset."""
        self.test_cases.append(test_case)
    
    def add_test_cases(self, test_cases: List[TestCase]):
        """Add multiple test cases."""
        self.test_cases.extend(test_cases)
    
    def get_by_category(self, category: str) -> List[TestCase]:
        """Get test cases by category."""
        return [tc for tc in self.test_cases if tc.category == category]
    
    def get_by_difficulty(self, difficulty: str) -> List[TestCase]:
        """Get test cases by difficulty."""
        return [tc for tc in self.test_cases if tc.difficulty == difficulty]
    
    def get_by_tag(self, tag: str) -> List[TestCase]:
        """Get test cases with a specific tag."""
        return [tc for tc in self.test_cases if tag in tc.tags]
    
    def save(self, path: str):
        """Save dataset to JSON file."""
        data = {
            "name": self.name,
            "test_cases": [tc.to_dict() for tc in self.test_cases],
        }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info("Dataset saved", path=path, count=len(self.test_cases))
    
    @classmethod
    def load(cls, path: str) -> "EvaluationDataset":
        """Load dataset from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)
        
        dataset = cls(name=data.get("name", "loaded"))
        dataset.test_cases = [
            TestCase.from_dict(tc) for tc in data.get("test_cases", [])
        ]
        
        logger.info("Dataset loaded", path=path, count=len(dataset.test_cases))
        return dataset
    
    def __len__(self) -> int:
        return len(self.test_cases)
    
    def __iter__(self):
        return iter(self.test_cases)


def create_sample_dataset() -> EvaluationDataset:
    """Create a sample evaluation dataset for GenAuto X1."""
    dataset = EvaluationDataset(name="genai-auto-eval-v1")
    
    test_cases = [
        # Specifications queries
        TestCase(
            id="spec-001",
            query="What is the engine power of the GenAuto X1?",
            expected_answer="The GenAuto X1 has 128 hp with gasoline and 116 hp with ethanol.",
            category="specifications",
            difficulty="easy",
            tags=["engine", "power"],
        ),
        TestCase(
            id="spec-002",
            query="What is the fuel tank capacity?",
            expected_answer="The fuel tank capacity is 50 liters (13.2 gallons).",
            category="specifications",
            difficulty="easy",
            tags=["fuel", "capacity"],
        ),
        TestCase(
            id="spec-003",
            query="What are the dimensions of the vehicle?",
            expected_answer="Length: 4,199 mm, Width: 1,760 mm, Height: 1,568 mm, Wheelbase: 2,651 mm",
            category="specifications",
            difficulty="medium",
            tags=["dimensions"],
        ),
        TestCase(
            id="spec-004",
            query="What is the towing capacity?",
            expected_answer="The towing capacity is 750 kg (1,653 lbs) braked.",
            category="specifications",
            difficulty="easy",
            tags=["towing", "capacity"],
        ),
        
        # Maintenance queries
        TestCase(
            id="maint-001",
            query="How often should I change the oil?",
            expected_answer="Oil should be changed every 10,000 km or 12 months, whichever comes first.",
            category="maintenance",
            difficulty="easy",
            tags=["oil", "service"],
        ),
        TestCase(
            id="maint-002",
            query="What is included in the 20,000 km service?",
            expected_answer="The 20,000 km service includes all items from 10,000 km service plus engine air filter replacement, cabin air filter replacement, belt inspection, and wheel alignment and balancing.",
            category="maintenance",
            difficulty="medium",
            tags=["service", "maintenance"],
        ),
        TestCase(
            id="maint-003",
            query="When should the timing belt be replaced?",
            expected_answer="The timing belt should be replaced every 100,000 km.",
            category="maintenance",
            difficulty="easy",
            tags=["timing belt", "service"],
        ),
        TestCase(
            id="maint-004",
            query="What type of oil should I use?",
            expected_answer="Use SAE 5W-30 with API SN specification. The capacity with filter is 4.2 liters.",
            category="maintenance",
            difficulty="easy",
            tags=["oil", "specifications"],
        ),
        
        # Troubleshooting queries
        TestCase(
            id="trouble-001",
            query="What should I do if the check engine light comes on?",
            expected_answer="First check if the gas cap is loose. Common causes include oxygen sensor issues, catalytic converter problems, and ignition coil failures. If the light is flashing, seek service immediately.",
            category="troubleshooting",
            difficulty="medium",
            tags=["check engine", "diagnostics"],
        ),
        TestCase(
            id="trouble-002",
            query="My brakes are making a squealing noise. What could be wrong?",
            expected_answer="Squealing brakes often indicate worn brake pads. Check pad thickness (minimum 3mm). If there's metallic grinding, the rotor may be warped or worn.",
            category="troubleshooting",
            difficulty="medium",
            tags=["brakes", "noise"],
        ),
        TestCase(
            id="trouble-003",
            query="The engine is overheating. What should I do?",
            expected_answer="Turn heater to maximum, turn off AC, pull over safely. NEVER open reservoir while engine is hot. Wait at least 30 minutes to cool down. Common causes include low coolant, stuck thermostat, or failed cooling fan.",
            category="troubleshooting",
            difficulty="hard",
            tags=["overheating", "emergency"],
        ),
        TestCase(
            id="trouble-004",
            query="How do I jump start the car?",
            expected_answer="Connect red (+) cable to good battery, then to dead battery. Connect black (-) cable to good battery, then to engine ground on the other car. Start good car, wait 2-3 minutes, then try starting the dead car. Remove cables in reverse order.",
            category="troubleshooting",
            difficulty="medium",
            tags=["battery", "jump start"],
        ),
        
        # Features queries
        TestCase(
            id="feat-001",
            query="How do I activate the Adaptive Cruise Control?",
            expected_answer="Accelerate to desired speed (minimum 20 mph), press SET button on steering wheel, adjust following distance. To deactivate, press brake or OFF button.",
            category="features",
            difficulty="medium",
            tags=["ACC", "cruise control"],
        ),
        TestCase(
            id="feat-002",
            query="How does the parking assistant work?",
            expected_answer="Activate turn signal toward parking space, drive past at low speed (<12 mph). When 'P' appears, stop, select detected space, release steering wheel and control only pedals. Supports parallel, perpendicular, and angled parking.",
            category="features",
            difficulty="hard",
            tags=["parking", "assistant"],
        ),
        TestCase(
            id="feat-003",
            query="What voice commands are supported?",
            expected_answer="Supported commands include: 'Call [contact]', 'Navigate to [address]', 'Play [music/artist]', 'Set temperature to [degrees]'. Activate by saying 'Ok GenAuto' or pressing the steering wheel button.",
            category="features",
            difficulty="medium",
            tags=["voice", "infotainment"],
        ),
        
        # Safety queries
        TestCase(
            id="safety-001",
            query="How many airbags does the car have?",
            expected_answer="The vehicle has 6 airbags: 2 frontal (driver and passenger), 2 side (driver and passenger), and 2 curtain (head protection).",
            category="safety",
            difficulty="easy",
            tags=["airbags", "safety"],
        ),
        TestCase(
            id="safety-002",
            query="What should I do in case of an accident?",
            expected_answer="Stay calm, turn on hazard lights, set up warning triangle 100 ft from vehicle, check for injuries, call 911, do not move injured persons except in case of fire risk, file police report.",
            category="safety",
            difficulty="hard",
            tags=["accident", "emergency"],
        ),
        TestCase(
            id="safety-003",
            query="What child seat recommendations are there?",
            expected_answer="Under 1 year: rear-facing infant seat. 1-4 years: forward-facing child seat. 4-8 years: booster seat with back. 8-12 years: booster seat. The vehicle has ISOFIX anchor points on outer rear seats.",
            category="safety",
            difficulty="medium",
            tags=["child seat", "safety"],
        ),
        
        # FAQ queries
        TestCase(
            id="faq-001",
            query="What is the warranty period?",
            expected_answer="The GenAuto X1 has a 3-year or 60,000-mile warranty (whichever comes first), valid for manufacturing defects. Wear items like brake pads, tires, and wiper blades are not covered.",
            category="faq",
            difficulty="easy",
            tags=["warranty"],
        ),
        TestCase(
            id="faq-002",
            query="What is the correct tire pressure?",
            expected_answer="Front: 32 psi, Rear: 32 psi for normal load. For maximum load: 35 psi.",
            category="faq",
            difficulty="easy",
            tags=["tires", "pressure"],
        ),
    ]
    
    dataset.add_test_cases(test_cases)
    return dataset
