import base64
import streamlit as st
from src.config.settings import Config

class Helpers:
    @staticmethod
    @st.cache_data(ttl=3600)
    def get_base64_image(image_path):
        """
        Converts an image to base64 string. Returns a placeholder SVG if image not found.
        """
        try:
            with open(image_path, "rb") as img_file: 
                return base64.b64encode(img_file.read()).decode()
        except FileNotFoundError: 
            # Return a simple SVG placeholder as base64
            placeholder_svg = '''<svg width="80" height="80" xmlns="http://www.w3.org/2000/svg">
                <rect width="80" height="80" fill="#007bff"/>
                <text x="40" y="45" font-size="40" text-anchor="middle" fill="white">H</text>
            </svg>'''
            return base64.b64encode(placeholder_svg.encode()).decode()
        except Exception as e: 
            return ""

    @staticmethod
    def logo_exists():
        """Check if logo.png exists."""
        return Config.LOGO_PATH.exists()
