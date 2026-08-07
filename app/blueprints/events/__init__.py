"""Events management blueprint."""
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models.event import Event, EventRegistration, EventVolunteer
from app.models.member import Member
from app.models.department import Department
from app.utils.decorators import permission_required
from app.utils.helpers import audit_action, paginate_query

events_bp = Blueprint('events', __name__)


@events_bp.route('/')
@login_required
@permission_required('events:view')
def index():
    """List events."""
    status = request.args.get('status', 'upcoming')
    query = Event.query
    if status == 'upcoming':
        query = query.filter(
            Event.start_date >= datetime.utcnow(),
            Event.status == 'upcoming'
        )
    elif status == 'past':
        query = query.filter(Event.start_date < datetime.utcnow())

    events_list = paginate_query(query.order_by(Event.start_date))
    return render_template('events/index.html', events=events_list, status=status)


@events_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('events:create')
def create():
    """Create a new event."""
    departments = Department.query.filter_by(is_active=True).all()

    if request.method == 'POST':
        event = Event(
            title=request.form['title'],
            description=request.form.get('description'),
            event_type=request.form['event_type'],
            location=request.form.get('location'),
            start_date=datetime.strptime(
                request.form['start_date'], '%Y-%m-%dT%H:%M'
            ),
            end_date=datetime.strptime(
                request.form['end_date'], '%Y-%m-%dT%H:%M'
            ) if request.form.get('end_date') else None,
            max_attendees=request.form.get('max_attendees', type=int),
            is_registration_required=bool(request.form.get('is_registration_required')),
            department_id=request.form.get('department_id', type=int) or None,
            created_by_id=current_user.id,
        )
        db.session.add(event)
        audit_action('create', 'events', f'Created event: {event.title}')
        db.session.commit()
        flash(f'Event "{event.title}" created.', 'success')
        return redirect(url_for('events.view', id=event.id))

    return render_template('events/create.html', departments=departments,
                           event_types=Event.EVENT_TYPES)


@events_bp.route('/<int:id>')
@login_required
@permission_required('events:view')
def view(id):
    """View event details."""
    event = Event.query.get_or_404(id)
    registrations = event.registrations.all()
    volunteers = event.volunteers.all()
    members = Member.query.filter_by(membership_status='active').order_by(Member.last_name).all()
    return render_template(
        'events/view.html',
        event=event,
        registrations=registrations,
        volunteers=volunteers,
        members=members,
    )


@events_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@permission_required('events:create')
def delete(id):
    """Delete an event."""
    event = Event.query.get_or_404(id)
    title = event.title
    db.session.delete(event)
    audit_action('delete', 'events', f'Deleted event: {title}')
    db.session.commit()
    flash(f'Event "{title}" deleted.', 'success')
    return redirect(url_for('events.index'))


@events_bp.route('/<int:id>/register', methods=['POST'])
@login_required
@permission_required('events:create')
def register(id):
    """Register a member for an event."""
    event = Event.query.get_or_404(id)
    member_id = request.form.get('member_id', type=int)

    existing = EventRegistration.query.filter_by(
        event_id=event.id, member_id=member_id
    ).first()
    if existing:
        flash('Member already registered.', 'warning')
    else:
        reg = EventRegistration(event_id=event.id, member_id=member_id)
        db.session.add(reg)
        db.session.commit()
        flash('Registration successful.', 'success')

    return redirect(url_for('events.view', id=event.id))
