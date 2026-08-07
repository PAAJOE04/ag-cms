"""Role-based permission definitions."""

ROLE_PERMISSIONS = {
    'developer': {
        'all': True,
    },
    'super_admin': {
        'members': ['all'],
        'attendance': ['all'],
        'finance': ['all'],
        'events': ['all'],
        'departments': ['all'],
        'communication': ['all'],
        'reports': ['all'],
        'ai': ['all'],
        'admin': ['view', 'create', 'edit', 'audit'],
        'users': ['all'],
    },
    'church_admin': {
        'members': ['all'],
        'attendance': ['all'],
        'finance': ['view'],
        'events': ['all'],
        'departments': ['view', 'edit'],
        'communication': ['all'],
        'reports': ['view', 'export'],
        'ai': ['view'],
        'visitors': ['all'],
    },
    'finance_officer': {
        'finance': ['all'],
        'reports': ['view', 'export'],
        'members': ['view'],
    },
    'department_leader': {
        'departments': ['view', 'edit'],
        'attendance': ['view', 'create'],
        'events': ['view', 'create'],
        'members': ['view'],
        'reports': ['view'],
    },
    'attendance_officer': {
        'attendance': ['all'],
        'members': ['view', 'search'],
        'reports': ['view'],
    },
    'member': {
        'members': ['view_own'],
        'attendance': ['view_own'],
        'events': ['view'],
        'communication': ['view'],
    },
}


def get_permissions_for_role(role_name):
    """Return permission dict for a role name."""
    return ROLE_PERMISSIONS.get(role_name, ROLE_PERMISSIONS['member'])
