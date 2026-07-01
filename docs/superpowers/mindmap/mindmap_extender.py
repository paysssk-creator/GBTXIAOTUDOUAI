"""
GBT MindMap Extender - ??????????
???????????, ?????
"""
import json, os, sys, time, re
from datetime import datetime

class MindNode:
    """???? - ?????????"""
    def __init__(self, concept, depth=0):
        self.concept = concept
        self.depth = depth
        self.children = []
        self.insights = []
        self.connections = []  # ?????
        self.score = 0
        self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {
            "concept": self.concept,
            "depth": self.depth,
            "insights": self.insights,
            "connections": self.connections,
            "score": self.score,
            "children": [c.to_dict() for c in self.children]
        }

class MindMap:
    """????????"""
    def __init__(self, root_concept):
        self.root = MindNode(root_concept, 0)
        self.node_count = 1
        self.max_depth = 4

    def explore_dimension(self, node, dim_id, dim_info, context_data):
        """???????, ???????????"""
        dim_node = MindNode(f"{dim_info['name']}: {node.concept[:40]}", node.depth + 1)

        # ?????????
        questions = dim_info["questions"]
        for q in questions:
            insight = self._reason(node.concept, q, dim_id, dim_info, context_data)
            dim_node.insights.append(insight)

        # ??
        dim_node.score = self._score_dimension(node.concept, dim_id, dim_info, context_data)

        # ???? (??????)
        if node.depth < self.max_depth - 1:
            sub_questions = self._generate_sub_questions(node.concept, dim_id, dim_info)
            for sq in sub_questions[:3]:
                sub_node = MindNode(sq, node.depth + 2)
                sub_node.insights.append(self._reason(node.concept, sq, dim_id, dim_info, context_data))
                dim_node.children.append(sub_node)
                self.node_count += 1

        node.children.append(dim_node)
        self.node_count += 1
        return dim_node

    def expand(self, context_data=None):
        """???????? - ???????????"""
        from dimension_space import DIMENSIONS

        print(f"\n  MindMap: {self.root.concept}")
        print(f"  Expanding across {len(DIMENSIONS)} dimensions...")

        for dim_id, dim_info in DIMENSIONS.items():
            child = self.explore_dimension(self.root, dim_id, dim_info, context_data)
            print(f"    d-{dim_id:15s}: score={child.score} | {len(child.insights)} insights | {len(child.children)} sub-branches")

        # ????? - ??????????
        self._cross_connect()

        return self

    def _reason(self, concept, question, dim_id, dim_info, context):
        """????? - ????????"""
        text = f"{concept} {question} {json.dumps(context or {}, ensure_ascii=False)}".lower()
        keywords = dim_info.get("keywords", [])
        hits = [kw for kw in keywords if kw in text]

        if hits:
            return f"{dim_info['name']}??: ?????? {', '.join(hits[:5])} ? {question[:60]}..."
        else:
            return f"{dim_info['name']}??: ??????? {question[:60]}..."

    def _score_dimension(self, concept, dim_id, dim_info, context):
        """????"""
        text = f"{concept} {json.dumps(context or {}, ensure_ascii=False)}".lower()
        keywords = dim_info.get("keywords", [])
        hits = sum(1 for kw in keywords if kw in text)
        base = min(hits * 12, 85)
        # ?????
        return min(base + dim_info.get("weight", 5), 100)

    def _generate_sub_questions(self, concept, dim_id, dim_info):
        """????????? - ????????"""
        base_questions = dim_info["questions"]
        sub = []
        for q in base_questions:
            sub.append(f"??{q} ????????")
            sub.append(f"{q} ?????????")
        return sub[:6]

    def _cross_connect(self):
        """????? - ???????????"""
        if len(self.root.children) >= 2:
            for i, dim_a in enumerate(self.root.children):
                for j, dim_b in enumerate(self.root.children):
                    if i >= j: continue
                    # ??????????????
                    from dimension_space import DIMENSIONS
                    da = DIMENSIONS.get(dim_a.concept.split(":")[0].strip(), {})
                    db = DIMENSIONS.get(dim_b.concept.split(":")[0].strip(), {})
                    common = set(da.get("keywords", [])) & set(db.get("keywords", []))
                    if common:
                        dim_a.connections.append({
                            "to": dim_b.concept,
                            "via": list(common)[:3]
                        })
                        dim_b.connections.append({
                            "to": dim_a.concept,
                            "via": list(common)[:3]
                        })

    def export(self, fmt="tree"):
        """??????"""
        if fmt == "json":
            return json.dumps(self.root.to_dict(), indent=2, ensure_ascii=False)
        return self._export_tree(self.root, "")

    def _export_tree(self, node, prefix):
        """??????"""
        lines = [f"{prefix}{node.concept}"]
        if node.score:
            lines[-1] += f" ({node.score}/100)"
        for ins in node.insights[:2]:
            lines.append(f"{prefix}  -> {ins[:80]}")
        for conn in node.connections:
            lines.append(f"{prefix}  ~~ {conn['to']} via {conn['via']}")
        for child in node.children:
            lines.append(self._export_tree(child, prefix + "  "))
        return "\n".join(lines)

    def stats(self):
        return {
            "root": self.root.concept,
            "nodes": self.node_count,
            "max_depth": self.max_depth,
            "dimensions": len(self.root.children),
            "connections": sum(len(c.connections) for c in self.root.children)
        }


# ========== ? DimensionEngine ?? ==========
class ExtendedDimensionEngine:
    """???????? - ??????"""
    def __init__(self):
        from dimension_engine import DimensionEngine
        self.engine = DimensionEngine()

    def mindmap_analyze(self, target, data):
        """??????????"""
        mindmap = MindMap(target)
        mindmap.expand(context_data=data)

        # ????????
        analysis = self.engine.analyze(target, data)
        evolution_plan = self.engine.evolve_from_analysis(target, analysis)

        return {
            "mindmap": mindmap.export("json"),
            "mindmap_text": mindmap.export("tree"),
            "analysis": analysis,
            "evolution_plan": evolution_plan,
            "stats": mindmap.stats()
        }
