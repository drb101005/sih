def test_import():
    from maintenance_optimizer import Optimiser
    assert Optimiser is not None

def test_resource_parser():
    from maintenance_optimizer.optimizer import CP_SATOptimizer
    assert CP_SATOptimizer._resources("A;B") == ["A", "B"]
