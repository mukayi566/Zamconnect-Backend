import random

def generate_ssn():
    """
    Generates a random 10-digit Social Security Number (SSN).
    Format: XXXXXXXXXX
    """
    return "".join([str(random.randint(0, 9)) for _ in range(10)])
