import ast
import os
import pathlib


def find_files(directory_path, recursive=True):
    """Find all modules available in the folder path provided.
    The directory inspection can be either recursive or not.

    The selection is made based on the file's extension.
    However, __init__.py will be discarded.
    """

    # Raise an exception if the folder is empty.
    if not os.listdir(directory_path):
        raise FileNotFoundError(f"There are no python source files in {directory_path}.")

    if recursive:
        modules = [str(path) for path in pathlib.Path(directory_path).rglob('*.py')
                   if not str(path).endswith("__init__.py")]
    else:
        modules = [os.path.join(directory_path, file) for file in os.listdir(directory_path)
                   if os.path.isfile(os.path.join(directory_path, file))
                   if pathlib.Path(os.path.join(directory_path, file)).suffix == ".py"
                   if not file.endswith("__init__.py")]
    if not modules:
        raise FileNotFoundError(f"No python modules found in: {directory_path}.")

    return sorted(modules)


def create_report(directory_path, recursive=True):
    """Write a report to list all modules and the docstring example
    coverage stats for each of these modules."""
    print(f'{"Name": <43}{"Docstrings":>12}{"Missed":>11}{"Covered":>10}')
    print('-' * 79)

    # The key of those dictionaries will be the name of the file.
    # So we can easily extract specific information for every module.
    all_methods_with_example = {}
    all_methods_without_example = {}

    # Abstract tree structure is used to get all functions, classes, methods.
    for file_name in find_files(directory_path, recursive):
        with open(file_name) as fd:
            file_contents = fd.read()
        tree = ast.parse(file_contents)

        missing_functions = []
        covered_functions = []
        function_definitions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
        for function in function_definitions:
            # private function are not expected to provide any examples
            if function.name.startswith('_'):
                continue
            if (
                    (ast.get_docstring(function) is None) or
                    ("Example" not in ast.get_docstring(function))
               ):
                missing_functions.append(function.name)
            else:
                covered_functions.append(function.name)

        class_definitions = [node for node in tree.body if isinstance(node, ast.ClassDef)]

        method_definitions = []
        missing_classes = []
        covered_classes = []
        for class_def in class_definitions:
            method_definitions.extend([node for node in class_def.body
                                      if isinstance(node, ast.FunctionDef)])
            if (
                    (ast.get_docstring(class_def) is None) or
                    ("Example" not in ast.get_docstring(class_def))
               ):
                missing_classes.append(class_def.name)
            else:
                covered_classes.append(class_def.name)

        missing_methods = []
        covered_methods = []
        if method_definitions:
            for method in method_definitions:
                # Handle method with decorator.
                # Property setters should not have any example but getters do.
                prop = False
                if method.decorator_list:
                    for decorator in method.decorator_list:
                        # Find property getter decorator.
                        if isinstance(decorator, ast.Name) and decorator.id == "property":
                            if ast.get_docstring(method) is None:
                                missing_methods.append(method.name)
                                prop = True
                            elif "Example" not in ast.get_docstring(method):
                                missing_methods.append(method.name)
                                prop = True
                            else:
                                covered_methods.append(method.name)
                                prop = True
                        # Find property setter decorator.
                        elif isinstance(decorator, ast.Attribute) and decorator.attr == "setter":
                            # For setter methods, we consider them covered.
                            covered_methods.append(method.name)
                            prop = True

                # If the method was a property, it has already been dealt with.
                # There is no need to continue the current method inspection.
                if prop:
                    continue

                # Private methods are not expected to provide any examples.
                if method.name.startswith('_'):
                    continue
                if ast.get_docstring(method) is None or "Example" not in ast.get_docstring(method):
                    missing_methods.append(method.name)
                else:
                    covered_methods.append(method.name)

        # Write report.
        all_methods_without_example[file_name] = missing_functions + missing_classes + \
            missing_methods
        all_methods_with_example[file_name] = covered_functions + covered_classes + covered_methods

        missing = len(all_methods_without_example[file_name])
        total = missing + len(all_methods_with_example[file_name])

        covered = total - missing
        if total:
            percentage_covered = covered/total*100
        else:
            # If no docstring is available in the module, coverage is considered to be 100%.
            percentage_covered = 100

        module_name = (
            os.path.basename(directory_path) +
            pathlib.Path(file_name.split(directory_path)[1].replace(os.path.sep, ".")).stem)

        print(f'{module_name[:42]: <43}{total:12}{missing:11}{percentage_covered:9.1f}%')

    # Get the stats for the entire package.
    all_methods_with_example_list = []
    for method_list in list(all_methods_with_example.values()):
        all_methods_with_example_list.extend(method_list)

    all_methods_without_example_list = []
    for method_list in list(all_methods_without_example.values()):
        all_methods_without_example_list.extend(method_list)

    package_total = len(all_methods_with_example_list) + len(all_methods_without_example_list)
    package_missing = len(all_methods_without_example_list)

    if package_total != 0:
        package_percentage_covered = (package_total - package_missing) / package_total * 100
    else:
        # If none example is expected in the entire package, coverage is considered to be 100%.
        package_percentage_covered = 100
    print('-' * 79)
    print(f'{"Total" : <43}{package_total : 12d}{package_missing : 11d}'
          f'{package_percentage_covered:9.1f}%')
