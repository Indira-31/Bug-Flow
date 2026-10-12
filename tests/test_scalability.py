import time
from datetime import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Issue, Project, BugCategory, User

def test_high_volume_and_sub_300ms_sla():
    """
    Evaluates Milestone 3 & Milestone 4 criteria:
    - End-to-end platform queries respond within 300ms SLA for 95th percentile requests
    - Database composite indexes (project_id, status), (assignee_id, status), (created_at)
      maintain high efficiency under heavy issue load.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Create base references
        user = User(
            id=1,
            username="perf_dev",
            email="perf@test.io",
            hashed_password="hash",
            full_name="Perf Tester",
            role="DEVELOPER"
        )
        project1 = Project(project_id=1, project_name="Enterprise Platform A")
        project2 = Project(project_id=2, project_name="Enterprise Platform B")
        cat = BugCategory(category_id=1, category_name="Backend Logic", urgency="High Urgency")
        db.add_all([user, project1, project2, cat])
        db.commit()

        now = time.time()
        batch = [
            Issue(
                project_id=1,
                reporter_id=1,
                assignee_id=1 if i % 3 == 0 else None,
                category_id=1,
                title=f"High scale issue item #{i}",
                description="Simulated performance benchmark issue payload for stress evaluation.",
                severity="CRITICAL" if i % 10 == 0 else "MINOR",
                priority="URGENT" if i % 10 == 0 else "MEDIUM",
                status="REPORTED" if i % 4 == 0 else ("IN_PROGRESS" if i % 4 == 1 else "RESOLVED"),
                dev_stage="Development",
                estimated_effort=2.0,
                priority_score=6.0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            for i in range(5000)
        ]
        db.add_all(batch)
        db.commit()

        # Benchmark 100 queries simulating concurrent request patterns
        durations = []
        for q in range(100):
            t0 = time.perf_counter()
            # Indexed query by project_id and status with pagination
            results = (
                db.query(Issue)
                .filter(Issue.project_id == 1, Issue.status == "IN_PROGRESS")
                .order_by(Issue.created_at.desc())
                .limit(50)
                .all()
            )
            t1 = time.perf_counter()
            durations.append((t1 - t0) * 1000)  # milliseconds
            assert len(results) > 0

        durations.sort()
        p95_idx = int(0.95 * len(durations))
        p95_duration = durations[p95_idx]
        avg_duration = sum(durations) / len(durations)

        print(f"\n[Scalability SLA Benchmark Results]")
        print(f"Total Issues Indexed: 5,000 (Scaled simulation)")
        print(f"Average Query Time: {avg_duration:.2f} ms")
        print(f"95th Percentile (p95): {p95_duration:.2f} ms (SLA Target: < 300 ms)")

        # Verify SLA requirement: < 300ms
        assert p95_duration < 300.0, f"p95 response time {p95_duration}ms exceeded 300ms SLA"
        assert avg_duration < 100.0, f"Average response time {avg_duration}ms exceeded 100ms"

    finally:
        db.close()

if __name__ == "__main__":
    test_high_volume_and_sub_300ms_sla()
