import bcrypt

def check_password(plain_password: str, hashed_password: str) -> bool:
    # Convertir la contraseña en texto plano a bytes
    plain_password_bytes = plain_password.encode('utf-8')
    
    # Convertir el hash a bytes
    hashed_password_bytes = hashed_password.encode('utf-8')
    
    # Verificar si la contraseña en texto plano coincide con el hash
    return bcrypt.checkpw(plain_password_bytes, hashed_password_bytes)

# Ejemplo de uso
plain_password = "miContraseñaSegura123"
hashed_password = "$2b$10$nebR7sHCGyK9xytp5WFfiec1XRGsCpkOF0pNqd7Vpfq4DOX52LeEC"  # Este es el hash bcrypt de la contraseña

if check_password(plain_password, hashed_password):
    print("La contraseña es correcta.")
else:
    print("La contraseña es incorrecta.")
