"""
Compatibility layer for backward compatibility
This file provides imports from the new structure with old names
"""

# Import from new structure
from src.ui.styles import CSS, inject_custom_css
from src.services.email_service import send_email, email_defaulters

# Export with old interface
__all__ = ['CSS', 'inject_custom_css', 'send_email', 'email_defaulters']
