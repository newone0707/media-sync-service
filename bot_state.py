# User state management

USER_STATES = {}

def get_state(user_id):
    return USER_STATES.get(user_id, None)

def set_state(user_id, state):
    USER_STATES[user_id] = state

def clear_state(user_id):
    if user_id in USER_STATES:
        del USER_STATES[user_id]
