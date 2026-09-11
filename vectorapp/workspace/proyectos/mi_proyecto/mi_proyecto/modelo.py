class Usuario:
    def __init__(self, nombre):
        self.nombre = nombre

    def saludar(self):
        return f'Hola {self.nombre}'
