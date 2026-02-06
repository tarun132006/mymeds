from flask import Blueprint, request, jsonify, render_template, abort
from flask_login import login_required, current_user
from app.models import Appointment, db
from datetime import datetime, timedelta

appointments = Blueprint('appointments', __name__)

@appointments.route('/appointments')
@login_required
def index():
    # Show upcoming first
    upcoming = Appointment.query.filter(
        Appointment.user_id == current_user.id,
        Appointment.appointment_datetime >= datetime.utcnow()
    ).order_by(Appointment.appointment_datetime).all()
    
    past = Appointment.query.filter(
        Appointment.user_id == current_user.id,
        Appointment.appointment_datetime < datetime.utcnow()
    ).order_by(Appointment.appointment_datetime.desc()).all()
    
    return render_template('appointments.html', upcoming=upcoming, past=past)

@appointments.route('/api/appointments', methods=['GET', 'POST'])
@login_required
def api_appointments():
    if request.method == 'POST':
        data = request.get_json()
        title = data.get('title')
        dt_str = data.get('datetime')
        description = data.get('description', '')
        
        try:
            appt_dt = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
            
        # Conflict detection: +/- 30 minutes
        # Find any appointment where abs(appt_dt - existing.dt) < 30 mins
        start_check = appt_dt - timedelta(minutes=29) # inclusive check might be strict, let's say < 30 mins
        end_check = appt_dt + timedelta(minutes=29)
        
        conflict = Appointment.query.filter(
            Appointment.user_id == current_user.id,
            Appointment.status != 'cancelled',
            Appointment.appointment_datetime >= start_check,
            Appointment.appointment_datetime <= end_check
        ).first()
        
        if conflict:
            return jsonify({'error': 'Conflict: You have an overlapping appointment', 'code': 409}), 409
            
        new_appt = Appointment(
            user_id=current_user.id,
            title=title,
            description=description,
            appointment_datetime=appt_dt
        )
        db.session.add(new_appt)
        db.session.commit()
        
        return jsonify({'message': 'Appointment booked', 'id': new_appt.id}), 201
        
    # GET list
    appts = Appointment.query.filter_by(user_id=current_user.id).order_by(Appointment.appointment_datetime).all()
    return jsonify([{
        'id': a.id,
        'title': a.title,
        'datetime': a.appointment_datetime.isoformat(),
        'status': a.status
    } for a in appts])

@appointments.route('/api/appointments/<int:id>', methods=['DELETE'])
@login_required
def delete_appointment(id):
    appt = Appointment.query.get_or_404(id)
    if appt.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    appt.status = 'cancelled' # Soft delete or actual delete? Prompt says DELETE endpoint.
    # Usually better to soft delete for record, but let's just delete to keep it simple/clean as per typical crud.
    # actually requirement is just DELETE /api/appointments/<id>. I'll hard delete.
    db.session.delete(appt)
    db.session.commit()
    return jsonify({'message': 'Deleted'})