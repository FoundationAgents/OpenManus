import pytest

from app.utils.files_utils import clean_path


@pytest.mark.parametrize(
    ("path", "workspace", "esperado"),
    [
        ("/workspace/src/main.py", "/workspace", "src/main.py"),
        ("src/main.py", "/workspace", "src/main.py"),
        ("/workspace", "/workspace", ""),
    ],
)
def test_clean_path_keeps_legitimate_path(path, workspace, esperado):
    """Controle positivo: caminho legitimo continua sendo devolvido igual."""
    assert clean_path(path, workspace) == esperado


def test_clean_path_does_not_escape_workspace():
    """'..' nao pode sobreviver no resultado, que e colado em /workspace."""
    resultado = clean_path("/workspace/../etc/passwd", "/workspace")
    assert ".." not in resultado.split("/")


def test_clean_path_does_not_strip_prefix_by_substring():
    """'/workspace-other' nao e '/workspace': o corte tem que ser por componente."""
    resultado = clean_path("/workspace-other/secret.txt", "/workspace")
    assert resultado != "-other/secret.txt"
