import random

class pacient:
    def __init__(self):
        self.memory = random.randint(0, 100)
        self.template = None

        # common with National data base
        self.name = None
        self.cpf = None
        self.rg = None
        self.birth_date = None

        self.current_health = None
        self.current_medication = None
        self.vaccine = None


    def rng_forgot_data(self):
        forgetfullness = random.randint(0, 100)
        if self.memory > forgetfullness:
            return False
    
        return True
        