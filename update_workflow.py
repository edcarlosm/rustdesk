import os
import re

# Configurações
WORKFLOW_FILES = [
    '.github/workflows/flutter-nightly.yml',
    '.github/workflows/flutter-build.yml'
]
NEW_APP_NAME = "BMDesk"
OLD_APP_NAME = "RustDesk"

# 1. Lista de Bloqueio (O que queremos remover)
# Removemos 'ubuntu' daqui pois muitos jobs de Android rodam em 'ubuntu-latest' e podem ter esse nome.
BLACKLIST_KEYWORDS = ['linux', 'mac', 'osx', 'ios', 'web', 'flatpak', 'appimage', 'dmg', 'freebsd', 'suse']

# 2. Lista de Permissão (O que deve ser mantido, mesmo que pareça suspeito na blacklist)
# Jobs de infraestrutura, setup ou cancelamento de workflow são cruciais.
WHITELIST_KEYWORDS = ['setup', 'prepare', 'cancel', 'env', 'config', 'release', 'prerelease', 'publish', 'draft']

def apply_renaming(line):
    """
    Aplica a renomeação de RustDesk para BMDesk em uma linha,
    protegendo chaves críticas de infraestrutura do GitHub Actions.
    """
    # Proteções: não alterar ações (uses), chaves de segredo, ou repositórios
    if "uses:" not in line and "repository:" not in line and "secrets." not in line:
        if OLD_APP_NAME in line:
            return line.replace(OLD_APP_NAME, NEW_APP_NAME)
    return line

def processar_arquivo(filepath):
    if not os.path.exists(filepath):
        print(f"Aviso: O arquivo '{filepath}' não foi encontrado. Pulando...")
        return

    print(f"\nProcessando: {filepath}...")

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

        # Se não estamos na seção jobs, apenas copia e renomeia
        if not in_jobs_section:
            new_lines.append(apply_renaming(line))
            continue

        # Estamos dentro da seção jobs, verificar se é a definição de um novo job
        match = job_regex.match(line)
        
        if match:
            indent = len(match.group(1))
            name = match.group(2).lower()

            # Define a indentação padrão dos jobs na primeira vez
            if jobs_indentation == -1:
                jobs_indentation = indent

            # Se a indentação for igual à dos jobs, é um novo job começando
            if indent == jobs_indentation:
                # --- LÓGICA DE FILTRAGEM V3 ---
                
                # 1. Verificar Whitelist (Prioridade Máxima)
                # Mantém jobs de infraestrutura ou que contenham Android/Windows explicitamente
                is_whitelisted = any(term in name for term in WHITELIST_KEYWORDS)
                is_target_platform = 'windows' in name or 'win' in name or 'android' in name
                
                if is_whitelisted or is_target_platform:
                    should_remove = False
                else:
                    # 2. Verificar Blacklist (Apenas se não for um job essencial)
                    should_remove = any(bad_term in name for bad_term in BLACKLIST_KEYWORDS)

                if should_remove:
                    skip_current_job = True
                    print(f"  [REMOVER] Job filtrado: {match.group(2)}")
                else:
                    skip_current_job = False
                    print(f"  [MANTER] Job preservado: {match.group(2)}")

        # Se o job atual foi marcado para pular, ignora a linha
        if skip_current_job:
            continue

        # Adiciona a linha processada
        new_lines.append(apply_renaming(line))

    # Salvar o arquivo modificado
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"  -> Arquivo {filepath} atualizado.")

if __name__ == "__main__":
    print("-" * 50)
    print(f"Iniciando atualização V3 (Preservação de Setup) para: {NEW_APP_NAME}")
    print("-" * 50)
    
    for arquivo in WORKFLOW_FILES:
        processar_arquivo(arquivo)
        
    print("-" * 50)
    print("Concluído. Tente rodar o build novamente.")