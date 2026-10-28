from banco import conectar

conexao = conectar()

try:
    with conexao.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_user;")
        banco, usuario = cursor.fetchone()

    print("Conexão realizada com sucesso!")
    print(f"Banco: {banco}")
    print(f"Usuário: {usuario}")
finally:
    conexao.close()