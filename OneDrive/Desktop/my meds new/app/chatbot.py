from flask import Blueprint, request, jsonify, render_template
import re

chatbot = Blueprint('chatbot', __name__)

CRISIS_KEYWORDS = ['suicide', 'kill', 'die', 'harm', 'dead']
NEG_KEYWORDS = ['sad', 'depressed', 'anxious', 'worried', 'bad', 'panic', 'stress']
POS_KEYWORDS = ['happy', 'good', 'great', 'fine', 'better', 'thanks']

def get_sentiment_score(text):
    text = text.lower()
    score = 0.0
    
    # Simple counting scorer
    words = re.findall(r'\w+', text)
    count = len(words)
    if count == 0: return 0.0
    
    for w in words:
        if w in NEG_KEYWORDS: score -= 0.5
        if w in POS_KEYWORDS: score += 0.5
        
    # Clamp -1 to 1
    return max(min(score, 1.0), -1.0)

def generate_response(text):
    text_lower = text.lower()
    
    # High risk check
    if any(k in text_lower for k in CRISIS_KEYWORDS):
        return {
            'reply': "I am concerned about what you're saying. If you are in immediate danger, please call 911 or your local emergency services immediately. This is not medical advice.",
            'intent': 'crisis',
            'score': -1.0
        }
        
    score = get_sentiment_score(text)
    
    # Simple Intent matching
    if 'appointment' in text_lower:
        return {'reply': "You can view and book appointments in the Appointments section.", 'intent': 'info_appt', 'score': score}
    
    if 'medicine' in text_lower or 'pill' in text_lower:
        return {'reply': "Don't forget to log your medicines in the Dashboard.", 'intent': 'info_meds', 'score': score}
        
    if score <= -0.3:
        return {'reply': "I'm sorry to hear you're feeling down. Have you tried taking a short walk or practicing deep breathing? (Not medical advice)", 'intent': 'mood_neg', 'score': score}
    
    if score >= 0.3:
        return {'reply': "That's great to hear! Keeping a positive mindset helps with recovery.", 'intent': 'mood_pos', 'score': score}
        
    return {'reply': "I see. How else can I help you today?", 'intent': 'smalltalk', 'score': score}

@chatbot.route('/chat')
def chat_ui():
    return render_template('chatbot.html')

@chatbot.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.get_json()
    message = data.get('message', '')
    
    response = generate_response(message)
    return jsonify(response)