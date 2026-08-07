"""SMS delivery service.

Default provider is 'log': messages are recorded in the SmsLog table but no
real text message is sent. Swap in a real gateway (Twilio, local aggregator)
by implementing the provider below and setting SMS_PROVIDER.
"""
from flask import current_app

from app.extensions import db
from app.models.communication import SmsLog
from app.models.department import DepartmentMember
from app.models.member import Member


def _send(recipient_name, recipient_phone, message, announcement, department_name=None):
    """Record an SMS according to the configured provider."""
    provider = current_app.config.get('SMS_PROVIDER', 'log')
    status = 'sent'
    try:
        if provider == 'twilio':
            status = _send_twilio(recipient_phone, message)
    except Exception:
        status = 'failed'
        current_app.logger.exception('SMS send failed for %s', recipient_phone)

    log = SmsLog(
        announcement_id=announcement.id if announcement else None,
        recipient_name=recipient_name,
        recipient_phone=recipient_phone,
        department_name=department_name,
        message=message,
        status=status,
        provider=provider,
    )
    db.session.add(log)
    return status


def _send_twilio(phone, message):
    """Send via Twilio (requires TWILIO_* env vars)."""
    from twilio.rest import Client

    client = Client(
        current_app.config['TWILIO_ACCOUNT_SID'],
        current_app.config['TWILIO_AUTH_TOKEN'],
    )
    client.messages.create(
        body=message,
        from_=current_app.config['TWILIO_FROM_NUMBER'],
        to=phone,
    )
    return 'sent'


def notify_announcement(announcement):
    """Send SMS to all target members of an announcement.

    If a department is targeted, only its active members receive it,
    otherwise all active members with a phone number.
    """
    query = db.session.query(Member).join(
        DepartmentMember, DepartmentMember.member_id == Member.id
    ).filter(
        DepartmentMember.is_active == True,  # noqa: E712
        DepartmentMember.department_id == announcement.target_department_id,
        Member.is_visitor == False,  # noqa: E712
        Member.membership_status == 'active',
        Member.phone.isnot(None),
        Member.phone != '',
    ) if announcement.target_department_id else Member.query.filter(
        Member.is_visitor == False,  # noqa: E712
        Member.membership_status == 'active',
        Member.phone.isnot(None),
        Member.phone != '',
    )

    department_name = (
        announcement.target_department.name
        if announcement.target_department else None
    )
    message = (
        f'{announcement.title}\n'
        f'{announcement.content}\n'
        f'— {current_app.config.get("CHURCH_NAME", "")}'
    )

    sent = 0
    for member in query.all():
        status = _send(
            member.full_name,
            member.phone,
            message,
            announcement,
            department_name,
        )
        if status == 'sent':
            sent += 1

    if sent:
        db.session.commit()
    return sent
