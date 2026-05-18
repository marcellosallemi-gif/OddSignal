from app.models import Alert


def save_alert(db, alert_data):
    alert = Alert(**alert_data)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert
