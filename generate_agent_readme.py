import os
import re

# Diretórios e arquivos a serem ignorados
IGNORE_PATTERNS = [
    # Controle de versão
    r"\.git/",
    # Ambientes virtuais
    r"venv/",
    r"\.venv/",
    r"__pycache__/",
    # Configurações de IDE/Editor
    r"\.vscode/",
    r"\.idea/",
    # Logs e workspaces
    r"logs/",
    r"workspace/",
    r"\.config/",
    # Arquivos de build/distribuição
    r"build/",
    r"dist/",
    r"node_modules/",
    r"\.pytest_cache/",
    r"\.mypy_cache/",
    # Arquivos específicos do agente
    r"AGENTREADME\.MD",
    r"generate_agent_readme\.py",
    # Extensões de arquivos binários comuns ou não textuais
    r"\.pyc$",
    r"\.pyo$",
    r"\.so$",
    r"\.dll$",
    r"\.exe$",
    r"\.DS_Store$",
    r"\.ipynb_checkpoints/",
    # Imagens e outros assets
    r"\.png$",
    r"\.jpg$",
    r"\.jpeg$",
    r"\.gif$",
    r"\.svg$",
    r"\.ico$",
    r"\.pdf$",
    r"\.zip$",
    r"\.tar\.gz$",
    r"\.woff$",
    r"\.woff2$",
    r"\.ttf$",
    r"\.eot$",
    # Arquivos de exemplo de configuração que não são código ativo
    r"config\.example.*\.toml$",
    r"mcp\.example\.json$",
]

# Marcadores para a seção de conteúdo no AGENTREADME.MD
CONTENT_START_MARKER = "<!-- CONTENT_START -->"
CONTENT_END_MARKER = "<!-- CONTENT_END -->"
AGENTREADME_FILE = "AGENTREADME.MD"

def get_file_language_extension(filepath):
    """Retorna a extensão do arquivo para uso em blocos de código markdown."""
    _, ext = os.path.splitext(filepath)
    return ext[1:] if ext else ""

def should_ignore(path):
    """Verifica se o caminho (arquivo ou diretório) deve ser ignorado."""
    for pattern in IGNORE_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            return True
    return False

def generate_repo_content():
    """
    Percorre o repositório, lê arquivos relevantes e formata seu conteúdo.
    """
    repo_root = os.getcwd()
    all_files_content = []

    for root, dirs, files in os.walk(repo_root, topdown=True):
        # Filtra diretórios ignorados
        dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d) + '/')]

        for filename in files:
            filepath = os.path.join(root, filename)
            relative_filepath = os.path.relpath(filepath, repo_root)

            if should_ignore(relative_filepath):
                continue

            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                lang_ext = get_file_language_extension(filepath)
                formatted_content = f"### ARQUIVO: {relative_filepath} ###\n"
                formatted_content += f"```{lang_ext}\n"
                formatted_content += content
                formatted_content += "\n```\n\n"
                all_files_content.append(formatted_content)
                print(f"Processado: {relative_filepath}")
            except Exception as e:
                print(f"Erro ao ler o arquivo {filepath}: {e}")

    return "".join(all_files_content)

def update_agent_readme(repo_content_str):
    """
    Atualiza o AGENTREADME.MD com o novo conteúdo do repositório.
    """
    try:
        with open(AGENTREADME_FILE, 'r', encoding='utf-8') as f:
            agent_readme_content = f.read()
    except FileNotFoundError:
        print(f"Erro: {AGENTREADME_FILE} não encontrado. Crie o arquivo primeiro com os marcadores.")
        return

    start_index = agent_readme_content.find(CONTENT_START_MARKER)
    end_index = agent_readme_content.find(CONTENT_END_MARKER)

    if start_index == -1 or end_index == -1:
        print(f"Erro: Marcadores {CONTENT_START_MARKER} ou {CONTENT_END_MARKER} não encontrados em {AGENTREADME_FILE}.")
        print("Certifique-se de que o AGENTREADME.MD tem a seguinte estrutura:")
        print(f"{CONTENT_START_MARKER}\n...conteúdo antigo aqui...\n{CONTENT_END_MARKER}")
        return

    # Preserva o conteúdo antes do marcador de início e após o marcador de fim
    before_content = agent_readme_content[:start_index + len(CONTENT_START_MARKER)]
    after_content = agent_readme_content[end_index:]

    # Monta o novo conteúdo do AGENTREADME.MD
    new_agent_readme_content = (
        before_content +
        "\n## Conteúdo Completo do Repositório\n\n" +
        repo_content_str +
        "\n" +
        after_content
    )

    try:
        with open(AGENTREADME_FILE, 'w', encoding='utf-8') as f:
            f.write(new_agent_readme_content)
        print(f"{AGENTREADME_FILE} atualizado com sucesso.")
    except Exception as e:
        print(f"Erro ao escrever no {AGENTREADME_FILE}: {e}")

if __name__ == "__main__":
    print("Iniciando a geração do conteúdo do repositório para AGENTREADME.MD...")
    repository_content = generate_repo_content()
    if repository_content:
        update_agent_readme(repository_content)
    else:
        print("Nenhum conteúdo foi gerado. Verifique os padrões de ignore e a estrutura do projeto.")
    print("Processo concluído.")
