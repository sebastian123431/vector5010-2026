# Herramienta generada automáticamente por Vector
# Descripción: Compara y verifica si un número es par o impar
# Fecha de creación: 2026-09-08

def comparar_pares(numero: int):
    """
    Compara y verifica si un número dado es par o impar.
    """
    if numero % 2 == 0:
        print(f"{numero} es par.")
        return True
    else:
        print(f"{numero} no es par.")
        return False

# Ejemplo de uso ejecutable
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        num = int(sys.argv[1])
    else:
        num = 4
    print(f"Probando con {num}:")
    comparar_pares(num)
