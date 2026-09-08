from scripts.run_benchmark_eval import run_benchmark


def test_end_to_end_benchmark_scenario() -> None:
    assert run_benchmark() is True
