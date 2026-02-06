from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import Medicine, DoseLog, db, ReminderQueue
from app.utils import calculate_adherence
from datetime import datetime

medicines = Blueprint('medicines', __name__)

@medicines.route('/medicines')
@login_required
def index():
    user_medicines = Medicine.query.filter_by(user_id=current_user.id).all()
    meds_data = []
    for med in user_medicines:
        meds_data.append({
            'medicine': med,
            'adherence': calculate_adherence(med.id)
        })
    return render_template('medicines.html', medicines=meds_data)

@medicines.route('/api/medicines', methods=['GET', 'POST'])
@login_required
def api_medicines():
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data'}), 400
            
        try:
            times = data.get('times', [])
            import json
            times_json = json.dumps(times)
            
            start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d')
            end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d') if data.get('end_date') else None
            
            med = Medicine(
                user_id=current_user.id,
                name=data['name'],
                dose=data['dose'],
                times=times_json,
                start_date=start_date,
                end_date=end_date
            )
            db.session.add(med)
            db.session.commit()
            
            # Trigger scheduler update or queue reminders (handled by background job usually, 
            # but for MVP we might just let the cron pick it up)
            
            return jsonify({'message': 'Medicine added', 'id': med.id}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 400
            
    # GET list
    meds = Medicine.query.filter_by(user_id=current_user.id).all()
    results = []
    for m in meds:
        results.append({
            'id': m.id,
            'name': m.name,
            'dose': m.dose,
            'times': m.get_times_list(),
            'adherence': calculate_adherence(m.id)
        })
    return jsonify(results)

@medicines.route('/api/medicines/<int:id>/log', methods=['POST'])
@login_required
def log_dose(id):
    med = Medicine.query.get_or_404(id)
    if med.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.get_json()
    try:
        scheduled_dt = datetime.strptime(data.get('scheduled_datetime'), '%Y-%m-%dT%H:%M:%S')
    except:
        scheduled_dt = datetime.now() # Fallback
        
    log = DoseLog(
        medicine_id=med.id,
        scheduled_datetime=scheduled_dt,
        taken=data.get('taken', True)
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'message': 'Dose logged', 'adherence': calculate_adherence(med.id)})

@medicines.route('/api/medicines/<int:id>', methods=['DELETE'])
@login_required
def delete_medicine(id):
    med = Medicine.query.get_or_404(id)
    if med.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    db.session.delete(med)
    db.session.commit()
    return jsonify({'message': 'Deleted'})