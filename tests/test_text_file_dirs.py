"""Exercise the actual standalone config reader without starting ComfyUI."""
import ast
import json
import os
from pathlib import Path
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "py" / "text_files.py"


class TextFileDirectories(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "user").mkdir()
        # The reader has no framework dependencies. Compile its real function
        # body alone so these config tests cannot bind a server or import nodes.
        tree = ast.parse(SOURCE.read_text())
        reader = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "get_allowed_dirs")
        namespace = {"os": os, "json": json, "__file__": str(self.root / "py" / "text_files.py")}
        exec(compile(ast.Module(body=[reader], type_ignores=[]), str(SOURCE), "exec"), namespace)
        self.read = namespace["get_allowed_dirs"]
        self.defaults = {"input": "$input/*.txt", "output": "$output/*.txt"}
        (self.root / "user" / "text_file_dirs.json").write_text(json.dumps(self.defaults))

    def test_tracked_default_unchanged_without_local_file(self):
        self.assertEqual(self.read(), self.defaults)

    def test_linux_recursive_temp_override_and_live_refresh(self):
        path = self.root / "user" / "text_file_dirs.local.json"
        local = {"input": "$input/**/*.txt", "output": "$output/**/*.txt", "temp": "$temp/**/*.txt"}
        path.write_text(json.dumps(local))
        self.assertEqual(self.read(), local)
        path.write_text(json.dumps({"temp": "$temp/**/*.txt"}))
        self.assertEqual(self.read(), {"temp": "$temp/**/*.txt"})
        self.assertEqual(json.loads((self.root / "user" / "text_file_dirs.json").read_text()), self.defaults)

    def test_invalid_local_configuration_is_not_hidden_by_fallback(self):
        path = self.root / "user" / "text_file_dirs.local.json"
        for value in ([], {"input": None}, {"temp": ["$temp/**/*.txt"]}):
            path.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                self.read()
        path.write_text("{broken")
        with self.assertRaises(json.JSONDecodeError):
            self.read()


if __name__ == "__main__":
    unittest.main()
