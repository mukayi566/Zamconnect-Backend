import random

def generate_zambian_nrc():
    """
    Generates a random Zambian NRC number in the format XXXXXX/XX/X
    """
    first_part = "".join([str(random.randint(0, 9)) for _ in range(6)])
    second_part = "".join([str(random.randint(0, 9)) for _ in range(2)])
    third_part = str(random.randint(1, 9)) # Usually 1 or 2
    
    return f"{first_part}/{second_part}/{third_part}"
