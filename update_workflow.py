import os
import re

# Configurações
WORKFLOW_FILES = [
    '.github/workflows/flutter-nightly.yml',
    '.github/workflows/flutter-build.yml'
]
NEW_APP_NAME = "BMDesk"
OLD_APP_NAME = "RustDesk"

# Termos que identificam jobs que DEVEMOS remover (apenas o indesejado)
BLACKLIST_KEYWORDS = ['linux', 'ubuntu', 'mac', 'osx', 'ios', 'web', 'flatpak', 'appimage', 'dmg']

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
                # Lógica V2: Remover APENAS se estiver na Blacklist.
                # Se for 'android', 'windows' ou genérico ('build'), MANTÉM.
                should_remove = any(bad_term in name for bad_term in BLACKLIST_KEYWORDS)
                
                # Exceção de segurança: Se o nome tiver 'windows' ou 'android',
                # ignoramos a blacklist (ex: 'web-android-bridge' -> mantém pois é android)
                if 'windows' in name or 'win' in name or 'android' in name:
                    should_remove = False

                if should_remove:
                    skip_current_job = True
                    print(f"  [REMOVER] Job encontrado e filtrado: {match.group(2)}")
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
    print(f"Iniciando atualização V2 para: {NEW_APP_NAME}")
    print("Estratégia: Remover apenas Linux/Mac/Web, manter Windows/Android e genéricos.")
    print("-" * 50)
    
    for arquivo in WORKFLOW_FILES:
        processar_arquivo(arquivo)
        
    print("-" * 50)
    print("ATENÇÃO: A compilação pode falhar no upload se os arquivos gerados")
    print("pelo build script (Cargo.toml, pubspec.yaml) ainda tiverem o nome antigo.")
    print("Certifique-se de prosseguir para a alteração dos arquivos de configuração.")