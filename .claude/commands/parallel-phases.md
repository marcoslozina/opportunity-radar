Ejecutá spec y design del cambio actual en paralelo siguiendo este protocolo:

1. Verificar que existe una propuesta aprobada en Engram:
   - mem_search(query: "sdd/{cambio-actual}/proposal")
   - Si no existe → STOP y decir "Necesitás aprobar una propuesta primero con /sdd-new"

2. Recuperar la propuesta completa:
   - mem_get_observation(id: {id-encontrado})

3. Lanzar los dos agentes en paralelo (delegate, NO task):
   - Agente A: sdd-spec con la propuesta como contexto
   - Agente B: sdd-design con la propuesta como contexto
   - Cada uno debe guardar su artefacto en Engram antes de terminar

4. Esperar ambos resultados.

5. Presentar al usuario:
   - Resumen de 3-4 bullets del spec
   - Resumen de 3-4 bullets del design
   - Puntos donde spec y design podrían estar en tensión (si los hay)

6. Preguntar: "¿El spec cubre todos los casos? ¿El diseño tiene sentido? ¿Arrancamos con las tasks?"
