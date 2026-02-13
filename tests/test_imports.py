import fpl_insights
import fpl_insights.core
import fpl_insights.ingestion
import fpl_insights.ml
import fpl_insights.pipelines
import fpl_insights.app

def test_imports():
    """Verify that all core modules can be imported correctly."""
    assert fpl_insights.__name__ == 'fpl_insights'
    assert fpl_insights.core.__name__ == 'fpl_insights.core'
    assert fpl_insights.ingestion.__name__ == 'fpl_insights.ingestion'
    print("All core imports successful!")

if __name__ == "__main__":
    test_imports()
