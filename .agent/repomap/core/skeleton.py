import ast
import re
from typing import Optional, List, Dict, Any


class Skeletonizer:
    """Indentation-Preserving AST Skeletonizer with Dynamic Docstring Pruning.

    Pruning tiers:
    - Low budget (budget <= 2048): Elide all docstrings completely.
    - Medium budget (2049 <= budget <= 4096): Retain first line of docstrings.
    - High budget (budget >= 4097): Retain full docstrings.
    """

    def __init__(self, budget_tokens: int = 2048):
        self.budget_tokens = budget_tokens

    def skeletonize(self, code: str, lang: str = "python") -> str:
        if lang == "python":
            return self._skeletonize_python(code)
        else:
            return self._skeletonize_lexical(code)

    def _format_docstring(self, doc: str) -> Optional[str]:
        if not doc:
            return None
        if self.budget_tokens <= 2048:
            return None
        elif self.budget_tokens <= 4096:
            first_line = doc.strip().splitlines()[0]
            return f'"""{first_line}"""'
        else:
            return f'"""{doc.strip()}"""'

    def _skeletonize_python(self, code: str) -> str:
        try:
            tree = ast.parse(code)
        except Exception:
            return self._skeletonize_lexical(code)

        lines: List[str] = []

        def build_skeleton(node: ast.AST, indent_level: int = 0) -> None:
            indent = "    " * indent_level

            if isinstance(node, ast.Module):
                # Check for module-level docstring
                doc = ast.get_docstring(node)
                fmt_doc = self._format_docstring(doc)
                if fmt_doc:
                    lines.append(f"{fmt_doc}\n")
                for item in node.body:
                    build_skeleton(item, indent_level)

            elif isinstance(node, ast.ClassDef):
                # Reconstruct class signature
                bases = [ast.unparse(b) for b in node.bases]
                bases_str = f"({', '.join(bases)})" if bases else ""
                lines.append(f"{indent}class {node.name}{bases_str}:")

                doc = ast.get_docstring(node)
                fmt_doc = self._format_docstring(doc)
                if fmt_doc:
                    lines.append(f"{indent}    {fmt_doc}")

                has_children = False
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        build_skeleton(item, indent_level + 1)
                        has_children = True

                if not has_children and not fmt_doc:
                    lines.append(f"{indent}    ...")

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
                args = ast.unparse(node.args)
                returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
                lines.append(f"{indent}{prefix} {node.name}({args}){returns}:")

                doc = ast.get_docstring(node)
                fmt_doc = self._format_docstring(doc)
                if fmt_doc:
                    lines.append(f"{indent}    {fmt_doc}")
                lines.append(f"{indent}    ...")

        build_skeleton(tree, 0)
        return "\n".join(lines)

    def _skeletonize_lexical(self, code: str) -> str:
        out_lines: List[str] = []
        for line in code.splitlines():
            sline = line.strip()
            indent = line[: len(line) - len(line.lstrip())]

            if re.match(r'^(class|interface|struct|trait)\s+', sline):
                out_lines.append(f"{indent}{sline}")
            elif re.match(r'^(async\s+)?(def|function|fn|func)\s+', sline):
                if sline.endswith(":"):
                    out_lines.append(f"{indent}{sline}")
                    out_lines.append(f"{indent}    ...")
                elif sline.endswith("{"):
                    out_lines.append(f"{indent}{sline[:-1].strip()} {{ ... }}")
                else:
                    out_lines.append(f"{indent}{sline}")

        return "\n".join(out_lines)
