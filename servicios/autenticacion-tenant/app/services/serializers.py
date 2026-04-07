def serializar_usuario(usuario):
    return {
        "id": str(usuario.id),
        "institucion_id": str(usuario.institucion_id),
        "nombre": usuario.nombre,
        "apellido": usuario.apellido,
        "correo": usuario.correo,
        "estado": usuario.estado,
        "roles": [
            {
                "id": str(rel.rol.id),
                "nombre": rel.rol.nombre
            }
            for rel in usuario.roles
        ]
    }

def serializar_rol(rol):
    return {
        "id": str(rol.id),
        "nombre": rol.nombre
    }