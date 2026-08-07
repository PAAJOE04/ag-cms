"""Members management blueprint."""
import os
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.attendance import Attendance
from app.models.department import Department, DepartmentMember
from app.models.event import EventRegistration, EventVolunteer
from app.models.finance import Transaction
from app.models.follow_up import FollowUp
from app.models.member import Member, Family, EmergencyContact, Visitor
from app.models.user import User
from app.utils.decorators import permission_required
from app.utils.helpers import audit_action, paginate_query, save_upload

members_bp = Blueprint('members', __name__)


@members_bp.route('/')
@login_required
@permission_required('members:view')
def index():
    """List all members."""
    query = Member.query.filter_by(is_visitor=False)
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '')

    if search:
        query = query.filter(
            db.or_(
                Member.first_name.ilike(f'%{search}%'),
                Member.last_name.ilike(f'%{search}%'),
                Member.membership_id.ilike(f'%{search}%'),
                Member.email.ilike(f'%{search}%'),
            )
        )
    if status:
        query = query.filter_by(membership_status=status)

    members = paginate_query(query.order_by(Member.last_name, Member.first_name))
    return render_template('members/index.html', members=members, search=search, status=status)


@members_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('members:create')
def create():
    """Register a new member."""
    if request.method == 'POST':
        def _parse_date(value):
            if not value:
                return None
            try:
                return datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                return 'invalid'

        date_of_birth = _parse_date(request.form.get('date_of_birth'))
        baptism_date = _parse_date(request.form.get('baptism_date'))
        if date_of_birth == 'invalid' or baptism_date == 'invalid':
            flash('One of the dates is invalid. Please check and try again.', 'danger')
            return render_template('members/create.html')
        if not request.form.get('first_name') or not request.form.get('last_name'):
            flash('First name and last name are required.', 'danger')
            return render_template('members/create.html')
        if not request.form.get('phone', '').strip():
            flash('Phone number is required — members receive church SMS updates on it.', 'danger')
            return render_template('members/create.html')

        saved = None
        save_error = False
        for attempt in range(5):
            member = Member(
                membership_id=Member.generate_membership_id(),
                first_name=request.form['first_name'],
                last_name=request.form['last_name'],
                middle_name=request.form.get('middle_name'),
                gender=request.form.get('gender'),
                email=request.form.get('email'),
                phone=request.form.get('phone'),
                address=request.form.get('address'),
                city=request.form.get('city'),
                occupation=request.form.get('occupation'),
                marital_status=request.form.get('marital_status'),
                membership_status='active',
                membership_date=datetime.utcnow().date(),
                created_by_id=current_user.id,
            )
            if date_of_birth:
                member.date_of_birth = date_of_birth
            if baptism_date:
                member.baptism_date = baptism_date
                member.baptism_place = request.form.get('baptism_place')

            if 'photo' in request.files:
                photo = save_upload(request.files['photo'], 'photos')
                if photo:
                    member.photo = photo

            db.session.add(member)
            db.session.flush()

            try:
                audit_action('create', 'members', f'Created member {member.membership_id}',
                             resource_type='member', resource_id=member.id)
                db.session.commit()
                saved = member
                break
            except IntegrityError:
                db.session.rollback()
            except Exception:
                db.session.rollback()
                save_error = True
                break

        if saved is not None:
            flash(f'Member {saved.full_name} registered successfully.', 'success')
            return redirect(url_for('members.view', id=saved.id))

        if save_error:
            flash('Something went wrong while saving. Nothing was lost — please try again.', 'danger')
        else:
            flash('Could not save the member because an ID conflict occurred. Please try again.', 'danger')
        return render_template('members/create.html')

    return render_template('members/create.html')


@members_bp.route('/<int:id>')
@login_required
@permission_required('members:view')
def view(id):
    """View member profile."""
    member = Member.query.get_or_404(id)
    departments = DepartmentMember.query.filter_by(
        member_id=member.id, is_active=True
    ).all()
    transactions = Transaction.query.filter_by(member_id=member.id).order_by(
        Transaction.transaction_date.desc(), Transaction.id.desc()
    ).all()
    total_giving = sum(
        float(tx.amount) for tx in transactions if tx.type == 'income'
    )
    return render_template(
        'members/view.html',
        member=member,
        departments=departments,
        transactions=transactions,
        total_giving=total_giving,
    )


@members_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@permission_required('members:edit')
def delete(id):
    """Delete a member and all related records."""
    member = Member.query.get_or_404(id)
    name = member.full_name
    membership_id = member.membership_id

    for dept in Department.query.filter_by(leader_id=member.id).all():
        dept.leader_id = None
    DepartmentMember.query.filter_by(member_id=member.id).delete(synchronize_session=False)
    Attendance.query.filter_by(member_id=member.id).delete(synchronize_session=False)
    EventRegistration.query.filter_by(member_id=member.id).delete(synchronize_session=False)
    EventVolunteer.query.filter_by(member_id=member.id).delete(synchronize_session=False)
    FollowUp.query.filter_by(member_id=member.id).delete(synchronize_session=False)

    for tx in Transaction.query.filter_by(member_id=member.id).all():
        tx.member_id = None
    for user in User.query.filter_by(member_id=member.id).all():
        user.member_id = None
    for visitor in Visitor.query.filter_by(converted_member_id=member.id).all():
        visitor.converted_member_id = None

    db.session.delete(member)
    db.session.commit()

    qr_path = os.path.join(
        current_app.config['UPLOAD_FOLDER'], 'qr_codes', f'{membership_id}.png'
    )
    if os.path.exists(qr_path):
        os.remove(qr_path)

    audit_action('delete', 'members', f'Deleted member {membership_id} ({name})',
                 resource_type='member', resource_id=id)
    flash(f'Member {name} deleted.', 'success')
    return redirect(url_for('members.index'))


@members_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('members:edit')
def edit(id):
    """Edit member profile."""
    member = Member.query.get_or_404(id)

    if request.method == 'POST':
        member.first_name = request.form['first_name']
        member.last_name = request.form['last_name']
        member.middle_name = request.form.get('middle_name')
        member.gender = request.form.get('gender')
        member.email = request.form.get('email')
        member.phone = request.form.get('phone')
        member.address = request.form.get('address')
        member.city = request.form.get('city')
        member.occupation = request.form.get('occupation')
        member.marital_status = request.form.get('marital_status')
        member.membership_status = request.form.get('membership_status', 'active')
        member.notes = request.form.get('notes')

        if 'photo' in request.files and request.files['photo'].filename:
            photo = save_upload(request.files['photo'], 'photos')
            if photo:
                member.photo = photo

        try:
            audit_action('update', 'members', f'Updated member {member.membership_id}',
                         resource_type='member', resource_id=member.id)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('Could not update the member because of a conflict. Please try again.', 'danger')
            return redirect(url_for('members.edit', id=member.id))
        except Exception:
            db.session.rollback()
            flash('Something went wrong while updating. Nothing was lost — please try again.', 'danger')
            return redirect(url_for('members.edit', id=member.id))

        flash('Member updated successfully.', 'success')
        return redirect(url_for('members.view', id=member.id))

    return render_template('members/edit.html', member=member)


@members_bp.route('/visitors')
@login_required
@permission_required('visitors:view')
def visitors():
    """List visitors."""
    visitors_list = paginate_query(
        Visitor.query.order_by(Visitor.visit_date.desc())
    )
    return render_template('members/visitors.html', visitors=visitors_list)


@members_bp.route('/visitors/create', methods=['GET', 'POST'])
@login_required
@permission_required('visitors:create')
def create_visitor():
    """Record a new visitor."""
    if request.method == 'POST':
        visitor = Visitor(
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            phone=request.form.get('phone'),
            email=request.form.get('email'),
            address=request.form.get('address'),
            visit_date=datetime.strptime(request.form['visit_date'], '%Y-%m-%d').date(),
            invited_by=request.form.get('invited_by'),
            how_heard=request.form.get('how_heard'),
            notes=request.form.get('notes'),
            recorded_by_id=current_user.id,
        )
        db.session.add(visitor)
        audit_action('create', 'visitors', f'Recorded visitor {visitor.first_name} {visitor.last_name}')
        db.session.commit()
        flash('Visitor recorded successfully.', 'success')
        return redirect(url_for('members.visitors'))

    return render_template('members/create_visitor.html')


@members_bp.route('/search')
@login_required
def search():
    """Smart member search API for attendance."""
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return {'results': []}

    members = Member.query.filter(
        Member.membership_status == 'active',
        db.or_(
            Member.first_name.ilike(f'%{q}%'),
            Member.last_name.ilike(f'%{q}%'),
            Member.membership_id.ilike(f'%{q}%'),
        )
    ).limit(10).all()

    return {
        'results': [
            {
                'id': m.id,
                'name': m.full_name,
                'membership_id': m.membership_id,
                'photo': m.photo,
            }
            for m in members
        ]
    }
