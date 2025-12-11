import os
import re

# Configurações
WORKFLOW_FILES = [
    '.github/workflows/flutter-nightly.yml',
    '.github/workflows/flutter-build.yml'
]
NEW_APP_NAME = "BMDesk"
OLD_APP_NAME = "RustDesk"

def apply_renaming(line):
    """
    Aplica a renomeação de RustDesk para BMDesk em uma linha,
    protegendo chaves críticas de infraestrutura do GitHub Actions.
    """
    # Evita alterar chaves críticas como 'repository:' ou 'uses:' que podem quebrar actions
    if "uses:" not in line and "repository:" not in line:
        # Substitui RustDesk por BMDesk (Case Sensitive)
        if OLD_APP_NAME in line:
            return line.replace(OLD_APP_NAME, NEW_APP_NAME)
    return line

def processar_arquivo(filepath):
    """
    Lê um arquivo de workflow, remove jobs indesejados (Linux, Mac, Web)
    e renomeia os artefatos.
    """
    if not os.path.exists(filepath):
        print(f"Aviso: O arquivo '{filepath}' não foi encontrado. Pulando...")
        return

    print(f"Processando: {filepath}...")

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    in_jobs_section = False
    skip_current_job = False
    jobs_indentation = -1 

    # Regex para identificar o início de um job (ex: "  build-linux:")
    # Captura a indentação (grupo 1) e o nome do job (grupo 2)
    job_regex = re.compile(r'^(\s+)([\w-]+):')

    for line in lines:
        stripped = line.strip()
        
        # Detectar a entrada na seção 'jobs:'
        if stripped == 'jobs:':
            in_jobs_section = True
            new_lines.append(line)
            continue

        # Se ainda não estamos em jobs, copiamos a linha aplicando renomeação (ex: nome do workflow)
        if not in_jobs_section:
            new_lines.append(apply_renaming(line))
            continue

        # Estamos dentro da seção jobs
        match = job_regex.match(line)
        
        # Se a linha corresponde a uma definição de chave (pode ser um job ou uma propriedade)
        if match:
            indent = len(match.group(1))
            name = match.group(2).lower()

            # Define a indentação padrão dos jobs na primeira vez que encontrar um
            if jobs_indentation == -1:
                jobs_indentation = indent

            # Se a indentação for igual à dos jobs, estamos definindo um NOVO job
            if indent == jobs_indentation:
                # Lógica de Filtro: Manter apenas Android e Windows
                # Verifica se o nome do job contém 'android' ou 'win'
                if 'android' in name or 'win' in name:
                    skip_current_job = False
                    print(f"  [MANTER] Job encontrado: {match.group(2)}")
                else:
                    skip_current_job = True
                    print(f"  [REMOVER] Job encontrado: {match.group(2)}")

        # Se estivermos em um bloco de job que deve ser pulado, ignoramos a linha
        if skip_current_job:
            continue

        # Adiciona a linha processada (com renomeação) ao novo conteúdo
        new_lines.append(apply_renaming(line))

    # Salvar o arquivo modificado
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"  -> Arquivo {filepath} atualizado com sucesso.\n")

if __name__ == "__main__":
    print("-" * 40)
    print(f"Iniciando modificação para: {NEW_APP_NAME}")
    print("-" * 40)
    
    for arquivo in WORKFLOW_FILES:
        processar_arquivo(arquivo)
        
    print("-" * 40)
    print("Processo concluído! Verifique os arquivos.")   