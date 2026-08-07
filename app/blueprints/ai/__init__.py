"""AI Assistant blueprint."""
from flask import Blueprint, flash, jsonify, render_template, request
from flask_login import login_required

from app.services.ai_service import AIService
from app.utils.decorators import permission_required

ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/')
@login_required
@permission_required('ai:view')
def index():
    """AI assistant chat interface."""
    return render_template('ai/index.html')


@ai_bp.route('/ask', methods=['POST'])
@login_required
@permission_required('ai:view')
def ask():
    """Process AI query."""
    question = request.form.get('question', '').strip()
    if not question:
        return jsonify({'error': 'Please enter a question.'}), 400

    service = AIService()
    response = service.query(question)
    return jsonify({'question': question, 'response': response})


@ai_bp.route('/suggestions')
@login_required
@permission_required('ai:view')
def suggestions():
    """Return suggested questions."""
    return jsonify({
        'suggestions': [
            'How many new members joined this year?',
            'Which members have missed four consecutive Sunday services?',
            'Generate this week\'s church announcement.',
            'Summarize this month\'s financial report.',
            'Predict next Sunday\'s attendance.',
            'Which department is growing the fastest?',
            'Show birthdays for this month.',
        ]
    })
