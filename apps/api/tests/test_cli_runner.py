import argparse

from scripts.kairo_cli import (
    check_continuity_cli,
    scan_anomalies_cli,
    trigger_handoff_cli,
    verify_acl_cli,
)


def test_cli_trigger_handoff() -> None:
    args = argparse.Namespace(
        org="snapmeet",
        task="BILL-204",
        repo="snapmeet/billing-service",
        from_dev="Rahul Sharma",
        to_dev="Aman Verma",
    )
    code = trigger_handoff_cli(args)
    assert code == 0


def test_cli_scan_anomalies() -> None:
    args = argparse.Namespace(
        org="snapmeet",
        repo="snapmeet/billing-service",
    )
    code = scan_anomalies_cli(args)
    assert code == 0


def test_cli_check_continuity() -> None:
    args = argparse.Namespace(
        org="snapmeet",
    )
    code = check_continuity_cli(args)
    assert code == 0


def test_cli_verify_acl_restricted() -> None:
    args = argparse.Namespace(
        org="snapmeet",
        user="usr_aman",
        repo="snapmeet/executive-financials",
    )
    code = verify_acl_cli(args)
    assert code == 1  # Blocked


def test_cli_verify_acl_allowed() -> None:
    args = argparse.Namespace(
        org="snapmeet",
        user="usr_aman",
        repo="snapmeet/billing-service",
    )
    code = verify_acl_cli(args)
    assert code == 0  # Granted
