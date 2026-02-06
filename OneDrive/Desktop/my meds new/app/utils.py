from datetime import datetime, timedelta
from app.models import DoseLog, Medicine, db
from sqlalchemy import  and_

def calculate_adherence(medicine_id):
    """
    Calculate adherence percentage for a medicine.
    Adherence = (taken doses / scheduled doses) * 100
    Scheduled doses are calculated from start_date up to now.
    """
    medicine = db.session.get(Medicine, medicine_id)
    if not medicine:
        return 0.0

    if not medicine.start_date:
        return 0.0
        
    start_date = medicine.start_date
    end_date = medicine.end_date if medicine.end_date and medicine.end_date < datetime.utcnow() else datetime.utcnow()
    
    # Simple calculation: Count how many times it SHOULD have been taken
    # This is complex because of "times" array. 
    # For MVP: Iterate days from start to end and count occurrences
    
    times = medicine.get_times_list() # e.g. ["09:00", "21:00"]
    if not times:
        return 0.0
        
    scheduled_count = 0
    current_day = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_day = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    while current_day <= end_day:
        for time_str in times:
            # Parse time
            try:
                h, m = map(int, time_str.split(':'))
                scheduled_time = current_day.replace(hour=h, minute=m)
                if scheduled_time <= end_date:
                    scheduled_count += 1
            except:
                continue
        current_day += timedelta(days=1)
        
    if scheduled_count == 0:
        return 100.0 if medicine.start_date <= end_date else 0.0

    # Count actual taken logs
    # We count ALL taken logs for this medicine. 
    # Ideally should filter by date range but for now all logs implies within range.
    taken_count = DoseLog.query.filter_by(medicine_id=medicine_id, taken=True).count()
    
    if taken_count > scheduled_count:
        return 100.0 # Cap at 100
        
    return round((taken_count / scheduled_count) * 100, 1)