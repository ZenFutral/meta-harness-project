import sys
import unittest
import tempfile
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parents[2]
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from repomap.facets.blast_radius import BlastRadiusTracer, trace_blast_radius
from repomap.facets.hierarchy import HierarchyFacet, get_symbol_hierarchy
from repomap.facets.endpoints import RouteScannerFacet, scan_routes
from repomap.facets.schemas import SchemaRegistry, get_schema_registry
from repomap.core.graph import TwoTierGraph
from repomap.core.type_hierarchy import TypeHierarchyLattice


class Phase5Tests(unittest.TestCase):
    def test_step_5_1_blast_radius_tracer_depth_and_fanout(self):
        graph = TwoTierGraph()
        graph.micro_graph = {
            "core.py::global::save::function": {
                "db.py::global::execute_query::function": 1.0,
            },
            "api.py::global::handle_request::function": {
                "core.py::global::save::function": 1.0,
            },
        }

        tracer = BlastRadiusTracer(graph)
        result = tracer.trace_blast_radius(
            symbol_name="core.py::global::save::function",
            direction="both",
            max_depth=3,
            max_fanout=10,
        )

        self.assertEqual(result["target_symbol"], "core.py::global::save::function")
        self.assertGreater(len(result["upstream"]), 0)
        self.assertGreater(len(result["downstream"]), 0)

    def test_step_5_2_type_hierarchy_facet(self):
        lattice = TypeHierarchyLattice()
        lattice.add_type("ChildClass", bases=["ParentClass"])
        lattice.add_type("ParentClass", bases=["GrandParentClass"])

        facet = HierarchyFacet(lattice)
        res = facet.get_symbol_hierarchy("ChildClass")

        self.assertIn("ParentClass", res["ancestors"])
        self.assertIn("GrandParentClass", res["ancestors"])
        self.assertTrue(res["is_leaf"])

    def test_step_5_3_route_scanner_facet(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        repo_root = Path(self.tmp_dir.name)

        py_app = repo_root / "main.py"
        py_app.write_text(
            '@app.get("/users")\n'
            'async def get_users():\n'
            '    return []\n'
        )

        ts_app = repo_root / "server.ts"
        ts_app.write_text(
            'router.post("/items", createItem);\n'
        )

        routes = scan_routes(repo_root)
        self.assertEqual(len(routes), 2)

        methods = {r["method"] for r in routes}
        paths = {r["path"] for r in routes}

        self.assertIn("GET", methods)
        self.assertIn("POST", methods)
        self.assertIn("/users", paths)
        self.assertIn("/items", paths)

        self.tmp_dir.cleanup()

    def test_step_5_4_schema_registry_protobuf_parsing(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        repo_root = Path(self.tmp_dir.name)

        proto_file = repo_root / "user.proto"
        proto_file.write_text(
            'syntax = "proto3";\n'
            'message User {\n'
            '  string name = 1;\n'
            '  int32 id = 2;\n'
            '}\n'
        )

        registry_data = get_schema_registry(repo_root)
        self.assertGreater(len(registry_data), 0)
        self.assertEqual(registry_data[0]["model"], "User")
        self.assertEqual(registry_data[0]["type"], "protobuf")

        self.tmp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
