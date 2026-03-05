class Node:
    def __init__(self, name):
        if not name:
            raise ValueError("Node name is required")
        self.name = name
        self.group = None

    def add_sibling(self, sibling):
        if not isinstance(sibling, Node):
            raise TypeError("Sibling must be a Node")
        if self.group is None:
            self.group = [self]
        if sibling.group is None:
            sibling.group = self.group
        if sibling not in self.group:
            self.group.append(sibling)
        return self.group

    def addSibling(self, sibling):
        return self.add_sibling(sibling)


class Parameter(Node):
    def __init__(self, name, parameter_type="string", description=None):
        super().__init__(name)
        self.type = parameter_type
        self.description = description

    def to_dict(self):
        return {
            "type": "parameter",
            "name": self.name,
            "parameter_type": self.type,
            "description": self.description,
        }

    def to_frontend_parameter(self, group_path=None):
        frontend_type = _normalize_frontend_parameter_type(self.type)
        payload = {
            "name": self.name,
            "type": frontend_type,
            "comment": self.description or "",
            "units": "",
        }
        if group_path:
            payload["group"] = group_path
        return payload


class Group(Node):
    def __init__(self, name):
        super().__init__(name)
        self.children = []
        self.parameters = self.children

    def add_child(self, child):
        if not isinstance(child, Node):
            raise TypeError("Group children must be Node instances")
        self.children.append(child)
        return child

    def addChild(self, child):
        return self.add_child(child)

    def add_parameter(self, name, parameter_type="string", description=None):
        parameter = Parameter(name=name, parameter_type=parameter_type, description=description)
        self.children.append(parameter)
        return parameter

    def add_group(self, name):
        group = Group(name=name)
        self.children.append(group)
        return group

    def get_or_add_group(self, name):
        for child in self.children:
            if isinstance(child, Group) and child.name == name:
                return child
        return self.add_group(name)

    def to_dict(self):
        return {
            "type": "group",
            "name": self.name,
            "children": [child.to_dict() for child in self.children],
        }

    def to_frontend_parameters(self, parent_path=None):
        current_path = self.name if not parent_path else f"{parent_path}.{self.name}"
        flattened = []
        for child in self.children:
            if isinstance(child, Parameter):
                flattened.append(child.to_frontend_parameter(group_path=current_path))
            elif isinstance(child, Group):
                flattened.extend(child.to_frontend_parameters(parent_path=current_path))
        return flattened


class Template:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.nodes = []
        self.parameters = self.nodes

    def add_node(self, node):
        if not isinstance(node, Node):
            raise TypeError("Template nodes must be Node instances")
        self.nodes.append(node)
        return node

    def addChild(self, child):
        return self.add_node(child)

    def add_group(self, name):
        group = Group(name=name)
        self.nodes.append(group)
        return group

    def add_parameter(self, name, parameter_type="string", description=None):
        parameter = Parameter(name=name, parameter_type=parameter_type, description=description)
        self.nodes.append(parameter)
        return parameter

    def get_or_add_group(self, name):
        for node in self.nodes:
            if isinstance(node, Group) and node.name == name:
                return node
        return self.add_group(name)

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "nodes": [node.to_dict() for node in self.nodes],
        }

    def to_frontend_parameters(self):
        flattened = []
        for node in self.nodes:
            if isinstance(node, Parameter):
                flattened.append(node.to_frontend_parameter())
            elif isinstance(node, Group):
                flattened.extend(node.to_frontend_parameters())
        return flattened


def _normalize_frontend_parameter_type(parameter_type):
    if parameter_type in {"single", "range", "list", "boolean", "table", "figure"}:
        return parameter_type

    mapping = {
        "string": "single",
        "number": "single",
        "integer": "single",
        "float": "single",
        "bool": "boolean",
        "array": "list",
        "object": "table",
    }
    return mapping.get(str(parameter_type).lower(), "single")


def _build_node(node_definition):
    node_type = node_definition.get("type")
    node_name = node_definition.get("name")

    if node_type == "parameter":
        return Parameter(
            name=node_name,
            parameter_type=node_definition.get("parameter_type", "string"),
            description=node_definition.get("description"),
        )

    if node_type == "group":
        group = Group(name=node_name)
        child_definitions = node_definition.get("children", [])
        for child_definition in child_definitions:
            group.add_child(_build_node(child_definition))
        return group

    raise ValueError("Node definition type must be 'group' or 'parameter'")


def define_template(name, description, node_definitions):
    template = Template(name=name, description=description)
    for node_definition in node_definitions:
        template.add_node(_build_node(node_definition))
    return template


def define_template_from_frontend_parameters(name, description, parameters):
    template = Template(name=name, description=description)

    for param in parameters:
        parameter_name = param.get("name")
        if not parameter_name:
            raise ValueError("Each parameter requires a name")

        parameter_type = param.get("type", "single")
        parameter_description = param.get("comment") or param.get("description")
        group_path = param.get("group")

        if not group_path:
            template.add_parameter(
                name=parameter_name,
                parameter_type=parameter_type,
                description=parameter_description,
            )
            continue

        parts = [part.strip() for part in str(group_path).split(".") if part.strip()]
        if not parts:
            template.add_parameter(
                name=parameter_name,
                parameter_type=parameter_type,
                description=parameter_description,
            )
            continue

        current_group = template.get_or_add_group(parts[0])
        for part in parts[1:]:
            current_group = current_group.get_or_add_group(part)

        current_group.add_parameter(
            name=parameter_name,
            parameter_type=parameter_type,
            description=parameter_description,
        )

    return template


template = define_template(
    name="Example Template",
    description="5 params across 3 groups",
    node_definitions=[
        {
            "type": "group",
            "name": "InputData",  # top-level group
            "children": [
                # 1 child parameter directly under top-level group
                {"type": "parameter", "name": "project_id", "parameter_type": "string"},

                # child group 1 with 2 parameters
                {
                    "type": "group",
                    "name": "Geometry",
                    "children": [
                        {"type": "parameter", "name": "outer_diameter", "parameter_type": "number"},
                        {"type": "parameter", "name": "wall_thickness", "parameter_type": "number"},
                    ],
                },

                # child group 2 with 2 parameters
                {
                    "type": "group",
                    "name": "Material",
                    "children": [
                        {"type": "parameter", "name": "youngs_modulus", "parameter_type": "number"},
                        {"type": "parameter", "name": "density", "parameter_type": "number"},
                    ],
                },
            ],
        }
    ],
)

# Optional: frontend-ready flat payload (with dotted group paths)
frontend_parameters = template.to_frontend_parameters()