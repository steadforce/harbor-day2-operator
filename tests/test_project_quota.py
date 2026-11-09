"""Tests for the storage quota sync of existing projects (src/projects.py)."""

import asyncio
import logging
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from harborapi.models import Quota, ResourceList

from projects import sync_project_quota, update_or_create_projects

GIB = 1024**3
LOGGER = logging.getLogger("test")


class FakeClient:
    """Records the calls of the operator; get_quotas answers with the given quotas."""

    def __init__(self, quotas=None, fail_on=None):
        self.quotas = quotas if quotas is not None else []
        self.fail_on = fail_on
        self.calls = []

    async def update_project(self, project_name_or_id, project):
        self.calls.append(("update_project", project_name_or_id))

    async def create_project(self, project):
        self.calls.append(("create_project", project["project_name"]))

    async def get_quotas(self, reference=None, reference_id=None, **kwargs):
        self.calls.append(("get_quotas", reference, reference_id))
        if self.fail_on == "get_quotas":
            raise RuntimeError("boom")
        return self.quotas

    async def update_quota(self, id, quota):
        self.calls.append(("update_quota", id, quota.hard.root["storage"]))
        if self.fail_on == "update_quota":
            raise RuntimeError("boom")


def quota(storage):
    return Quota(id=7, hard=ResourceList(root={"storage": storage}))


PROJECT = SimpleNamespace(project_id=42, name="buildcache")


def run(client, target):
    asyncio.run(sync_project_quota(client, PROJECT, target, LOGGER))
    return [c for c in client.calls if c[0] != "get_quotas"]


def test_raises_the_quota_when_it_differs():
    c = FakeClient([quota(100 * GIB)])
    assert run(c, {"project_name": "buildcache", "storage_limit": 200 * GIB}) == [
        ("update_quota", 7, 200 * GIB)
    ]
    assert ("get_quotas", "project", "42") in c.calls


def test_does_nothing_when_the_quota_matches():
    c = FakeClient([quota(200 * GIB)])
    assert run(c, {"project_name": "buildcache", "storage_limit": 200 * GIB}) == []


def test_unlimited_matches_unlimited():
    c = FakeClient([quota(-1)])
    assert run(c, {"project_name": "buildcache", "storage_limit": -1}) == []


def test_sets_unlimited_when_configured():
    c = FakeClient([quota(100 * GIB)])
    assert run(c, {"project_name": "buildcache", "storage_limit": -1}) == [
        ("update_quota", 7, -1)
    ]


def test_without_storage_limit_nothing_is_called():
    c = FakeClient([quota(100 * GIB)])
    assert run(c, {"project_name": "buildcache"}) == []
    assert c.calls == []


def test_not_exactly_one_quota_changes_nothing():
    assert (
        run(FakeClient([]), {"project_name": "buildcache", "storage_limit": GIB}) == []
    )
    two = FakeClient([quota(GIB), quota(GIB)])
    assert run(two, {"project_name": "buildcache", "storage_limit": 2 * GIB}) == []


def test_api_errors_are_logged_and_not_raised():
    for step in ("get_quotas", "update_quota"):
        c = FakeClient([quota(GIB)], fail_on=step)
        run(c, {"project_name": "buildcache", "storage_limit": 2 * GIB})


def test_existing_project_is_updated_then_quota_synced_new_project_only_created():
    c = FakeClient([quota(100 * GIB)])
    targets = [
        {"project_name": "buildcache", "storage_limit": 200 * GIB},
        {"project_name": "fresh", "storage_limit": 5 * GIB},
    ]
    asyncio.run(update_or_create_projects(c, targets, {"buildcache": PROJECT}, LOGGER))
    assert [x[0] for x in c.calls] == [
        "update_project",
        "get_quotas",
        "update_quota",
        "create_project",
    ]
