from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from app.models.sync_job import SyncJob
from app.tasks.sync import _run_job
from tests.helpers import create_user, seed_connected_account


class DummyTask:
    def __init__(self, task_id: str = "task-1", retries: int = 0, max_retries: int = 2):
        self.request = SimpleNamespace(id=task_id, retries=retries)
        self.max_retries = max_retries

    def retry(self, exc: Exception, countdown: int):
        raise RuntimeError(f"retry:{countdown}") from exc


def _create_sync_job(db: Session, user_id: str, account_id: str) -> SyncJob:
    job = SyncJob(user_id=user_id, ad_account_id=account_id, sync_type="initial", status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def test_sync_job_success_transition(db_session, monkeypatch):
    user = create_user(db_session, "sync-success@example.com")
    account = seed_connected_account(db_session, user)
    job = _create_sync_job(db_session, user.id, account.id)

    def _run_ok(db, row, mock_payload=None):
        row.progress = 100
        row.current_step = "done"
        db.commit()

    monkeypatch.setattr("app.tasks.sync.MetaSyncOrchestrator.run", _run_ok)
    monkeypatch.setattr("app.tasks.sync.MetaSyncOrchestrator.log", lambda *args, **kwargs: None)

    _run_job(DummyTask(), job.id, "initial")

    db_session.expire_all()
    refreshed = db_session.query(SyncJob).filter(SyncJob.id == job.id).first()
    assert refreshed is not None
    assert refreshed.status == "completed"
    assert refreshed.progress == 100
    assert refreshed.completed_at is not None


def test_sync_job_failure_persistence(db_session, monkeypatch):
    user = create_user(db_session, "sync-fail@example.com")
    account = seed_connected_account(db_session, user)
    job = _create_sync_job(db_session, user.id, account.id)

    def _run_fail(db, row, mock_payload=None):
        raise ValueError("hard failure")

    monkeypatch.setattr("app.tasks.sync.MetaSyncOrchestrator.run", _run_fail)
    monkeypatch.setattr("app.tasks.sync.MetaSyncOrchestrator.log", lambda *args, **kwargs: None)

    with pytest.raises(ValueError):
        _run_job(DummyTask(task_id="task-2", retries=2, max_retries=2), job.id, "initial")

    db_session.expire_all()
    refreshed = db_session.query(SyncJob).filter(SyncJob.id == job.id).first()
    assert refreshed is not None
    assert refreshed.status == "failed"
    assert refreshed.error_message is not None
    assert "hard failure" in refreshed.error_message
