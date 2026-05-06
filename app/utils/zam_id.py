import random
import string
from datetime import datetime

def generate_zam_id():
    """
    Generates a unique ZamID in format: ZAM-YY-XXXXXX
    YY = Last two digits of current year
    XXXXXX = Random uppercase alphanumeric chars
    Example: ZAM-26-A1B2C3
    """
    year = str(datetime.now().year)[2:]
    # Exclude I, O, 0, 1 to avoid confusion
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    random_part = ''.join(random.choices(chars, k=6))
    return f"ZAM-{year}-{random_part}"
