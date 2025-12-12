import os
import re

# Configurações
WORKFLOW_FILES = [
    '.github/workflows/flutter-nightly.yml',
    '.github/workflows/flutter-build.yml'
]
NEW_APP_NAME = "BMDesk"
OLD_APP_NAME = "RustDesk"

# Critérios de Filtragem
TARGET_PLATFORMS = ['windows', 'win', 'android']
# Removemos 'ubuntu' para evitar falsos positivos, pois Android roda em ubuntu-latest
IGNORE_PLATFORMS = ['linux', 'mac', 'macos', 'osx', 'ios', 'web', 'flatpak', 'appimage', 'dmg'] 

def get_job_list(lines):
    """
    Escaneia o arquivo para mapear todos os jobs e decidir o status (keep/drop).
    Retorna um dicionário: {'nome-do-job': 'keep' ou 'drop'}
    """
    jobs = {} 
    job_indent = -1
    in_jobs = False
    
    # Regex para capturar o nome do job (ex: "  build-linux:")
    job_regex = re.compile(r'^(\s+)([\w-]+):')
    
    for line in lines:
        stripped = line.strip()
        # Ignora comentários
        if stripped.startswith('#'):
            continue

        if stripped == 'jobs:':
            in_jobs = True
            continue
        
        if not in_jobs:
            continue
            
        match = job_regex.match(line)
        if match:
            indent = len(match.group(1))
            name = match.group(2)
            
            # Detecta a indentação correta dos jobs (primeiro nível após 'jobs:')
            if job_indent == -1:
                job_indent = indent
            
            # Se for um job (mesma indentação)
            if indent == job_indent:
                lower_name = name.lower()
                
                # Por padrão, mantemos (para jobs genéricos como 'release', 'setup')
                status = 'keep'
                
                # 1. É uma plataforma alvo? (Windows/Android) -> MANTER
                is_target = any(p in lower_name for p in TARGET_PLATFORMS)
                
                # 2. É uma plataforma ignorada? -> REMOVER (Exceto se for alvo também)
                is_ignore = any(p in lower_name for p in IGNORE_PLATFORMS)
                
                if is_ignore and not is_target:
                    status = 'drop'
                
                jobs[name] = status
                
    return jobs

def clean_needs_line(line, dropped_jobs):
    """
    Remove referências a jobs deletados de uma linha 'needs:'.
    Ex: needs: [build-win, build-linux] -> needs: [build-win]
    """
    if 'needs:' not in line:
        return line
        
    # Separa a chave 'needs:' do conteúdo
    parts = line.split('needs:', 1)
    if len(parts) < 2:
        return line
        
    prefix, content = parts
    new_content = content
    
    # Remove cada job dropado da lista
    for job in dropped_jobs:
        # Regex busca o nome do job cercado por delimitadores comuns em YAML/JSON (espaço, vírgula, colchetes, aspas)
        pattern = r'(?<=[\s\["\'\,])' + re.escape(job) + r'(?=[\s\]"\'\,]|$)'
        new_content = re.sub(pattern, '', new_content)
        
    # Limpeza cosmética da lista (remove vírgulas duplas ou soltas)
    new_content = re.sub(r',\s*,', ',', new_content) # ,, -> ,
    new_content = re.sub(r'\[\s*,', '[', new_content) # [, -> [
    new_content = re.sub(r',\s*\]', ']', new_content) # ,] -> ]
    
    # (Opcional) Se ficou vazio "[]" ou apenas espaços, o job pode falhar se o GitHub exigir needs.
    # Mas geralmente jobs genéricos dependem de pelo menos um build (Windows/Android), então deve sobrar algo.
    
    return prefix + 'needs:' + new_content

def apply_renaming(line):
    """Renomeia artefatos e referências textuais."""
    # Evita quebrar actions ou referências de repositório
    if "uses:" not in line and "repository:" not in line and "secrets." not in line:
        if OLD_APP_NAME in line:
            return line.replace(OLD_APP_NAME, NEW_APP_NAME)
    return line

def processar_arquivo(filepath):
    if not os.path.exists(filepath):
        print(f"Arquivo não encontrado: {filepath}")
        return

    print(f"\nAnalisando estrutura de: {filepath}...")

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    # Passo 1: Mapear o que fica e o que sai
    jobs_map = get_job_list(lines)
    dropped_jobs = [j for j, status in jobs_map.items() if status == 'drop']
    kept_jobs = [j for j, status in jobs_map.items() if status == 'keep']
    
    print(f"  -> Mantendo ({len(kept_jobs)}): {kept_jobs}")
    print(f"  -> Removendo ({len(dropped_jobs)}): {dropped_jobs}")
    
    new_lines = []
    current_job_status = 'keep' # Começa como keep (cabeçalho)
    in_jobs = False
    job_indent = -1
    job_regex = re.compile(r'^(\s+)([\w-]+):')

    # Passo 2: Reescrever o arquivo
    for line in lines:
        stripped = line.strip()
        
        # Detecta início da seção jobs
        if stripped == 'jobs:':
            in_jobs = True
            new_lines.append(line)
            continue
            
        if in_jobs:
            match = job_regex.match(line)
            if match:
                indent = len(match.group(1))
                name = match.group(2)
                
                if job_indent == -1:
                    job_indent = indent
                
                # Se for a definição de um novo job
                if indent == job_indent:
                    current_job_status = jobs_map.get(name, 'keep') # Pega status decidido no passo 1
        
        # Se estamos dentro de um job marcado para remover, pula a linha
        if in_jobs and current_job_status == 'drop':
            continue
            
        # Se estamos em um job mantido, verifica se precisa limpar dependências (needs)
        if in_jobs and 'needs:' in line:
            line = clean_needs_line(line, dropped_jobs)
            
        # Aplica a renomeação (RustDesk -> BMDesk)
        line = apply_renaming(line)
        new_lines.append(line)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print("  -> Arquivo atualizado com sucesso.")

if __name__ == "__main__":
    print("-" * 60)
    print(f"Iniciando modificação inteligente de workflows para: {NEW_APP_NAME}")
    print("Modo: Análise de dependências e preservação de infraestrutura.")
    print("-" * 60)
    
    for arquivo in WORKFLOW_FILES:
        processar_arquivo(arquivo)
        
    print("-" * 60)
    print("Concluído! Jobs irrelevantes removidos e dependências corrigidas.")