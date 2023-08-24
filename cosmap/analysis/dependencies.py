import networkx


class CosmapAnalysisException(Exception):
    pass


def build_dependency_graphs(transformation_blocks: dict, block_=None) -> dict:
    graphs = {}
    for name, block in transformation_blocks.items():
        if block_ is not None and name != block_:
            continue
        if name[0].isupper():
            dependency_graph = build_dependency_graph(block)
            graphs.update({name: dependency_graph})
    return graphs


def build_dependency_graph(transformation_block: dict, block=None) -> networkx.DiGraph:
    """
    Once an analysis has been defined, we have to check its validity.
    Obvious failrue cases include if two transformations depend on the output
    of each other. Or if there is a loop (i.e. three transformations which
    depend on eachother). To check this, we consruct a directed graph of
    transformation dependencies and check for cycles. Checking for cycles
    also ensures that a graph has at least one transformation with no dependencies,
    which is required.

    For each transformation, there should be an associated entry in the parameters
    dictionary which specifies dependencies. A transformation without this entry
    will be assumed to have no dependencies. This method will also halt if it finds
    an isolated transformation. That is to say, one which has no dependencies and
    depends on nothing.
    """
    transformation_names = transformation_block.keys()
    dependency_graph = networkx.DiGraph()
    dependency_graph.add_nodes_from(transformation_names)
    for transformation, tparams in transformation_block.items():
        dependencies = tparams.get("dependencies", None)
        if dependencies is not None:
            if not isinstance(dependencies, dict):
                raise CosmapAnalysisException(
                    "Dependencies should be passed as a dictionary, "
                    "where the key is the name of the dependency "
                    "transformation and the value is the name the argument "
                    "with its output will be assigned when passed to this "
                    "transformation."
                )
            if not all([dep in transformation_block.keys() for dep in dependencies]):
                raise CosmapAnalysisException(
                    "Unknown dependencies found! If this transformation needs a "
                    "parameter, you should put the parameter name in the "
                    "needed-parameters block of the dependency's configuration."
                )

            for dep in dependencies:
                dependency_graph.add_edge(dep, transformation)

    [node for node in dependency_graph.nodes() if dependency_graph.in_degree(node) == 0]
    cycles = list(networkx.simple_cycles(dependency_graph))
    if cycles:
        raise CosmapAnalysisException("Analysis contains a dependency cycle!")

    return dependency_graph
