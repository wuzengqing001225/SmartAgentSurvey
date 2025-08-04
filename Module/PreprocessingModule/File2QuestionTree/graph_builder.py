import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
import json

import matplotlib
matplotlib.use('Agg')

class SurveyFlowVisualizer:
    def __init__(self, survey_data: Dict[str, Any]):
        self.survey_data = survey_data
        self.graph = nx.DiGraph()
        self.simplified_graph = nx.DiGraph()
        self._build_graph()

    def _build_graph(self):
        for question_id, data in self.survey_data.items():
            is_table = 'table_structure' in data
            self.graph.add_node(question_id,
                              type=data.get('type', ''),
                              is_table=is_table)

            jump_logic = data.get('jump_logic', {})
            if isinstance(jump_logic, dict):
                if 'next' in jump_logic and jump_logic['next']:
                    self.graph.add_edge(question_id, str(jump_logic['next']))
                else:
                    for condition, next_id in jump_logic.items():
                        if next_id and condition != 'next':
                            self.graph.add_edge(question_id, str(next_id), condition=condition)

    def _find_sequence_groups(self) -> List[List[str]]:
        groups = []
        current_group = []

        # Separate numeric and non-numeric nodes
        numeric_nodes = []
        non_numeric_nodes = []

        for node in self.graph.nodes():
            try:
                int(node)
                numeric_nodes.append(node)
            except ValueError:
                non_numeric_nodes.append(node)

        # Sort numeric nodes by their integer value, then add non-numeric nodes
        sorted_numeric = sorted(numeric_nodes, key=lambda x: int(x))
        sorted_nodes = sorted_numeric + sorted(non_numeric_nodes)

        for node in sorted_nodes:
            node_data = self.graph.nodes[node]
            out_edges = list(self.graph.out_edges(node))
            in_edges = list(self.graph.in_edges(node))

            if (node_data.get('is_table', False) or
                len(out_edges) > 1 or len(in_edges) > 1):
                if current_group:
                    groups.append(current_group)
                    current_group = []
                groups.append([node])
            else:
                if not current_group:
                    current_group.append(node)
                else:
                    last_node = current_group[-1]
                    if self.graph.has_edge(last_node, node):
                        current_group.append(node)
                    else:
                        groups.append(current_group)
                        current_group = [node]

        if current_group:
            groups.append(current_group)

        return groups

    def _build_simplified_graph(self):
        self.simplified_graph = nx.DiGraph()
        sequences = self._find_sequence_groups()

        node_mapping = {}

        for sequence in sequences:
            if len(sequence) == 1:
                node_id = sequence[0]
                self.simplified_graph.add_node(node_id,
                                            is_table=self.graph.nodes[node_id].get('is_table', False))
                node_mapping[node_id] = node_id
            else:
                node_id = f"{sequence[0]}-{sequence[-1]}"
                self.simplified_graph.add_node(node_id, is_table=False)
                for orig_node in sequence:
                    node_mapping[orig_node] = node_id

        edges_to_add = set()
        for u, v, data in self.graph.edges(data=True):
            new_u = node_mapping[u]
            new_v = node_mapping[v]
            if new_u != new_v:
                if 'condition' in data:
                    edges_to_add.add((new_u, new_v, data['condition']))
                else:
                    edges_to_add.add((new_u, new_v, None))

        for u, v, condition in edges_to_add:
            if condition:
                self.simplified_graph.add_edge(u, v, condition=condition)
            else:
                self.simplified_graph.add_edge(u, v)

    def is_dag(self) -> bool:
        return nx.is_directed_acyclic_graph(self.graph)

    def get_all_paths(self) -> List[List[str]]:
        start_nodes = [n for n in self.graph.nodes() if self.graph.in_degree(n) == 0]
        end_nodes = [n for n in self.graph.nodes() if self.graph.out_degree(n) == 0]

        all_paths = []
        for start in start_nodes:
            for end in end_nodes:
                paths = list(nx.all_simple_paths(self.graph, start, end))
                all_paths.extend(paths)
        return all_paths

    def visualize(self, output_path: str = None):
        self._build_simplified_graph()
        plt.figure(figsize=(12, 8))

        try:
            pos = nx.shell_layout(self.simplified_graph)
        except:
            try:
                pos = nx.spring_layout(self.simplified_graph, k=2, iterations=50)
            except:
                pos = nx.kamada_kawai_layout(self.simplified_graph)

        node_sizes = 2000
        regular_color = '#ADD8E6'
        table_color = '#90EE90'
        branch_color = '#FFB6C1'

        table_nodes = [n for n, d in self.simplified_graph.nodes(data=True)
                      if d.get('is_table', False)]
        branch_nodes = [n for n in self.simplified_graph.nodes()
                       if any(e[0] == n and self.simplified_graph.edges[e].get('condition')
                             for e in self.simplified_graph.edges)]
        regular_nodes = [n for n in self.simplified_graph.nodes()
                        if n not in table_nodes and n not in branch_nodes]

        if regular_nodes:
            nx.draw_networkx_nodes(self.simplified_graph, pos,
                                 nodelist=regular_nodes,
                                 node_color=regular_color,
                                 node_size=node_sizes,
                                 alpha=0.7)

        if table_nodes:
            nx.draw_networkx_nodes(self.simplified_graph, pos,
                                 nodelist=table_nodes,
                                 node_color=table_color,
                                 node_size=node_sizes,
                                 alpha=0.7)

        if branch_nodes:
            nx.draw_networkx_nodes(self.simplified_graph, pos,
                                 nodelist=branch_nodes,
                                 node_color=branch_color,
                                 node_size=node_sizes,
                                 alpha=0.7)

        normal_edges = [(u, v) for u, v, d in self.simplified_graph.edges(data=True)
                       if 'condition' not in d]
        conditional_edges = [(u, v) for u, v, d in self.simplified_graph.edges(data=True)
                           if 'condition' in d]

        if normal_edges:
            nx.draw_networkx_edges(self.simplified_graph, pos,
                                 edgelist=normal_edges,
                                 edge_color='gray',
                                 arrows=True,
                                 arrowsize=20,
                                 width=2)

        if conditional_edges:
            nx.draw_networkx_edges(self.simplified_graph, pos,
                                 edgelist=conditional_edges,
                                 edge_color='blue',
                                 style='dashed',
                                 arrows=True,
                                 arrowsize=20,
                                 width=2)

        labels = {}
        for node in self.simplified_graph.nodes():
            if '-' in str(node):
                start, end = node.split('-')
                labels[node] = f"Q{start}-{end}"
            else:
                # Handle special nodes like 'end'
                try:
                    int(node)
                    labels[node] = f"Q{node}"
                except ValueError:
                    # For non-numeric nodes like 'end', use the node name as is
                    labels[node] = str(node).upper()

        nx.draw_networkx_labels(self.simplified_graph, pos,
                              labels=labels,
                              font_size=16,
                              font_weight='bold')

        edge_labels = {(u, v): d.get('condition', '')
                      for u, v, d in self.simplified_graph.edges(data=True)
                      if 'condition' in d}

        if edge_labels:
            nx.draw_networkx_edge_labels(self.simplified_graph, pos,
                                       edge_labels=edge_labels,
                                       font_size=16)

        plt.title("Survey Question Flow", pad=20, size=16)
        plt.axis('off')

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
        else:
            # plt.show()
            plt.close()

    def split_question_segments(self, max_questions_per_segment = 20):
        segments = []

        # Find the actual start nodes (nodes with no incoming edges)
        start_nodes = [n for n in self.graph.nodes() if self.graph.in_degree(n) == 0]

        # If no start nodes found, use the first numeric node
        if not start_nodes:
            numeric_nodes = []
            for node in self.graph.nodes():
                try:
                    int(node)
                    numeric_nodes.append(int(node))
                except ValueError:
                    continue
            if numeric_nodes:
                start_nodes = [str(min(numeric_nodes))]
            else:
                # If no numeric nodes, use the first node
                start_nodes = [list(self.graph.nodes())[0]] if self.graph.nodes() else []

        if not start_nodes:
            return segments

        # Convert start node to int if possible, otherwise use as string
        start_node = start_nodes[0]
        try:
            start_node_int = int(start_node)
            paths_to_follow = [[start_node_int, "", [start_node_int]]]
        except ValueError:
            paths_to_follow = [[start_node, "", [start_node]]]

        processed_paths = set()

        while paths_to_follow:
            start, condition, current_path = paths_to_follow.pop(0)
            current_segment = [start, condition, current_path.copy()]
            processed_paths.add(tuple(current_path))

            while current_segment[2]:
                current_question = current_segment[2][-1]
                jump_logic = self.survey_data.get(str(current_question), {}).get('jump_logic', {})

                if isinstance(jump_logic, dict) and len(jump_logic) > 1:
                    self._add_segment(current_segment, max_questions_per_segment, segments)
                    for cond, next_id in jump_logic.items():
                        if cond != 'next' and next_id:
                            new_path = [next_id]
                            if tuple(new_path) not in processed_paths:
                                paths_to_follow.append([current_question, cond, new_path])
                                processed_paths.add(tuple(new_path))
                    break
                elif 'next' in jump_logic:
                    next_question = jump_logic['next']
                    if next_question is None or str(next_question).lower() == 'end':
                        self._add_segment(current_segment, max_questions_per_segment, segments)
                        break
                    current_segment[2].append(next_question)
                else:
                    self._add_segment(current_segment, max_questions_per_segment, segments)
                    break

        return segments

    def _add_segment(self, current_segment, max_questions_per_segment, segments):
        question_list = current_segment[2]

        # Handle previous_question calculation safely
        try:
            previous_question = int(current_segment[0]) - 1
        except (ValueError, TypeError):
            previous_question = current_segment[0]

        if len(question_list) > max_questions_per_segment:
            for i in range(0, len(question_list), max_questions_per_segment):
                segment_end = i + max_questions_per_segment
                if segment_end > len(question_list):
                    segment_end = len(question_list)

                if i == 0:
                    segments.append([
                        current_segment[0],
                        current_segment[1],
                        question_list[i:segment_end]
                    ])
                else:
                    segments.append([
                        question_list[i-1],
                        '',
                        question_list[i:segment_end]
                    ])
        else:
            segments.append(current_segment.copy())

