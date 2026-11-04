from ..extensions import db
from ..models import ActivityLog


def log(user_id, action, entity_type, entity_id=None, before=None, after=None):
    entry = ActivityLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_state=before,
        after_state=after,
    )
    db.session.add(entry)
    db.session.commit()
    return entry


def list_recent(limit=25):
    entries = (
        ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(limit).all()
    )
    return [entry.to_dict() for entry in entries]
