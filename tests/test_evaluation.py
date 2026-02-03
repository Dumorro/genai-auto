"""Evaluation module tests."""

import pytest
from src.evaluation.metrics import MetricsCalculator, RetrievalMetrics, GenerationMetrics
from src.evaluation.dataset import TestCase, EvaluationDataset, create_sample_dataset


class TestMetricsCalculator:
    """Metrics calculation tests."""

    def test_precision_at_k(self):
        """Test Precision@K calculation."""
        calc = MetricsCalculator()
        
        # All relevant
        assert calc.precision_at_k([True, True, True], k=3) == 1.0
        
        # None relevant
        assert calc.precision_at_k([False, False, False], k=3) == 0.0
        
        # Half relevant
        assert calc.precision_at_k([True, False, True, False], k=4) == 0.5
        
        # Empty list
        assert calc.precision_at_k([], k=3) == 0.0

    def test_recall_at_k(self):
        """Test Recall@K calculation."""
        calc = MetricsCalculator()
        
        # All relevant found
        assert calc.recall_at_k([True, True, True], total_relevant=3) == 1.0
        
        # Half found
        assert calc.recall_at_k([True, True, False], total_relevant=4) == 0.5
        
        # None found
        assert calc.recall_at_k([False, False, False], total_relevant=3) == 0.0
        
        # Zero total relevant
        assert calc.recall_at_k([True, True], total_relevant=0) == 0.0

    def test_mrr(self):
        """Test Mean Reciprocal Rank calculation."""
        calc = MetricsCalculator()
        
        # First is relevant
        assert calc.mrr([True, False, False]) == 1.0
        
        # Second is relevant
        assert calc.mrr([False, True, False]) == 0.5
        
        # Third is relevant
        assert calc.mrr([False, False, True]) == pytest.approx(0.333, rel=0.01)
        
        # None relevant
        assert calc.mrr([False, False, False]) == 0.0

    def test_hit_rate(self):
        """Test Hit Rate calculation."""
        calc = MetricsCalculator()
        
        assert calc.hit_rate([True, False, False]) == 1.0
        assert calc.hit_rate([False, True, False]) == 1.0
        assert calc.hit_rate([False, False, False]) == 0.0

    def test_ndcg(self):
        """Test NDCG calculation."""
        calc = MetricsCalculator()
        
        # Perfect ranking
        scores = [1.0, 0.8, 0.6, 0.4]
        assert calc.ndcg(scores) == 1.0
        
        # Empty scores
        assert calc.ndcg([]) == 0.0
        
        # Single score
        assert calc.ndcg([0.9]) == 1.0


class TestRetrievalMetrics:
    """RetrievalMetrics dataclass tests."""

    def test_to_dict(self):
        """Test metrics serialization."""
        metrics = RetrievalMetrics(
            precision_at_k=0.8,
            recall_at_k=0.6,
            mrr=0.9,
            ndcg=0.85,
            hit_rate=1.0,
            avg_score=0.75,
        )
        
        d = metrics.to_dict()
        
        assert d["precision_at_k"] == 0.8
        assert d["mrr"] == 0.9
        assert isinstance(d["precision_at_k"], float)


class TestGenerationMetrics:
    """GenerationMetrics dataclass tests."""

    def test_to_dict(self):
        """Test metrics serialization."""
        metrics = GenerationMetrics(
            faithfulness=0.9,
            answer_relevance=0.85,
            context_relevance=0.8,
            completeness=0.75,
        )
        
        d = metrics.to_dict()
        
        assert d["faithfulness"] == 0.9
        assert d["answer_relevance"] == 0.85


class TestTestCase:
    """TestCase tests."""

    def test_create_test_case(self):
        """Test creating a test case."""
        tc = TestCase(
            id="test-001",
            query="What is the engine power?",
            expected_answer="128 hp",
            category="specifications",
            difficulty="easy",
            tags=["engine", "power"],
        )
        
        assert tc.id == "test-001"
        assert tc.category == "specifications"
        assert "engine" in tc.tags

    def test_to_dict(self):
        """Test test case serialization."""
        tc = TestCase(
            id="test-001",
            query="Test query",
        )
        
        d = tc.to_dict()
        
        assert d["id"] == "test-001"
        assert d["query"] == "Test query"
        assert "category" in d

    def test_from_dict(self):
        """Test test case deserialization."""
        data = {
            "id": "test-001",
            "query": "Test query",
            "expected_answer": "Test answer",
            "category": "test",
            "difficulty": "easy",
            "tags": ["tag1"],
            "relevant_doc_ids": [],
            "relevant_sources": [],
        }
        
        tc = TestCase.from_dict(data)
        
        assert tc.id == "test-001"
        assert tc.expected_answer == "Test answer"


class TestEvaluationDataset:
    """EvaluationDataset tests."""

    def test_create_dataset(self):
        """Test creating a dataset."""
        dataset = EvaluationDataset(name="test-dataset")
        
        assert dataset.name == "test-dataset"
        assert len(dataset) == 0

    def test_add_test_case(self):
        """Test adding test cases."""
        dataset = EvaluationDataset()
        tc = TestCase(id="test-001", query="Test")
        
        dataset.add_test_case(tc)
        
        assert len(dataset) == 1

    def test_get_by_category(self):
        """Test filtering by category."""
        dataset = EvaluationDataset()
        dataset.add_test_cases([
            TestCase(id="1", query="Q1", category="specs"),
            TestCase(id="2", query="Q2", category="specs"),
            TestCase(id="3", query="Q3", category="maintenance"),
        ])
        
        specs = dataset.get_by_category("specs")
        
        assert len(specs) == 2

    def test_get_by_difficulty(self):
        """Test filtering by difficulty."""
        dataset = EvaluationDataset()
        dataset.add_test_cases([
            TestCase(id="1", query="Q1", difficulty="easy"),
            TestCase(id="2", query="Q2", difficulty="hard"),
            TestCase(id="3", query="Q3", difficulty="easy"),
        ])
        
        easy = dataset.get_by_difficulty("easy")
        
        assert len(easy) == 2

    def test_iteration(self):
        """Test iterating over dataset."""
        dataset = EvaluationDataset()
        dataset.add_test_cases([
            TestCase(id="1", query="Q1"),
            TestCase(id="2", query="Q2"),
        ])
        
        ids = [tc.id for tc in dataset]
        
        assert ids == ["1", "2"]


class TestSampleDataset:
    """Sample dataset tests."""

    def test_create_sample_dataset(self):
        """Test sample dataset creation."""
        dataset = create_sample_dataset()
        
        assert len(dataset) > 0
        assert dataset.name == "genai-auto-eval-v1"

    def test_sample_dataset_has_categories(self):
        """Test sample dataset has multiple categories."""
        dataset = create_sample_dataset()
        
        categories = set(tc.category for tc in dataset)
        
        assert len(categories) >= 4
        assert "specifications" in categories
        assert "maintenance" in categories

    def test_sample_dataset_has_difficulties(self):
        """Test sample dataset has multiple difficulties."""
        dataset = create_sample_dataset()
        
        difficulties = set(tc.difficulty for tc in dataset)
        
        assert "easy" in difficulties
        assert "medium" in difficulties
        assert "hard" in difficulties
